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

    // A separate page tests recovery without touching owner data or real voice.
    // Delayed mutation responses can be lost after the isolated server commits.
    const recovery = await context.newPage();
    recovery.on('pageerror', e => errors.push(e.message));
    await recovery.goto(url);
    await recovery.getByText('Running on this computer', {exact: true}).waitFor();
    async function holdApi(pattern, method, mode = 'success') {
      let release, arrived, count = 0;
      const gate = new Promise(resolve => { release = resolve; });
      const started = new Promise(resolve => { arrived = resolve; });
      const handler = async route => {
        if (route.request().method() !== method) return route.continue();
        count++;
        const response = mode === 'failure' ? null : await route.fetch();
        arrived(); await gate;
        if (mode === 'network') return route.abort('failed');
        if (mode === 'timeout') { await route.fulfill({response}).catch(() => {}); return; }
        if (mode === 'failure') return route.fulfill({status: 503, json: {error: 'Synthetic recovery failure'}});
        return route.fulfill({response});
      };
      await recovery.route(pattern, handler);
      return {started, release, count: () => count, remove: () => recovery.unroute(pattern, handler)};
    }
    const saveButton = recovery.locator('#memory-form button[type="submit"]');
    async function fillMemory(text) {
      await recovery.locator('#memory-text').fill(text);
      await recovery.locator('#memory-approved').check();
    }
    async function saved() { await recovery.waitForFunction(() => document.getElementById('memory-form').getAttribute('aria-busy') === 'false'); }
    async function chatReady() { await recovery.waitForFunction(() => !document.getElementById('send-chat').disabled); }
    async function submitChat(text) { await recovery.locator('#chat-input').fill(text); await recovery.locator('#send-chat').click(); }
    await recovery.locator('.nav-button[data-panel="memory"]').click();
    await recovery.locator('#memory-status').filter({hasText: 'ON'}).waitFor();

    const firstSave = await holdApi('**/api/memory', 'POST');
    await fillMemory('Synthetic recovery first memory');
    await saveButton.click(); await firstSave.started;
    assert.equal(await saveButton.isDisabled(), true);
    await recovery.locator('#memory-form').evaluate(form => form.requestSubmit());
    await recovery.locator('#memory-text').fill('Synthetic next unsent memory draft');
    await recovery.locator('#memory-category').selectOption('project');
    await recovery.locator('#refresh-memory').click();
    await recovery.locator('#memory-list').getByText('Synthetic recovery first memory', {exact: true}).waitFor();
    assert.equal(await saveButton.isDisabled(), true, 'A list refresh cannot unlock a pending save');
    firstSave.release(); await saved(); await firstSave.remove();
    assert.equal(firstSave.count(), 1, 'Repeated submit must not duplicate a pending mutation');
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic next unsent memory draft');
    assert.equal(await recovery.locator('#memory-category').inputValue(), 'project');
    passed++;

    const revertedSave = await holdApi('**/api/memory', 'POST');
    await fillMemory('Synthetic recovery second memory');
    await saveButton.click(); await revertedSave.started;
    await recovery.locator('#memory-text').fill('Synthetic temporary edit');
    await recovery.locator('#memory-text').fill('Synthetic recovery second memory');
    revertedSave.release(); await saved(); await revertedSave.remove();
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic recovery second memory', 'Reverting text does not undo newer user interaction');
    passed++;

    const memoryRow = text => recovery.locator('#memory-list .list-item').filter({has: recovery.getByText(text, {exact: true})});
    await memoryRow('Synthetic recovery first memory').getByRole('button', {name: 'Edit', exact: true}).click();
    const editSave = await holdApi('**/api/memory/*', 'PATCH');
    await fillMemory('Synthetic first memory updated');
    await saveButton.click(); await editSave.started;
    await memoryRow('Synthetic recovery second memory').getByRole('button', {name: 'Edit', exact: true}).click();
    await recovery.locator('#memory-text').fill('Synthetic new selected edit draft');
    editSave.release(); await saved(); await editSave.remove();
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic new selected edit draft');
    assert.equal(await recovery.locator('#cancel-memory-edit').isVisible(), true);
    assert.equal(await recovery.locator('#memory-form-title').textContent(), 'Edit this memory');
    await recovery.locator('#cancel-memory-edit').click();
    passed++;

    const networkSave = await holdApi('**/api/memory', 'POST', 'network');
    await fillMemory('Synthetic committed before network loss');
    await saveButton.click(); await networkSave.started; networkSave.release();
    await saved(); await networkSave.remove();
    await recovery.locator('#notice').filter({hasText: 'may already have completed'}).waitFor();
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic committed before network loss');
    assert.equal(networkSave.count(), 1);
    assert.equal(await saveButton.isDisabled(), false);
    await recovery.locator('#refresh-memory').click();
    await memoryRow('Synthetic committed before network loss').waitFor();
    passed++;

    await recovery.route('**/api/memory', route => route.request().method() === 'GET'
      ? route.fulfill({status: 503, json: {error: 'Synthetic memory list failure'}}) : route.continue());
    await fillMemory('Synthetic confirmed save with failed list refresh');
    await saveButton.click(); await saved();
    await recovery.locator('#notice').filter({hasText: 'Memory saved, but the list could not refresh'}).waitFor();
    assert.equal(await recovery.locator('#memory-text').inputValue(), '', 'Confirmed save must not be treated as an unconfirmed write');
    assert.equal(await saveButton.isDisabled(), false);
    await recovery.unroute('**/api/memory');
    await recovery.locator('#refresh-memory').click();
    await memoryRow('Synthetic confirmed save with failed list refresh').waitFor();
    passed++;

    await recovery.locator('.nav-button[data-panel="conversation"]').click();
    const failedChat = await holdApi('**/api/chat', 'POST', 'failure');
    await submitChat('Synthetic failed chat draft');
    await failedChat.started; failedChat.release(); await chatReady(); await failedChat.remove();
    assert.equal(await recovery.locator('#chat-input').inputValue(), 'Synthetic failed chat draft');
    await recovery.locator('.message.user').filter({hasText: 'Synthetic failed chat draft'}).getByText(/Response unconfirmed/).waitFor();
    assert.equal(failedChat.count(), 1, 'Draft restoration must not resend automatically');
    passed++;

    const newerDraftChat = await holdApi('**/api/chat', 'POST', 'failure');
    await submitChat('Synthetic failed chat with newer draft');
    await newerDraftChat.started;
    await recovery.locator('#chat-input').fill('Synthetic newer draft must survive');
    newerDraftChat.release(); await chatReady(); await newerDraftChat.remove();
    assert.equal(await recovery.locator('#chat-input').inputValue(), 'Synthetic newer draft must survive');
    const erasedDraftChat = await holdApi('**/api/chat', 'POST', 'failure');
    await submitChat('Synthetic failed chat after deliberate draft deletion');
    await erasedDraftChat.started;
    await recovery.locator('#chat-input').fill('Synthetic then deliberately deleted');
    await recovery.locator('#chat-input').fill('');
    erasedDraftChat.release(); await chatReady(); await erasedDraftChat.remove();
    assert.equal(await recovery.locator('#chat-input').inputValue(), '', 'User-deleted newer draft must stay empty');
    passed++;

    const clearedChat = await holdApi('**/api/chat', 'POST', 'failure');
    await submitChat('Synthetic request cleared before failure');
    await clearedChat.started;
    await recovery.locator('#clear-chat').click();
    clearedChat.release(); await chatReady(); await clearedChat.remove();
    assert.equal(await recovery.locator('#chat-input').inputValue(), '');
    assert.equal(await recovery.locator('#messages').getByText(/Synthetic request cleared|Response unconfirmed/).count(), 0);
    assert.match(await recovery.locator('#notice').textContent(), /Chat cleared from this page/);
    passed++;

    await recovery.route('**/api/memory', route => route.fulfill({status: 503, json: {error: 'Synthetic refresh failure'}}));
    await submitChat('Hello, Wanda');
    await chatReady();
    await recovery.locator('#notice').filter({hasText: 'Wanda replied, but the memory list could not refresh'}).waitFor();
    assert.equal(await recovery.locator('#chat-input').inputValue(), '');
    assert.equal(await recovery.locator('#messages').getByText(/Response unconfirmed/).count(), 0);
    assert.equal(await recovery.locator('#messages .message.assistant').count(), 2, 'Greeting plus the confirmed response remain visible');
    await recovery.unroute('**/api/memory');
    passed++;

    await recovery.clock.install();
    await recovery.locator('.nav-button[data-panel="memory"]').click();
    const timeoutSave = await holdApi('**/api/memory', 'POST', 'timeout');
    await fillMemory('Synthetic committed before timeout');
    await saveButton.click(); await timeoutSave.started;
    await recovery.clock.fastForward(35001); await saved();
    await recovery.locator('#notice').filter({hasText: 'It may already have completed'}).waitFor();
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic committed before timeout');
    assert.equal(timeoutSave.count(), 1);
    timeoutSave.release(); await timeoutSave.remove();
    await recovery.locator('#refresh-memory').click();
    await memoryRow('Synthetic committed before timeout').waitFor();
    await recovery.route('**/api/memory', route => route.abort('failed'));
    await recovery.locator('#refresh-memory').click();
    await recovery.locator('#notice').filter({hasText: 'Wanda is not reachable'}).waitFor();
    assert.equal((await recovery.locator('#notice').textContent()).includes('may already have completed'), false, 'Failed reads have no mutation uncertainty');
    await recovery.unroute('**/api/memory');
    passed++;

    async function addDeletionFixture(text) {
      if (await recovery.locator('#cancel-memory-edit').isVisible()) await recovery.locator('#cancel-memory-edit').click();
      await fillMemory(text); await recovery.locator('#memory-category').selectOption('preference');
      await saveButton.click(); await saved(); await memoryRow(text).waitFor();
    }
    async function confirmDeleteAll() {
      await recovery.locator('#clear-memory').click(); await recovery.locator('#confirm-accept').click();
    }
    async function confirmDelete(text) {
      await memoryRow(text).getByRole('button', {name: 'Delete', exact: true}).click();
      await recovery.locator('#confirm-accept').click();
    }
    await addDeletionFixture('Synthetic delete-all unchanged form');
    await memoryRow('Synthetic delete-all unchanged form').getByRole('button', {name: 'Edit', exact: true}).click();
    const unchangedDeleteAll = await holdApi('**/api/memory', 'DELETE');
    await confirmDeleteAll(); await unchangedDeleteAll.started; unchangedDeleteAll.release();
    await recovery.getByText('All local memories deleted.', {exact: true}).waitFor();
    assert.equal(await recovery.locator('#memory-text').inputValue(), '');
    assert.equal(await recovery.locator('#cancel-memory-edit').isVisible(), false);
    assert.equal(await recovery.locator('#memory-list .list-item').count(), 0);
    await unchangedDeleteAll.remove();
    passed++;

    await addDeletionFixture('Synthetic delete-all newer draft fixture');
    const newerDeleteAll = await holdApi('**/api/memory', 'DELETE');
    await confirmDeleteAll(); await newerDeleteAll.started;
    await fillMemory('Synthetic newer draft after delete-all confirmation');
    await recovery.locator('#memory-category').selectOption('project');
    newerDeleteAll.release();
    await recovery.locator('#notice').filter({hasText: 'Your newer draft was kept'}).waitFor();
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic newer draft after delete-all confirmation');
    assert.equal(await recovery.locator('#memory-category').inputValue(), 'project');
    assert.equal(await recovery.locator('#memory-list .list-item').count(), 0);
    await newerDeleteAll.remove();
    passed++;

    await addDeletionFixture('Synthetic deleted record selected during wait');
    const selectedDeleteAll = await holdApi('**/api/memory', 'DELETE');
    await confirmDeleteAll(); await selectedDeleteAll.started;
    await memoryRow('Synthetic deleted record selected during wait').getByRole('button', {name: 'Edit', exact: true}).click();
    await fillMemory('Synthetic preserved edit becomes a new draft');
    await recovery.locator('#memory-category').selectOption('sensitive');
    selectedDeleteAll.release();
    await recovery.locator('#notice').filter({hasText: 'unsaved draft for a new memory'}).waitFor();
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic preserved edit becomes a new draft');
    assert.equal(await recovery.locator('#memory-category').inputValue(), 'sensitive');
    assert.equal(await recovery.locator('#memory-form-title').textContent(), 'Add a memory');
    assert.equal(await recovery.locator('#cancel-memory-edit').isVisible(), false);
    await selectedDeleteAll.remove();
    const recreatedRequest = recovery.waitForRequest(request => new URL(request.url()).pathname === '/api/memory' && request.method() === 'POST');
    await saveButton.click(); await recreatedRequest; await saved();
    await memoryRow('Synthetic preserved edit becomes a new draft').waitFor();
    passed++;

    await memoryRow('Synthetic preserved edit becomes a new draft').getByRole('button', {name: 'Edit', exact: true}).click();
    const newerSingleDelete = await holdApi('**/api/memory/*', 'DELETE');
    await confirmDelete('Synthetic preserved edit becomes a new draft'); await newerSingleDelete.started;
    await recovery.locator('#memory-text').fill('Synthetic new text during single deletion');
    await recovery.locator('#memory-category').selectOption('project');
    await recovery.route('**/api/memory', route => route.fulfill({status: 503, json: {error: 'Synthetic post-delete refresh failure'}}));
    newerSingleDelete.release();
    await recovery.locator('#notice').filter({hasText: 'The memory list could not refresh'}).waitFor();
    assert.match(await recovery.locator('#notice').textContent(), /^Memory deleted\./);
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic new text during single deletion');
    assert.equal(await recovery.locator('#memory-category').inputValue(), 'project');
    assert.equal(await recovery.locator('#memory-form-title').textContent(), 'Add a memory');
    assert.equal(await recovery.locator('#cancel-memory-edit').isVisible(), false);
    await newerSingleDelete.remove(); await recovery.unroute('**/api/memory');
    await recovery.locator('#refresh-memory').click();
    await recovery.getByText('A fresh page. Nothing is saved yet.', {exact: true}).waitFor();
    passed++;

    await addDeletionFixture('Synthetic unrelated deletion target');
    await addDeletionFixture('Synthetic unrelated edit must stay selected');
    await memoryRow('Synthetic unrelated edit must stay selected').getByRole('button', {name: 'Edit', exact: true}).click();
    const unrelatedDelete = await holdApi('**/api/memory/*', 'DELETE');
    await confirmDelete('Synthetic unrelated deletion target'); await unrelatedDelete.started; unrelatedDelete.release();
    await recovery.getByText('Memory deleted.', {exact: true}).waitFor();
    assert.equal(await recovery.locator('#memory-text').inputValue(), 'Synthetic unrelated edit must stay selected');
    assert.equal(await recovery.locator('#memory-form-title').textContent(), 'Edit this memory');
    assert.equal(await recovery.locator('#cancel-memory-edit').isVisible(), true);
    await unrelatedDelete.remove();
    passed++;

    const unchangedSingleDelete = await holdApi('**/api/memory/*', 'DELETE');
    await confirmDelete('Synthetic unrelated edit must stay selected'); await unchangedSingleDelete.started; unchangedSingleDelete.release();
    await recovery.waitForFunction(() => document.getElementById('memory-text').value === '' && document.getElementById('cancel-memory-edit').hidden);
    assert.equal(await recovery.locator('#memory-list .list-item').count(), 0);
    await unchangedSingleDelete.remove();
    await recovery.close();
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
    await voiceContext.route('**/*', async route => {
      if (!route.request().url().startsWith(base)) { external.push(new URL(route.request().url()).origin); await route.abort(); }
      else await route.continue();
    });
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
    vp.on('pageerror', e => errors.push(e.message));
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
    const emit = event => vp.evaluate(event => window.__probe.channel.onmessage({data: JSON.stringify(event)}), event);
    const sent = type => vp.evaluate(type => window.__probe.sends.filter(event => event.type === type), type);
    async function latestRequest() { return (await sent('response.create')).at(-1); }
    async function created(id, request = null) {
      await emit({type: 'response.created', response: {id, ...(request ? {metadata: request.response.metadata} : {})}});
    }
    const done = (id, status = 'completed') => emit({type: 'response.done', response: {id, status}});
    async function typeTurn(text) {
      await vp.locator('#chat-input').fill(text);
      await vp.locator('#send-chat').click();
    }
    async function completeLatest(id) { await created(id, await latestRequest()); await done(id); }
    async function cancelCount(id) { return (await sent('response.cancel')).filter(event => event.response_id === id).length; }

    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    const greetingRequest = await latestRequest();
    await typeTurn('A synthetic cloud test');
    assert.equal((await sent('response.create')).length, 1, 'Greeting creation must be acknowledged first');
    assert.equal((await sent('conversation.item.create')).length, 1, 'Queued text must not be sent yet');
    assert.equal(await vp.locator('#send-chat').isDisabled(), true);
    await vp.locator('#chat-input').fill('Preserve this next draft');
    await vp.locator('#chat-form').evaluate(form => form.requestSubmit());
    assert.equal(await vp.locator('#chat-input').inputValue(), 'Preserve this next draft');
    await created('greeting', greetingRequest);
    assert.equal(await cancelCount('greeting'), 1);
    assert.equal((await sent('output_audio_buffer.clear')).length, 1, 'Late-created cancellation must also clear queued audio');
    assert.equal(await vp.locator('#remote-audio').evaluate(audio => audio.muted), true);
    await done('unrelated-response');
    assert.equal((await sent('response.create')).length, 1, 'An unrelated done event cannot release the queue');
    await done('greeting', 'cancelled');
    assert.equal((await sent('response.create')).length, 2);
    assert.equal((await sent('conversation.item.create')).at(-1).item.content[0].text, 'A synthetic cloud test');
    assert.equal(await vp.locator('#send-chat').isDisabled(), false);
    assert.equal(await vp.locator('#chat-input').inputValue(), 'Preserve this next draft');
    passed++;

    // A current response is cancelled once; late completion cannot release a
    // different response, and cancelled transcript/audio events stay inert.
    await created('typed-first', await latestRequest());
    await typeTurn('A queued follow-up');
    assert.equal(await cancelCount('typed-first'), 1);
    await done('greeting', 'cancelled');
    assert.equal((await sent('response.create')).length, 2);
    await emit({type: 'response.output_audio_transcript.delta', response_id: 'typed-first', delta: 'Cancelled text must not appear'});
    assert.equal(await vp.getByText('Cancelled text must not appear', {exact: true}).count(), 0);
    await done('typed-first', 'cancelled');
    assert.equal((await sent('response.create')).length, 3);
    await created('typed-follow-up', await latestRequest());
    await emit({type: 'output_audio_buffer.started', response_id: 'typed-follow-up'});
    await done('typed-follow-up');
    await emit({type: 'output_audio_buffer.stopped', response_id: 'typed-first'});
    const clearsBefore = (await sent('output_audio_buffer.clear')).length;
    await vp.locator('#interrupt').click();
    assert.equal((await sent('output_audio_buffer.clear')).length, clearsBefore + 1, 'Old audio stop cannot hide current playback');
    assert.equal(await cancelCount('typed-follow-up'), 0, 'Completed generation only needs playback cleared');
    passed++;

    // Native automatic VAD responses are tracked without manufacturing an
    // extra client response.create. Typed follow-ups still wait for their done.
    const beforeAutomatic = (await sent('response.create')).length;
    await emit({type: 'input_audio_buffer.speech_started'});
    await created('automatic-turn');
    assert.equal(await vp.locator('#remote-audio').evaluate(audio => audio.muted), false);
    await emit({type: 'response.output_audio_transcript.delta', response_id: 'automatic-turn', delta: 'Synthetic automatic transcript'});
    await vp.getByText('Synthetic automatic transcript', {exact: true}).waitFor();
    await emit({type: 'input_audio_buffer.speech_started'});
    await created('automatic-barge-in');
    await done('automatic-turn', 'cancelled');
    assert.equal(await vp.locator('#voice-state').textContent(), 'Wanda is responding · mic on');
    assert.equal(await vp.locator('#remote-audio').evaluate(audio => audio.muted), false);
    assert.equal((await sent('response.create')).length, beforeAutomatic);
    await typeTurn('After an automatic turn');
    assert.equal(await cancelCount('automatic-barge-in'), 1);
    assert.equal(await cancelCount('automatic-turn'), 0);
    assert.equal((await sent('response.create')).length, beforeAutomatic);
    await done('automatic-barge-in', 'cancelled');
    await completeLatest('after-automatic');
    assert.equal((await sent('response.create')).length, beforeAutomatic + 1);
    passed++;

    // Interrupt is meaningful even before response.created, and a late created
    // event must neither unmute playback nor start a queued replacement.
    await typeTurn('Interrupt before creation');
    const earlyRequest = await latestRequest();
    const beforeEarlyCancel = (await sent('response.create')).length;
    await vp.locator('#interrupt').click();
    await created('early-interruption', earlyRequest);
    assert.equal(await cancelCount('early-interruption'), 1);
    assert.equal(await vp.locator('#remote-audio').evaluate(audio => audio.muted), true);
    await vp.locator('#interrupt').click();
    assert.equal(await cancelCount('early-interruption'), 1);
    await done('early-interruption', 'cancelled');
    assert.equal((await sent('response.create')).length, beforeEarlyCancel);
    passed++;

    // Preference changes coalesce around the single queued typed turn. Latest
    // language/tone arrive once, after cancellation, without losing the text.
    await created('automatic-style');
    const beforeStyleItems = (await sent('conversation.item.create')).length;
    const beforeStyleResponses = (await sent('response.create')).length;
    await vp.locator('#language').selectOption('pt');
    await vp.locator('#tone').selectOption('neutral');
    await typeTurn('Keep this typed message');
    await vp.locator('#language').selectOption('es');
    assert.equal(await cancelCount('automatic-style'), 1);
    assert.equal((await sent('conversation.item.create')).length, beforeStyleItems);
    await done('automatic-style', 'cancelled');
    const styleItems = (await sent('conversation.item.create')).slice(beforeStyleItems);
    assert.equal(styleItems.length, 2);
    assert.match(styleItems[0].item.content[0].text, /Spanish.*neutral, direct/);
    assert.equal(styleItems[1].item.content[0].text, 'Keep this typed message');
    assert.equal((await sent('response.create')).length, beforeStyleResponses + 1);
    await completeLatest('typed-with-style');
    passed++;

    // Automatic VAD may win the server-side race against a manual create. Only
    // the correlated rejected create can retry once; its text is never resent.
    await typeTurn('Synthetic collision');
    const collision = await latestRequest();
    const collisionItems = (await sent('conversation.item.create')).length;
    const collisionCreates = (await sent('response.create')).length;
    await created('automatic-collision');
    assert.equal(await cancelCount('automatic-collision'), 1);
    await emit({type: 'error', error: {code: 'conversation_already_has_active_response', event_id: collision.event_id}});
    assert.equal((await sent('response.create')).length, collisionCreates);
    await vp.locator('#language').selectOption('pt');
    await done('automatic-collision', 'cancelled');
    assert.equal((await sent('response.create')).length, collisionCreates + 1);
    assert.equal((await sent('conversation.item.create')).length, collisionItems + 1);
    assert.match((await sent('conversation.item.create')).at(-1).item.content[0].text, /Portuguese.*neutral, direct/);
    assert.equal((await sent('conversation.item.create')).filter(event => event.item.content[0].text === 'Synthetic collision').length, 1);
    await completeLatest('collision-retry');
    passed++;

    await typeTurn('Synthetic reordered collision');
    const reordered = await latestRequest();
    const reorderedItems = (await sent('conversation.item.create')).length;
    const reorderedCreates = (await sent('response.create')).length;
    await emit({type: 'error', error: {code: 'conversation_already_has_active_response', event_id: reordered.event_id}});
    assert.equal((await sent('response.create')).length, reorderedCreates);
    await created('automatic-reordered');
    await done('automatic-reordered', 'cancelled');
    assert.equal((await sent('response.create')).length, reorderedCreates + 1);
    assert.equal((await sent('conversation.item.create')).length, reorderedItems);
    await completeLatest('reordered-retry');
    passed++;

    await typeTurn('Disconnect the outstanding request');
    const disconnectedRequest = await latestRequest();
    await typeTurn('Must stay unsent after disconnect');
    const beforeDisconnect = (await sent('response.create')).length;
    await vp.evaluate(() => { window.__probe.oldMessage = window.__probe.channel.onmessage; });
    await vp.locator('#disconnect').click();
    await vp.evaluate(request => {
      window.__probe.oldMessage({data: JSON.stringify({type: 'response.created', response: {id: 'late-disconnected', metadata: request.response.metadata}})});
      window.__probe.oldMessage({data: JSON.stringify({type: 'response.done', response: {id: 'late-disconnected', status: 'completed'}})});
    }, disconnectedRequest);
    assert.equal((await sent('response.create')).length, beforeDisconnect);
    assert.equal((await sent('conversation.item.create')).some(event => event.item.content[0].text === 'Must stay unsent after disconnect'), false);
    await vp.getByText('Not sent · voice interrupted or disconnected.', {exact: true}).waitFor();
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
    await completeLatest('timer-greeting');
    await vp.clock.fastForward(5 * 60 * 1000 + 1);
    assert.equal(await vp.locator('#microphone-label').textContent(), 'Mic off');
    assert.equal(await vp.locator('#voice-state').textContent(), 'Five-minute session ended · mic off');
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

    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    await typeTurn('Unsent on creation timeout');
    const beforeCreationTimeout = (await sent('response.create')).length;
    await vp.clock.fastForward(15001);
    assert.equal(await vp.locator('#voice-state').textContent(), 'Voice acknowledgement timed out · mic off');
    assert.equal((await sent('response.create')).length, beforeCreationTimeout);
    assert.equal((await sent('conversation.item.create')).some(event => event.item.content[0].text === 'Unsent on creation timeout'), false);
    assert.equal(await vp.evaluate(() => window.__probe.stops), 6);
    passed++;

    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    await created('missing-cancel-ack', await latestRequest());
    await typeTurn('Unsent on cancellation timeout');
    const beforeCancelTimeout = (await sent('response.create')).length;
    await emit({type: 'error', error: {code: 'response_cancel_not_active'}});
    assert.equal((await sent('response.create')).length, beforeCancelTimeout, 'Cancel error is not a done acknowledgement');
    await vp.clock.fastForward(15001);
    assert.equal(await vp.locator('#voice-state').textContent(), 'Voice acknowledgement timed out · mic off');
    assert.equal((await sent('conversation.item.create')).some(event => event.item.content[0].text === 'Unsent on cancellation timeout'), false);
    assert.equal(await vp.evaluate(() => window.__probe.stops), 7);
    passed++;

    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    await completeLatest('bounded-retry-greeting');
    await typeTurn('Never retry twice');
    const firstRejected = await latestRequest();
    await created('bounded-automatic-one');
    await emit({type: 'error', error: {code: 'conversation_already_has_active_response', event_id: firstRejected.event_id}});
    await done('bounded-automatic-one', 'cancelled');
    const finalRejected = await latestRequest();
    assert.notEqual(finalRejected.event_id, firstRejected.event_id);
    await created('bounded-automatic-two');
    const beforeRepeatedError = (await sent('response.create')).length;
    await emit({type: 'error', error: {code: 'conversation_already_has_active_response', event_id: finalRejected.event_id}});
    assert.equal(await vp.locator('#microphone-label').textContent(), 'Mic off');
    assert.equal((await sent('response.create')).length, beforeRepeatedError);
    assert.equal((await sent('conversation.item.create')).filter(event => event.item.content[0].text === 'Never retry twice').length, 1);
    assert.equal(await vp.evaluate(() => window.__probe.stops), 8);
    passed++;

    await connect();
    await vp.locator('#microphone-label').filter({hasText: 'Mic on · OpenAI'}).waitFor();
    const beforeUncorrelatedError = (await sent('response.create')).length;
    await emit({type: 'error', error: {code: 'conversation_already_has_active_response', event_id: 'unrelated-client-event'}});
    assert.equal(await vp.locator('#microphone-label').textContent(), 'Mic off');
    assert.equal((await sent('response.create')).length, beforeUncorrelatedError);
    assert.equal(await vp.evaluate(() => window.__probe.stops), 9);
    assert.deepEqual(errors, []);
    assert.deepEqual(external, []);
    passed++;
    console.log(`PASS: ${passed} browser workflows; local-only requests, memory CRUD/export, encrypted backup/restore, home permissions/outage, responsive layout, and mocked voice sequencing/consent/cancellation/timeout.`);
  } finally {
    if (browser) await browser.close();
    child.kill('SIGTERM');
    await new Promise(resolve => { if (child.exitCode !== null) resolve(); else { child.once('exit', resolve); setTimeout(resolve, 3000); } });
    if (child.exitCode === null) child.kill('SIGKILL');
    fs.rmSync(dataDir, {recursive: true, force: true});
  }
}
main().catch(error => { console.error(error.stack); process.exitCode = 1; });
