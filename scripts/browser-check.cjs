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

    // Real Web Crypto with synthetic memories; only authenticated loopback APIs.
    await page.locator('.nav-button[data-panel="memory"]').click();
    await page.locator('#memory-enabled').check();
    await page.locator('#memory-status').filter({hasText: 'ON'}).waitFor();
    const backupText = '<img src=x onerror=window.__backupInjected=1> encrypted synthetic memory';
    const password = 'synthetic backup passphrase 2026';
    await page.locator('#memory-text').fill(backupText);
    await page.locator('#memory-category').selectOption('project');
    await page.locator('#memory-approved').check();
    await page.getByRole('button', {name: 'Save memory', exact: true}).click();
    await page.locator('#memory-list').getByText(backupText, {exact: true}).waitFor();
    await page.locator('#backup-password').fill(password);
    await page.locator('#backup-password-confirm').fill(password);
    const encryptedDownload = page.waitForEvent('download');
    await page.locator('#create-backup').click();
    const encryptedFile = await encryptedDownload;
    const encrypted = fs.readFileSync(await encryptedFile.path(), 'utf8');
    assert.equal(JSON.parse(encrypted).format, 'wanda-encrypted-backup');
    assert.equal(encrypted.includes(backupText), false);
    const decrypted = await page.evaluate(async ({serialized, password}) => {
      return window.WandaBackup.decrypt(serialized, password);
    }, {serialized: encrypted, password});
    assert.equal(decrypted.memories[0].text, backupText);
    assert.deepEqual(Object.keys(decrypted).sort(), ['created_at', 'format', 'memories', 'version']);
    for (const id of ['backup-password', 'backup-password-confirm', 'restore-password']) {
      assert.equal(await page.locator('#' + id).inputValue(), '');
    }
    passed++;

    let restorePosts = 0, previewPosts = 0;
    page.on('request', request => {
      const pathname = new URL(request.url()).pathname;
      if (request.method() === 'POST' && pathname === '/api/memory/restore') restorePosts++;
      if (request.method() === 'POST' && pathname === '/api/memory/restore/preview') previewPosts++;
    });
    async function loadBackup(serialized, secret = password) {
      await page.locator('#restore-file').setInputFiles({
        name: 'synthetic-encrypted-backup.json', mimeType: 'application/json', buffer: Buffer.from(serialized),
      });
      await page.locator('#restore-password').fill(secret);
      await page.locator('#preview-backup').click();
    }
    async function waitForBackupIdle() {
      await page.waitForFunction(() => document.getElementById('backup-section').getAttribute('aria-busy') === 'false');
    }
    await page.locator('#clear-memory').click();
    await page.locator('#confirm-accept').click();
    await page.getByText('A fresh page. Nothing is saved yet.', {exact: true}).waitFor();
    await loadBackup(encrypted, 'incorrect synthetic passphrase');
    await waitForBackupIdle();
    await page.locator('#notice').filter({hasText: 'password is incorrect'}).waitFor();
    assert.equal(await page.locator('#restore-preview').isVisible(), false);
    assert.equal(await page.locator('#restore-password').inputValue(), '');
    assert.equal(await page.locator('#restore-file').inputValue(), '');
    const tampered = JSON.parse(encrypted);
    tampered.ciphertext = (tampered.ciphertext[0] === 'A' ? 'B' : 'A') + tampered.ciphertext.slice(1);
    await loadBackup(JSON.stringify(tampered));
    await waitForBackupIdle();
    await page.locator('#notice').filter({hasText: 'password is incorrect'}).waitFor();
    assert.equal(restorePosts, 0);
    assert.equal(previewPosts, 0);
    assert.equal(await page.locator('#memory-list .list-item').count(), 0);
    passed++;

    await loadBackup(encrypted);
    await page.locator('#restore-summary').filter({hasText: '1 can be merged'}).waitFor();
    await page.locator('#restore-memory-list').getByText(backupText, {exact: true}).waitFor();
    assert.equal(await page.locator('#restore-memory-list img').count(), 0);
    assert.equal(await page.evaluate(() => window.__backupInjected), undefined);
    assert.equal(await page.locator('#restore-password').inputValue(), '');
    await page.locator('#merge-backup').click();
    await page.locator('#confirm-dialog').getByRole('button', {name: 'Cancel', exact: true}).click();
    await page.locator('#notice').filter({hasText: 'Restore cancelled'}).waitFor();
    assert.equal(restorePosts, 0);
    assert.equal(await page.locator('#restore-preview').isVisible(), false);
    assert.equal(await page.locator('#memory-list .list-item').count(), 0);
    passed++;

    await loadBackup(encrypted);
    await page.locator('#restore-summary').filter({hasText: '1 can be merged'}).waitFor();
    await page.locator('#merge-backup').click();
    await page.locator('#confirm-accept').filter({hasText: 'Approve memory merge'}).click();
    await page.locator('#memory-list').getByText(backupText, {exact: true}).waitFor();
    assert.equal(restorePosts, 1);
    await loadBackup(encrypted);
    await page.locator('#restore-summary').filter({hasText: '0 can be merged · 1 duplicates'}).waitFor();
    assert.equal(await page.locator('#merge-backup').isDisabled(), true);
    assert.equal(await page.locator('#memory-list .list-item').count(), 1);
    await page.locator('#discard-backup-preview').click();
    assert.equal(restorePosts, 1);
    passed++;

    const manyEncrypted = await page.evaluate(async ({password}) => {
      const created = Math.floor(Date.now() / 1000);
      const memories = Array.from({length: 51}, (_, index) => ({
        id: crypto.randomUUID(), text: `Synthetic recovery record ${index + 1}`,
        category: 'project', created_at: created, expires_at: null,
      }));
      return window.WandaBackup.encrypt({format: 'wanda-memory-backup', version: 1, created_at: created, memories}, password);
    }, {password});
    await loadBackup(manyEncrypted);
    await page.locator('#restore-summary').filter({hasText: '51 can be merged'}).waitFor();
    assert.equal(await page.locator('#restore-memory-list .list-item').count(), 50);
    await page.locator('#restore-next-page').click();
    await page.locator('#restore-memory-list').getByText('Synthetic recovery record 51', {exact: true}).waitFor();
    assert.equal(await page.locator('#restore-memory-list .list-item').count(), 1);
    assert.equal(await page.locator('#restore-next-page').isDisabled(), true);
    await page.locator('#restore-previous-page').click();
    await page.locator('#restore-memory-list').getByText('Synthetic recovery record 1', {exact: true}).waitFor();
    await page.setViewportSize({width: 390, height: 844});
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Backup layout overflows mobile viewport');
    await page.setViewportSize({width: 1440, height: 1000});
    await page.locator('#discard-backup-preview').click();
    assert.equal(restorePosts, 1);
    passed++;

    // A delayed preview must stay discarded after leaving Memory and returning
    // before the response arrives. The decrypted text must not reappear.
    let releasePreview, previewReachedResolve;
    const previewReached = new Promise(resolve => { previewReachedResolve = resolve; });
    await page.route('**/api/memory/restore/preview', async route => {
      previewReachedResolve();
      await new Promise(resolve => { releasePreview = resolve; });
      await route.continue();
    });
    await loadBackup(manyEncrypted);
    await previewReached;
    await page.locator('.nav-button[data-panel="privacy"]').click();
    await page.locator('.nav-button[data-panel="memory"]').click();
    assert.equal(await page.locator('#restore-preview').isVisible(), false);
    assert.equal(await page.locator('#restore-memory-list .list-item').count(), 0);
    assert.equal(await page.locator('#restore-password').inputValue(), '');
    assert.equal(await page.locator('#restore-file').inputValue(), '');
    releasePreview();
    await waitForBackupIdle();
    await page.locator('#notice').filter({hasText: 'Backup preview discarded'}).waitFor();
    assert.equal(await page.locator('#restore-preview').isVisible(), false);
    assert.equal(await page.locator('#restore-memory-list .list-item').count(), 0);
    await page.unroute('**/api/memory/restore/preview');
    passed++;

    // Once approval submits a merge, navigation must clear the hidden preview
    // without claiming to cancel the server request. A later error stays honest.
    await loadBackup(manyEncrypted);
    await page.locator('#restore-summary').filter({hasText: '51 can be merged'}).waitFor();
    let releaseRestore, restoreReachedResolve;
    const restoreReached = new Promise(resolve => { restoreReachedResolve = resolve; });
    await page.route('**/api/memory/restore', async route => {
      restoreReachedResolve();
      await new Promise(resolve => { releaseRestore = resolve; });
      await route.fulfill({status: 503, json: {error: 'Synthetic restore failed'}});
    });
    await page.locator('#merge-backup').click();
    await page.locator('#confirm-accept').filter({hasText: 'Approve memory merge'}).click();
    await restoreReached;
    await page.locator('.nav-button[data-panel="privacy"]').click();
    assert.equal(await page.locator('#restore-preview').isVisible(), false);
    assert.equal(await page.locator('#restore-memory-list .list-item').count(), 0);
    releaseRestore();
    await waitForBackupIdle();
    await page.locator('#notice').filter({hasText: 'Synthetic restore failed'}).waitFor();
    assert.equal((await page.locator('#notice').textContent()).includes('Restore cancelled'), false);
    await page.locator('.nav-button[data-panel="memory"]').click();
    assert.equal(await page.locator('#restore-preview').isVisible(), false);
    assert.equal(await page.locator('#restore-memory-list .list-item').count(), 0);
    assert.equal(await page.locator('#restore-password').inputValue(), '');
    assert.equal(await page.locator('#restore-file').inputValue(), '');
    await page.unroute('**/api/memory/restore');
    passed++;

    await page.locator('#backup-password').fill(password);
    await page.locator('#backup-password-confirm').fill('different synthetic passphrase');
    await page.locator('#create-backup').click();
    await page.locator('#notice').filter({hasText: 'passwords do not match'}).waitFor();
    assert.equal(await page.locator('#backup-password').inputValue(), '');
    assert.equal(await page.locator('#backup-password-confirm').inputValue(), '');
    assert.equal(await page.evaluate(() => {
      return [...Object.keys(localStorage), ...Object.keys(sessionStorage)].some(key => /backup|password/i.test(key));
    }), false);
    await page.locator('.nav-button[data-panel="privacy"]').click();
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
    await vp.unroute('**/api/status');
    await vp.route('**/api/status', async route => {
      const response = await route.fetch();
      const data = await response.json(); data.voice.configured = true;
      await route.fulfill({response, json: data});
    });
    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    await vp.locator('#read-aloud').check();
    await vp.locator('.nav-button[data-panel="memory"]').click();
    await vp.locator('#backup-password').fill(password);
    assert.equal(await vp.locator('#microphone-label').textContent(), 'Mic off');
    assert.equal(await vp.evaluate(() => window.__probe.stops), 5);
    assert.equal(await vp.locator('#connect-voice').isDisabled(), true);
    assert.equal(await vp.locator('#read-aloud').isChecked(), false);
    await vp.locator('.nav-button[data-panel="conversation"]').click();
    assert.equal(await vp.locator('#backup-password').inputValue(), '');
    assert.equal(await vp.locator('#connect-voice').isDisabled(), false);
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    passed++;
    console.log(`PASS: ${passed} browser workflows; local-only requests, memory CRUD/export, encrypted backup/restore, home permissions/outage, responsive layout, and mocked voice consent/cancellation/timeout.`);
  } finally {
    if (browser) await browser.close();
    child.kill('SIGTERM');
    await new Promise(resolve => { if (child.exitCode !== null) resolve(); else { child.once('exit', resolve); setTimeout(resolve, 3000); } });
    if (child.exitCode === null) child.kill('SIGKILL');
    fs.rmSync(dataDir, {recursive: true, force: true});
  }
}
main().catch(error => { console.error(error.stack); process.exitCode = 1; });
