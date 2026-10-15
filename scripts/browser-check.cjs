/* Optional Playwright checks. Isolated synthetic app; never contacts a provider. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const {spawn} = require('node:child_process');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '..');
const pause = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function freePort() {
  const server = net.createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  return port;
}

async function main() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wanda-browser-'));
  const port = await freePort();
  const env = {...process.env, WANDA_CONFIG: '', WANDA_DATA_DIR: dataDir, WANDA_PORT: String(port),
    WANDA_ENABLE_CLOUD_VOICE: 'false', OPENAI_API_KEY: '', WANDA_HOME_MODE: 'mock',
    HOME_ASSISTANT_URL: '', HOME_ASSISTANT_TOKEN: '', WANDA_HOME_ENTITIES: ''};
  const child = spawn(process.env.WANDA_TEST_PYTHON || 'python3', ['-m', 'wanda', '--no-browser'], {cwd: root, env, stdio: ['ignore', 'pipe', 'pipe']});
  let browser;
  let passed = 0;
  try {
    const launchFile = path.join(dataDir, 'launcher.json');
    for (let i = 0; i < 100 && !fs.existsSync(launchFile); i++) await pause(50);
    if (!fs.existsSync(launchFile)) throw new Error('Isolated Wanda launcher did not start. Check loopback permission and Python.');
    const launch = JSON.parse(fs.readFileSync(launchFile, 'utf8'));
    const base = `http://127.0.0.1:${port}`;
    const url = `${base}/#token=${launch.token}`;
    browser = await chromium.launch({headless: true,
      ...(process.env.WANDA_TEST_BROWSER ? {channel: process.env.WANDA_TEST_BROWSER} : {})});
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const page = await context.newPage();
    const errors = [], external = [];
    page.on('pageerror', e => errors.push(e.message));
    await context.route('**/*', async route => {
      if (!route.request().url().startsWith(base)) { external.push(new URL(route.request().url()).origin); await route.abort(); }
      else await route.continue();
    });
    await page.goto(url);
    await page.getByText('Running on this computer', {exact: true}).waitFor();
    assert.equal(new URL(page.url()).hash, '');
    assert.equal(await page.locator('#connect-voice').isDisabled(), true);
    assert.equal(await page.locator('#microphone-label').textContent(), 'Mic off');
    await page.locator('[data-suggestion="How does privacy work?"]').click();
    await page.locator('#messages').getByText(/This text demo stays on this computer/).waitFor();
    passed++;

    await page.locator('.nav-button[data-panel="memory"]').click();
    await page.locator('#memory-enabled').check();
    await page.locator('#memory-status').filter({hasText: 'ON'}).waitFor();
    await page.locator('.nav-button[data-panel="conversation"]').click();
    await page.locator('#chat-input').fill('My favorite color is green.');
    await page.locator('#send-chat').click();
    await page.getByText('A consented detail was saved locally. Review it in Memory.', {exact: true}).waitFor();
    await page.reload();
    await page.getByText('Running on this computer', {exact: true}).waitFor();
    await page.locator('.nav-button[data-panel="memory"]').click();
    await page.locator('#memory-list').getByText('My favorite color is green.', {exact: true}).waitFor();
    await page.locator('#memory-list').getByRole('button', {name: 'Edit', exact: true}).click();
    const inert = '<img src=x onerror=window.__injected=1> synthetic note';
    await page.locator('#memory-text').fill(inert);
    await page.locator('#memory-approved').check();
    await page.getByRole('button', {name: 'Save memory', exact: true}).click();
    await page.locator('#memory-list').getByText(inert, {exact: true}).waitFor();
    assert.equal(await page.locator('#memory-list img').count(), 0);
    assert.equal(await page.evaluate(() => window.__injected), undefined);
    const downloadPromise = page.waitForEvent('download');
    await page.locator('#export-memory').click();
    const download = await downloadPromise;
    const exported = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
    assert.equal(exported.memories[0].text, inert);
    await page.locator('#memory-enabled').uncheck();
    await page.locator('#memory-status').filter({hasText: 'OFF'}).waitFor();
    await page.locator('#memory-list').getByRole('button', {name: 'Delete', exact: true}).click();
    await page.locator('#confirm-accept').click();
    await page.getByText('A fresh page. Nothing is saved yet.', {exact: true}).waitFor();
    passed++;

    await page.locator('.nav-button[data-panel="home"]').click();
    let lamp = page.locator('.device-card').filter({has: page.getByRole('heading', {name: 'Demo lamp', exact: true})});
    await lamp.getByRole('button', {name: 'Turn on', exact: true}).click();
    await page.locator('#notice').filter({hasText: 'No active permission'}).waitFor();
    await page.getByRole('button', {name: 'Grant this permission', exact: true}).click();
    await page.locator('#home-grants').getByText('Demo lamp · turn on', {exact: true}).waitFor();
    await lamp.getByRole('button', {name: 'Turn on', exact: true}).click();
    await page.locator('#confirm-accept').filter({hasText: 'Approve this action'}).click();
    await lamp.getByText('Reported state: on', {exact: true}).waitFor();
    await page.locator('#home-outage').check();
    await lamp.getByText('Reported state: unavailable', {exact: true}).waitFor();
    await lamp.getByRole('button', {name: 'Turn on', exact: true}).click();
    await page.locator('#confirm-accept').click();
    await page.locator('#notice').filter({hasText: 'Mock home is offline.'}).waitFor();
    await page.locator('#home-outage').uncheck();
    await lamp.getByText('Reported state: on', {exact: true}).waitFor();
    await page.getByRole('button', {name: 'Revoke permission', exact: true}).click();
    await page.getByText('No permissions yet. Device actions are denied until you grant a scope.', {exact: true}).waitFor();
    passed++;

    await page.locator('.nav-button[data-panel="privacy"]').click();
    await page.getByRole('button', {name: 'Save permission rule', exact: true}).click();
    await page.locator('#disclosure-list').getByText('openai · preference · Denied', {exact: true}).waitFor();
    await page.getByRole('button', {name: 'Revoke rule', exact: true}).click();
    await page.getByText('No disclosure rules. Saved memory stays local.', {exact: true}).waitFor();
    passed++;

    await page.locator('.nav-button[data-panel="conversation"]').click();
    await page.locator('#language').selectOption('pt');
    await page.locator('#chat-input').fill('Olá');
    await page.locator('#send-chat').click();
    await page.locator('#messages').getByText(/Sou a Wanda/).waitFor();
    const screenshotDir = process.env.WANDA_SCREENSHOTS;
    await page.evaluate(() => window.scrollTo(0, 0));
    if (screenshotDir) {
      fs.mkdirSync(screenshotDir, {recursive: true});
      await page.screenshot({path: path.join(screenshotDir, 'wanda-desktop.png'), fullPage: true});
    }
    await page.setViewportSize({width: 390, height: 844});
    if (screenshotDir) await page.screenshot({path: path.join(screenshotDir, 'wanda-mobile.png'), fullPage: true});
    const overflow = await page.evaluate(() => ({width: document.documentElement.scrollWidth, viewport: window.innerWidth,
      elements: [...document.querySelectorAll('body *')].filter(x => x.getBoundingClientRect().right > window.innerWidth + 1).map(x => x.tagName + '.' + x.className).slice(0, 8)}));
    assert.ok(overflow.width <= overflow.viewport, 'Mobile overflow: ' + JSON.stringify(overflow));
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    passed++;

    // Synthetic browser APIs exercise lifecycle paths, never a microphone/provider.
    const voiceContext = await browser.newContext();
    await voiceContext.addInitScript(() => {
      window.__probe = {captures: 0, stops: 0, closes: 0, sends: [], pending: null};
      const probe = window.__probe;
      const stream = () => ({getTracks: () => [{stop() { probe.stops++; }, addEventListener() {}}]});
      Object.defineProperty(navigator, 'mediaDevices', {value: {getUserMedia: async () => {
        probe.captures++;
        if (probe.reject) throw new DOMException('Synthetic denial', 'NotAllowedError');
        if (probe.delay) return new Promise(resolve => { probe.pending = () => resolve(stream()); });
        return stream();
      }}, configurable: true});
      window.RTCPeerConnection = class {
        addTrack() {}
        createDataChannel() {
          this.channel = {readyState: 'connecting', send(value) { probe.sends.push(JSON.parse(value)); }, close() { this.readyState = 'closed'; }};
          probe.channel = this.channel;
          return this.channel;
        }
        async createOffer() { return {type: 'offer', sdp: 'v=0\r\nsynthetic-offer'}; }
        async setLocalDescription(offer) { this.localDescription = offer; }
        async setRemoteDescription() { this.channel.readyState = 'open'; this.channel.onopen(); }
        close() { probe.closes++; }
      };
    });
    const vp = await voiceContext.newPage();
    await vp.route('**/api/status', async route => {
      const response = await route.fetch();
      const data = await response.json(); data.voice.configured = true;
      await route.fulfill({response, json: data});
    });
    let offers = 0;
    await vp.route('**/api/voice/session', async route => {
      const data = route.request().postDataJSON();
      assert.equal(data.audio_consent, true);
      assert.deepEqual(Object.keys(data).sort(), ['audio_consent', 'sdp']);
      offers++;
      await route.fulfill({json: {sdp: 'v=0\r\nsynthetic-answer'}});
    });
    await vp.goto(url);
    await vp.getByText('Running on this computer', {exact: true}).waitFor();
    await vp.locator('#connect-voice').click();
    assert.equal(await vp.locator('#confirm-accept').isDisabled(), true);
    assert.equal(await vp.evaluate(() => window.__probe.captures), 0);
    await vp.locator('#confirm-dialog').getByRole('button', {name: 'Cancel', exact: true}).click();
    assert.equal(await vp.evaluate(() => window.__probe.captures), 0);
    passed++;

    async function connect() {
      await vp.locator('#connect-voice').click();
      await vp.locator('#audio-consent').check();
      await vp.locator('#confirm-accept').click();
    }
    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    await vp.locator('#chat-input').fill('A synthetic cloud test');
    await vp.locator('#send-chat').click();
    assert.ok(await vp.evaluate(() => window.__probe.sends.some(x => x.type === 'conversation.item.create' && x.item.content[0].text === 'A synthetic cloud test')));
    await vp.evaluate(() => window.__probe.channel.onmessage({data: JSON.stringify({type: 'response.created'})}));
    await vp.locator('#interrupt').click();
    assert.ok(await vp.evaluate(() => window.__probe.sends.some(x => x.type === 'response.cancel')));
    await vp.locator('#disconnect').click();
    assert.equal(await vp.evaluate(() => window.__probe.stops), 1);
    assert.equal(await vp.locator('#microphone-label').textContent(), 'Mic off');
    assert.equal(offers, 1);
    passed++;

    await vp.evaluate(() => { window.__probe.delay = true; });
    await connect();
    await vp.locator('#voice-state').filter({hasText: 'Waiting for microphone'}).waitFor();
    await vp.locator('#disconnect').click();
    await vp.evaluate(() => window.__probe.pending());
    await vp.waitForFunction(() => window.__probe.stops === 2);
    assert.equal(offers, 1);
    assert.equal(await vp.locator('#microphone-label').textContent(), 'Mic off');
    passed++;

    await vp.evaluate(() => { window.__probe.delay = false; window.__probe.reject = true; });
    await connect();
    await vp.locator('#notice').filter({hasText: 'Microphone permission was declined'}).waitFor();
    assert.equal(await vp.locator('#microphone-label').textContent(), 'Mic off');
    assert.equal(offers, 1);
    passed++;

    await vp.clock.install();
    await vp.evaluate(() => { window.__probe.reject = false; });
    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    await vp.clock.fastForward(5 * 60 * 1000 + 1);
    assert.equal(await vp.locator('#microphone-label').textContent(), 'Mic off');
    assert.equal(await vp.evaluate(() => window.__probe.stops), 3);
    passed++;
    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    await vp.route('**/api/status', route => route.fulfill({status: 503, json: {error: 'Synthetic local service stopped'}}));
    await vp.clock.fastForward(3001);
    await vp.locator('#microphone-label').filter({hasText: 'Mic off'}).waitFor();
    assert.equal(await vp.evaluate(() => window.__probe.stops), 4);
    passed++;
    console.log(`PASS: ${passed} browser workflows; local-only requests, memory CRUD/export, home permissions/outage, responsive layout, and mocked voice consent/cancellation/timeout.`);
  } finally {
    if (browser) await browser.close();
    child.kill('SIGTERM');
    await new Promise(resolve => { if (child.exitCode !== null) resolve(); else { child.once('exit', resolve); setTimeout(resolve, 3000); } });
    if (child.exitCode === null) child.kill('SIGKILL');
    fs.rmSync(dataDir, {recursive: true, force: true});
  }
}
main().catch(error => { console.error(error.stack); process.exitCode = 1; });
