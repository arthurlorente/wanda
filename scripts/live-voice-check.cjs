/* Bounded live smoke-test child. The Python parent owns authorization and budget.
 * stdin: one JSON line {base, token, mode}; token is a loopback capability only.
 * stdout: one sanitized JSON result. Never run this as an automatic CI test.
 */
'use strict';

const readline = require('node:readline');

let browser;
let emitted = false;
let mode = 'smoke';
let phase = 'input';
let overallTimer;

function emit(result) {
  if (emitted) return;
  emitted = true;
  clearTimeout(overallTimer);
  clearTimeout(watchdog);
  process.stdout.write(JSON.stringify({provider_hangup_ack: false, ...result}) + '\n');
  process.exitCode = result.ok ? 0 : 1;
}

const watchdog = setTimeout(async () => {
  let cleanup = !browser;
  if (browser) {
    cleanup = await Promise.race([
      browser.close().then(() => true, () => false),
      new Promise(resolve => setTimeout(() => resolve(false), 500)),
    ]);
  }
  emit({ok: false, mode, phase, error_code: 'process_deadline', cleanup});
  process.exit(1);
}, 70_000);

function readInput() {
  return new Promise((resolve, reject) => {
    const lines = readline.createInterface({input: process.stdin, crlfDelay: Infinity});
    let received = false;
    lines.once('line', line => {
      received = true;
      lines.close();
      process.stdin.pause();
      try {
        if (line.length > 4096) throw new Error();
        const value = JSON.parse(line);
        if (!value || Object.keys(value).sort().join(',') !== 'base,mode,token') throw new Error();
        if (!['smoke', 'cancel'].includes(value.mode)) throw new Error();
        if (typeof value.base !== 'string') throw new Error();
        const base = new URL(value.base);
        if (base.protocol !== 'http:' || base.hostname !== '127.0.0.1' || !base.port ||
            base.username || base.password || base.search || base.hash || base.pathname !== '/') throw new Error();
        if (typeof value.token !== 'string' || !/^[A-Za-z0-9_-]{20,256}$/.test(value.token)) throw new Error();
        resolve({base: base.origin, token: value.token, mode: value.mode});
      } catch (_) { reject(new Error('invalid_input')); }
    });
    lines.once('close', () => { if (!received) reject(new Error('missing_input')); });
  });
}

async function main() {
  let result;
  let expired = false;
  try {
    const input = await readInput();
    mode = input.mode;
    const deadline = Date.now() + 60_000;
    overallTimer = setTimeout(() => {
      expired = true;
      // The page's 60-second deadline starts cleanup, including bounded hangup.
      // Keep the peer alive for that acknowledgement; the 70-second watchdog
      // remains independent if page execution or cleanup becomes unresponsive.
    }, 60_000);
    phase = 'browser';
    const {chromium} = require('playwright');
    browser = await chromium.launch({headless: true,
      channel: process.env.WANDA_TEST_BROWSER || 'chrome',
      args: ['--mute-audio', '--autoplay-policy=no-user-gesture-required'],
      timeout: 15_000});
    const context = await browser.newContext({permissions: [], serviceWorkers: 'block'});
    await context.addInitScript(() => {
      window.__wandaMicrophoneCalls = 0;
      if (navigator.mediaDevices) {
        Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {value: async () => {
          window.__wandaMicrophoneCalls++;
          throw new Error('Real microphone forbidden in synthetic test');
        }});
      }
    });
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.origin === input.base && ['/health', '/api/voice/session', '/api/voice/test/end'].includes(url.pathname)) {
        return route.continue();
      }
      return route.abort();
    });
    const page = await context.newPage();
    phase = 'health';
    const health = await page.goto(input.base + '/health', {timeout: 10_000});
    if (!health || !health.ok()) throw new Error('health_failed');
    phase = 'webrtc';
    result = await page.evaluate(async ({base, token, mode, deadline}) => {
      const began = performance.now();
      const elapsed = () => Math.round(performance.now() - began);
      const result = {ok: false, mode, phase: 'setup', cleanup: false,
        provider_hangup_ack: false, provider_hangup_attempted: false,
        transcript: '', audio_packets: 0, audio_bytes: 0, audio_tracks: 0,
        response_create_count: 0, microphone_calls: 0, event_types: [], timings: {}};
      const eventTypes = new Set();
      const controller = new AbortController();
      let audioContext, source, stream, peer, channel;
      let finished = false;
      let configured = false;
      let sessionAttempted = false;
      let responseId;
      let responseDone = false;
      let cancelSent = false;
      let cancelCleared = false;
      let cancelMissed = false;
      let audioStarted = false;
      let audioPacketsAtStart = 0;
      let statsPending = false;
      let eventCount = 0;
      let setupTimer, responseTimer, finalTimer, overall, statsTimer;
      let resolveResult;
      const completion = new Promise(resolve => { resolveResult = resolve; });
      const safeNumber = value => Number.isSafeInteger(value) && value >= 0 ? value : undefined;

      function usageSummary(usage) {
        if (!usage || typeof usage !== 'object') return null;
        const out = {};
        for (const key of ['total_tokens', 'input_tokens', 'output_tokens']) {
          if (safeNumber(usage[key]) === undefined) return null;
          out[key] = usage[key];
        }
        let valid = out.total_tokens === out.input_tokens + out.output_tokens;
        for (const group of ['input_token_details', 'output_token_details']) {
          out[group] = {};
          for (const key of ['text_tokens', 'audio_tokens']) {
            if (safeNumber(usage[group]?.[key]) === undefined) valid = false;
          }
          for (const key of ['text_tokens', 'audio_tokens', 'image_tokens', 'cached_tokens', 'reasoning_tokens']) {
            const value = safeNumber(usage[group]?.[key]);
            if (value !== undefined) out[group][key] = value;
            else if (usage[group]?.[key] !== undefined) valid = false;
          }
          const cached = usage[group]?.cached_tokens_details;
          if (cached) {
            out[group].cached_tokens_details = {};
            for (const key of ['text_tokens', 'audio_tokens', 'image_tokens']) {
              const value = safeNumber(cached[key]);
              if (value !== undefined) out[group].cached_tokens_details[key] = value;
              else if (cached[key] !== undefined) valid = false;
            }
          }
          const total = group === 'input_token_details' ? out.input_tokens : out.output_tokens;
          const details = out[group];
          if ((details.text_tokens || 0) + (details.audio_tokens || 0) + (details.image_tokens || 0) > total ||
              (details.cached_tokens || 0) > total || (details.reasoning_tokens || 0) > total) valid = false;
        }
        return {data: out, valid};
      }

      async function finish(errorCode) {
        if (finished) return;
        finished = true;
        if (errorCode) result.error_code = errorCode;
        result.ok = !errorCode;
        for (const timer of [setupTimer, responseTimer, finalTimer, overall]) clearTimeout(timer);
        clearInterval(statsTimer);
        controller.abort();
        if (channel?.readyState === 'open' && responseId && !responseDone && !cancelSent) {
          try {
            channel.send(JSON.stringify({type: 'response.cancel', response_id: responseId}));
            channel.send(JSON.stringify({type: 'output_audio_buffer.clear'}));
          } catch (_) {}
        }
        // Stop sending synthetic input immediately, but keep the peer connected
        // until the parent can request and confirm provider-side call teardown.
        for (const track of stream?.getTracks() || []) track.stop();
        try { source?.stop(); source?.disconnect(); } catch (_) {}
        if (sessionAttempted) {
          const hangupController = new AbortController();
          const hangupTimer = setTimeout(() => hangupController.abort(), 10_000);
          result.provider_hangup_attempted = true;
          result.timings.hangup_started_ms = elapsed();
          try {
            const answer = await fetch(base + '/api/voice/test/end', {
              method: 'POST', redirect: 'error', credentials: 'omit', cache: 'no-store',
              headers: {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
              body: '{}', signal: hangupController.signal,
            });
            if (answer.ok) result.provider_hangup_ack = (await answer.json())?.hangup_confirmed === true;
          } catch (_) { result.provider_hangup_ack = false; }
          finally {
            clearTimeout(hangupTimer);
            result.timings.hangup_done_ms = elapsed();
          }
        }
        if (channel) { channel.onmessage = null; channel.onerror = null; channel.onclose = null; channel.close(); }
        if (peer) {
          peer.onconnectionstatechange = null;
          peer.ontrack = null;
          for (const receiver of peer.getReceivers()) receiver.track?.stop();
          peer.close();
        }
        try { if (audioContext && audioContext.state !== 'closed') await audioContext.close(); } catch (_) {}
        result.microphone_calls = window.__wandaMicrophoneCalls;
        result.event_types = [...eventTypes].sort();
        result.cleanup = (!peer || peer.connectionState === 'closed') &&
          (!stream || stream.getTracks().every(track => track.readyState === 'ended')) &&
          (!audioContext || audioContext.state === 'closed');
        if (!result.cleanup || result.microphone_calls !== 0) {
          result.ok = false;
          result.error_code = 'cleanup_or_microphone_violation';
        }
        result.timings.total_ms = elapsed();
        resolveResult(result);
      }

      function send(value) {
        if (finished || channel?.readyState !== 'open') return false;
        try { channel.send(JSON.stringify(value)); return true; }
        catch (_) { finish('datachannel_send_failed'); return false; }
      }

      function maybeCancel() {
        if (mode !== 'cancel' || cancelSent || !responseId || !audioStarted || responseDone || finished) return;
        cancelSent = true;
        result.timings.cancel_sent_ms = elapsed();
        send({type: 'response.cancel', response_id: responseId});
        send({type: 'output_audio_buffer.clear'});
      }

      function maybeComplete() {
        if (!responseDone || finished) return;
        if (mode === 'cancel') {
          if (!cancelSent || cancelMissed || result.response_status !== 'cancelled') return finish('cancellation_inconclusive');
          if (cancelCleared) {
            result.cancel_acknowledged = true;
            return finish();
          }
        } else if (result.response_status !== 'completed') return finish('response_not_completed');
        else if (audioStarted && result.audio_packets > audioPacketsAtStart && result.transcript) return finish();
        if (!finalTimer) finalTimer = setTimeout(() => finish(mode === 'cancel' ? 'cancel_not_acknowledged' : 'missing_audio_or_transcript'), 2000);
      }

      function startResponse() {
        if (!configured || channel?.readyState !== 'open' || result.response_create_count || finished) return;
        clearTimeout(setupTimer);
        result.phase = 'response';
        result.timings.setup_ms = elapsed();
        result.response_create_count = 1;
        responseTimer = setTimeout(() => finish('response_deadline'), 20_000);
        send({type: 'response.create', response: {
          conversation: 'none',
          input: [{type: 'message', role: 'user', content: [{type: 'input_text', text: mode === 'cancel'
            ? 'Count from one to ten in Portuguese, then Spanish. No introduction.'
            : 'Say exactly: Hello. Olá. Hola.'}]}],
          output_modalities: ['audio'], max_output_tokens: 128,
          reasoning: {effort: 'minimal'}, tools: [], tool_choice: 'none',
        }});
      }

      function onEvent(event) {
        if (finished) return;
        let value;
        try {
          if (typeof event.data !== 'string' || event.data.length > 100_000) return finish('invalid_event');
          value = JSON.parse(event.data);
        } catch (_) { return finish('invalid_event'); }
        if (typeof value?.type !== 'string' || !/^[a-z][a-z0-9_.]{0,79}$/.test(value.type)) return finish('invalid_event');
        eventTypes.add(value.type);
        if (++eventCount > 5000 || eventTypes.size > 100) return finish('event_limit');
        if (value.type === 'error') {
          // A completed response can race our cancellation. Retain the ensuing
          // response.done usage instead of discarding accounting information.
          if (mode === 'cancel' && cancelSent && value.error?.code === 'response_cancel_not_active') {
            cancelMissed = true;
            maybeComplete();
            return;
          }
          return finish('provider_event_error');
        }
        if (value.type === 'session.created') {
          const session = value.session;
          if (configured || session?.type !== 'realtime' || session.model !== 'gpt-realtime-2.1' ||
              session.max_output_tokens !== 128 || session.audio?.input?.turn_detection !== null ||
              session.audio.input.transcription != null || !Array.isArray(session.tools) || session.tools.length !== 0 ||
              session.tool_choice !== 'none' || session.reasoning?.effort !== 'minimal' || session.tracing != null ||
              JSON.stringify(session.output_modalities) !== '["audio"]') return finish('unexpected_session_config');
          configured = true;
          result.timings.session_created_ms = elapsed();
          startResponse();
        } else if (value.type === 'response.created') {
          if (!result.response_create_count || responseId || typeof value.response?.id !== 'string') return finish('unexpected_response');
          responseId = value.response.id;
          result.timings.response_created_ms = elapsed();
          maybeCancel();
        } else if (value.type === 'response.output_audio_transcript.delta') {
          if (!responseId || value.response_id !== responseId || typeof value.delta !== 'string') return finish('invalid_transcript');
          result.transcript = (result.transcript + value.delta).slice(0, 400);
        } else if (value.type === 'output_audio_buffer.started') {
          if (!responseId || value.response_id !== responseId) return finish('unexpected_audio_response');
          if (!audioStarted) audioPacketsAtStart = result.audio_packets;
          audioStarted = true;
          result.timings.audio_started_ms ??= elapsed();
          maybeCancel();
        } else if (value.type === 'output_audio_buffer.cleared') {
          if (!responseId || value.response_id !== responseId) return finish('unexpected_audio_response');
          cancelCleared = true;
          maybeComplete();
        } else if (value.type === 'response.done') {
          if (!responseId || value.response?.id !== responseId || responseDone) return finish('unexpected_response');
          responseDone = true;
          result.timings.response_done_ms = elapsed();
          const status = value.response.status;
          if (!['completed', 'cancelled', 'failed', 'incomplete'].includes(status)) return finish('invalid_response_status');
          result.response_status = status;
          const summary = usageSummary(value.response.usage);
          if (summary) result.usage = summary.data;
          if (!summary?.valid) return finish('missing_or_invalid_usage');
          if (result.usage.output_tokens > 32_000 || result.usage.input_tokens > 128_000 ||
              result.usage.input_token_details.audio_tokens !== 0 ||
              (result.usage.input_token_details.image_tokens || 0) !== 0) return finish('unexpected_usage');
          if (result.usage.output_tokens > 128) {
            result.output_cap_exceeded = true;
            return finish('output_cap_exceeded');
          }
          maybeComplete();
        }
      }

      overall = setTimeout(() => finish('overall_deadline'), Math.max(1, deadline - Date.now()));
      setupTimer = setTimeout(() => finish('setup_deadline'), 25_000);
      try {
        audioContext = new AudioContext();
        source = new ConstantSourceNode(audioContext, {offset: 0});
        const destination = audioContext.createMediaStreamDestination();
        source.connect(destination); // No connection to audioContext.destination or speakers.
        stream = destination.stream;
        source.start();
        await audioContext.resume();
        if (finished) return completion;
        peer = new RTCPeerConnection();
        for (const track of stream.getTracks()) peer.addTrack(track, stream);
        peer.ontrack = event => { if (event.track.kind === 'audio') result.audio_tracks++; };
        peer.onconnectionstatechange = () => {
          if (peer.connectionState === 'connected') result.timings.peer_connected_ms ??= elapsed();
          if (['failed', 'closed'].includes(peer.connectionState) && !finished) finish('peer_connection_failed');
        };
        channel = peer.createDataChannel('oai-events');
        channel.onmessage = onEvent;
        channel.onopen = startResponse;
        channel.onerror = () => finish('datachannel_error');
        channel.onclose = () => { if (!finished) finish('datachannel_closed'); };
        statsTimer = setInterval(async () => {
          if (finished || statsPending) return;
          statsPending = true;
          try {
            const stats = await peer.getStats();
            if (finished) return;
            let packets = 0, bytes = 0;
            for (const row of stats.values()) {
              if (row.type === 'inbound-rtp' && (row.kind === 'audio' || row.mediaType === 'audio')) {
                packets += safeNumber(row.packetsReceived) || 0;
                bytes += safeNumber(row.bytesReceived) || 0;
              }
            }
            result.audio_packets = packets;
            result.audio_bytes = bytes;
            if (packets > 0) {
              result.timings.first_audio_packet_ms ??= elapsed();
            }
            maybeComplete();
          } catch (_) { if (!finished) finish('stats_failed'); }
          finally { statsPending = false; }
        }, 100);
        await peer.setLocalDescription(await peer.createOffer());
        if (finished) return completion;
        sessionAttempted = true;
        const answer = await fetch(base + '/api/voice/session', {
          method: 'POST', redirect: 'error', credentials: 'omit', cache: 'no-store',
          headers: {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
          body: JSON.stringify({sdp: peer.localDescription.sdp, audio_consent: true}), signal: controller.signal,
        });
        if (finished) return completion;
        if (!answer.ok) { finish('session_http_' + answer.status); return completion; }
        const data = await answer.json();
        if (typeof data?.sdp !== 'string' || !data.sdp.startsWith('v=0') || data.sdp.length > 100_000) {
          finish('invalid_session_answer'); return completion;
        }
        if (finished) return completion;
        await peer.setRemoteDescription({type: 'answer', sdp: data.sdp});
      } catch (_) { if (!finished) finish('setup_failed'); }
      return completion;
    }, {...input, deadline});
  } catch (error) {
    const codes = new Set(['invalid_input', 'missing_input', 'health_failed']);
    result = {ok: false, mode, phase, error_code: expired ? 'overall_deadline' :
      codes.has(error.message) ? error.message : phase + '_failed', cleanup: false};
  } finally {
    if (browser) {
      try {
        await browser.close();
        result.browser_cleanup = true;
        if (result.microphone_calls !== undefined) result.inner_cleanup = result.cleanup;
        else result.cleanup = true;
      } catch (_) {
        result.ok = false;
        result.browser_cleanup = false;
        result.cleanup = false;
        result.error_code = 'browser_cleanup_failed';
      }
    } else if (result) { result.cleanup = true; result.browser_cleanup = true; }
    emit(result || {ok: false, mode, phase, error_code: 'missing_result', cleanup: false});
  }
}

main();
