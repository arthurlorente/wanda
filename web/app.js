/* Wanda V0. No external dependencies, analytics, or implicit microphone access. */
"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const state = {status: null, memories: [], memoryEnabled: false, panel: "conversation", home: null,
    editId: null, memorySaving: false, memoryFormRevision: 0, busy: false, chatEpoch: 0,
    chatDraftRevision: 0, homePending: new Set()};
  const backup = {busy: false, payload: null, summary: null, page: 0, generation: 0};
  const fragment = new URLSearchParams(location.hash.slice(1));
  let capability = fragment.get("token") || "";
  // Remove the launch capability before any requests or UI navigation.
  if (location.hash) history.replaceState(null, "", location.pathname + location.search);
  try {
    if (capability) sessionStorage.setItem("wanda-capability", capability);
    else capability = sessionStorage.getItem("wanda-capability") || "";
  } catch (_) { /* A fragment launch still works if session storage is unavailable. */ }
  let noticeTimer;
  const voice = {epoch: 0, pc: null, stream: null, channel: null, abort: null,
    phase: "off", responsePhase: "idle", request: null, pendingTurn: null, sequence: 0,
    responses: new Map(), finishedResponses: new Map(), awaitingAutomatic: false,
    playingId: null, ackTimer: null, ackKey: "", timer: null, handshakeTimer: null,
    healthTimer: null, healthAbort: null, transcripts: new Map()};

  function tell(message, error = false) {
    $("notice").textContent = message;
    $("notice").classList.toggle("error", error);
    $("notice").hidden = false;
    clearTimeout(noticeTimer);
    if (!error) noticeTimer = setTimeout(() => { $("notice").hidden = true; }, 7000);
  }
  function guard(handler) {
    return async (event) => {
      try { await handler(event); }
      catch (error) { tell(error.message || "Something did not complete. Please try again.", true); }
    };
  }
  async function api(path, options = {}) {
    if (!capability) throw new Error("Open Wanda using the launcher to start a private local session.");
    const method = options.method || "GET";
    const mutation = !["GET", "HEAD"].includes(method);
    const controller = options.signal ? null : new AbortController();
    const timeout = controller && setTimeout(() => controller.abort(), 35000);
    try {
      const response = await fetch(path, {
        method, credentials: "omit", cache: "no-store",
        headers: {"Authorization": "Bearer " + capability, "Content-Type": "application/json"},
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: options.signal || controller.signal,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Wanda could not complete that request.");
      return data;
    } catch (error) {
      if (error.name === "AbortError") throw new Error(mutation
        ? "The request stopped or timed out. It may already have completed. Check the current state before trying again."
        : "The request stopped or timed out. You can refresh and try again.");
      if (error instanceof TypeError) throw new Error(mutation
        ? "The connection was interrupted. The request may already have completed. Check the current state before trying again."
        : "Wanda is not reachable. Start the launcher again if it has stopped.");
      throw error;
    } finally { clearTimeout(timeout); }
  }
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function action(label, callback, className = "text-button") {
    const button = node("button", label, className);
    button.type = "button";
    button.addEventListener("click", guard(callback));
    return button;
  }
  function empty(element, text) {
    element.replaceChildren(node("p", text, "empty-state"));
  }
  function timeLabel(value) {
    return value ? new Date(value * 1000).toLocaleString() : "No expiry";
  }
  function categoryLabel(value) { return String(value || "memory").replaceAll("_", " "); }
  function changePanel(panel) {
    state.panel = panel;
    // Leaving Memory discards decrypted text even if a preview or merge is in
    // flight. A submitted merge still finishes at the server and reports its
    // actual result; only the browser's local preview is discarded here.
    if (panel !== "memory") clearBackupPreview();
    for (const section of document.querySelectorAll(".panel")) section.hidden = section.id !== panel + "-panel";
    for (const button of document.querySelectorAll(".nav-button")) {
      const current = button.dataset.panel === panel;
      button.classList.toggle("active", current);
      if (current) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    }
    $("page-label").textContent = {conversation: "YOUR EVERYDAY COMPANION", memory: "YOUR LOCAL MEMORY", home: "YOUR HOME, YOUR RULES", privacy: "YOUR PRIVACY CONTROLS"}[panel];
    if (panel === "memory") refreshMemory().catch((error) => tell(error.message, true));
    if (panel === "home") refreshHome().catch((error) => tell(error.message, true));
    if (panel === "privacy") refreshDisclosures().catch((error) => tell(error.message, true));
  }
  document.querySelectorAll("[data-panel]").forEach((button) => button.addEventListener("click", () => changePanel(button.dataset.panel)));

  function confirmChoice(title, description, label = "Confirm", audio = false) {
    const dialog = $("confirm-dialog");
    if (dialog.open) return Promise.resolve(false);
    $("confirm-title").textContent = title;
    $("confirm-description").textContent = description;
    $("confirm-accept").textContent = label;
    $("audio-consent-label").hidden = !audio;
    $("audio-consent").checked = false;
    $("confirm-accept").disabled = audio;
    $("audio-consent").onchange = () => { $("confirm-accept").disabled = audio && !$("audio-consent").checked; };
    dialog.returnValue = "cancel";
    dialog.showModal();
    return new Promise((resolve) => dialog.addEventListener("close", () => {
      resolve(dialog.returnValue === "confirm" && (!audio || $("audio-consent").checked));
    }, {once: true}));
  }

  function addMessage(who, text, mode = "demo") {
    const row = node("article", undefined, "message " + who);
    const avatar = node("span", who === "user" ? "YOU" : "w", "message-avatar");
    avatar.setAttribute("aria-hidden", "true");
    const body = node("div", undefined, "message-body");
    body.append(node("strong", who === "user" ? "You" : mode === "live" ? "Wanda · cloud voice" : "Wanda · local demo"));
    const paragraph = node("p", text);
    body.append(paragraph); row.append(avatar, body); $("messages").append(row);
    $("messages").scrollTop = $("messages").scrollHeight;
    return {body, paragraph};
  }
  function greeting() {
    addMessage("assistant", "Hello. I'm Wanda. This local demo is a small beginning: a place to try privacy controls, local memory, and home permissions. What shall we explore?");
  }
  function browserSpeak(text) {
    if (voice.phase !== "off" || backupPrivacyActive() || !$("read-aloud").checked || !("speechSynthesis" in window)) return;
    const localVoice = speechSynthesis.getVoices().find((item) => item.localService && item.lang.toLowerCase().startsWith($("language").value));
    if (!localVoice) { tell("No local browser voice is available for this language. Text replies still work."); return; }
    speechSynthesis.cancel();
    const speech = new SpeechSynthesisUtterance(text);
    speech.voice = localVoice; speech.lang = localVoice.lang; speech.rate = 0.97;
    speechSynthesis.speak(speech);
  }
  function stopBrowserSpeech() { if ("speechSynthesis" in window) speechSynthesis.cancel(); }
  async function sendChat(text) {
    if (state.busy || !text.trim()) return;
    if (voice.phase === "connecting") { tell("Wait for live voice to connect, or disconnect to use the local demo."); return; }
    const clean = text.trim().slice(0, 4000);
    if (voice.phase === "live" && voice.pendingTurn?.kind === "typed") {
      tell("One message is waiting for Wanda to stop. Your next draft is still in the text box."); return;
    }
    $("chat-input").value = "";
    $("suggestions").hidden = true;
    if (voice.phase === "live") {
      const message = addMessage("user", clean, "live");
      const note = node("span", "Waiting to send to cloud voice…", "message-note");
      message.body.append(note);
      queueLiveTurn({kind: "typed", text: clean, note});
      return;
    }
    state.busy = true; $("send-chat").disabled = true; $("connect-voice").disabled = true;
    const chatEpoch = state.chatEpoch, draftRevision = state.chatDraftRevision;
    const submitted = addMessage("user", clean);
    try {
      let data;
      try {
        data = await api("/api/chat", {method: "POST", body: {text: clean, language: $("language").value, tone: $("tone").value}});
      } catch (error) {
        if (chatEpoch !== state.chatEpoch) return;
        submitted.body.append(node("span", "Response unconfirmed. Check local Memory before resending; approved details may already have been saved.", "message-note"));
        // A late failure must not replace a newer draft or resurrect cleared
        // text. Restoring a draft never retries the request automatically.
        if (!$("chat-input").value && draftRevision === state.chatDraftRevision) $("chat-input").value = text.slice(0, 4000);
        throw error;
      }
      if (chatEpoch !== state.chatEpoch) return;
      const message = addMessage("assistant", data.reply);
      if (data.memory_saved?.length) message.body.append(node("span", "A consented detail was saved locally. Review it in Memory.", "message-note"));
      if (data.memory_candidates?.length) {
        message.body.append(node("span", "There is a detail to review before saving.", "message-note"));
        for (const candidate of data.memory_candidates) {
          const item = typeof candidate === "string" ? {text: candidate, category: "sensitive"} : candidate;
          if (!item.text) continue;
          message.body.append(action("Review proposed memory", () => {
            changePanel("memory"); resetMemoryForm();
            $("memory-text").value = item.text;
            $("memory-category").value = item.category || "sensitive";
            $("memory-approved").checked = false;
            $("memory-text").focus();
          }));
        }
      }
      browserSpeak(data.reply);
      try { await refreshMemory(); }
      catch (_) {
        if (chatEpoch === state.chatEpoch) tell("Wanda replied, but the memory list could not refresh. Open Memory and choose Refresh to check saved details.", true);
      }
    } finally {
      state.busy = false; $("send-chat").disabled = false;
      $("connect-voice").disabled = voice.phase !== "off" || backupPrivacyActive() || !state.status?.voice?.configured;
    }
  }
  $("chat-form").addEventListener("submit", guard(async (event) => { event.preventDefault(); await sendChat($("chat-input").value); }));
  $("chat-input").addEventListener("input", () => { ++state.chatDraftRevision; });
  $("chat-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); $("chat-form").requestSubmit(); }
  });
  document.querySelectorAll("[data-suggestion]").forEach((button) => button.addEventListener("click", guard(() => sendChat(button.dataset.suggestion))));
  $("clear-chat").addEventListener("click", guard(async () => {
    if (voice.phase !== "off") {
      if (!await confirmChoice("Clear this conversation?", "This disconnects live voice and clears the chat from this page. It cannot erase data already processed by the cloud provider. Saved local memories are separate.", "Disconnect and clear")) return;
      disconnectVoice();
    }
    ++state.chatEpoch;
    stopBrowserSpeech(); $("messages").replaceChildren(); $("suggestions").hidden = false; greeting();
    tell("Chat cleared from this page. Saved memories are unchanged.");
  }));
  $("read-aloud").addEventListener("change", () => {
    if (!$("read-aloud").checked) stopBrowserSpeech();
    else if (!("speechSynthesis" in window)) { $("read-aloud").checked = false; tell("This browser does not provide speech synthesis."); }
  });

  async function refreshMemory() {
    const data = await api("/api/memory");
    state.memories = data.memories || [];
    state.memoryEnabled = data.enabled;
    $("memory-enabled").checked = data.enabled;
    $("memory-status").textContent = data.enabled ? "ON" : "OFF";
    $("memory-count").textContent = state.memories.length;
    $("memory-form").querySelector('button[type="submit"]').disabled = !data.enabled || state.memorySaving;
    $("memory-form-title").textContent = data.enabled ? (state.editId ? "Edit this memory" : "Add a memory") : "Enable memory to add or edit";
    renderMemories();
    updateBackupControls();
  }
  function renderMemories() {
    const list = $("memory-list"); list.replaceChildren();
    const query = $("memory-search").value.toLocaleLowerCase();
    const memories = state.memories.filter((memory) => memory.text.toLocaleLowerCase().includes(query));
    if (!memories.length) { empty(list, query ? "No matching memories." : "A fresh page. Nothing is saved yet."); return; }
    for (const memory of memories) {
      const item = node("article", undefined, "list-item");
      item.append(node("p", memory.text), node("div", categoryLabel(memory.category) + " · " + timeLabel(memory.expires_at), "item-meta"));
      if (memory.disclosure_categories?.length) item.append(node("div", "Disclosure rules required: " + memory.disclosure_categories.map(categoryLabel).join(" + ") + ". V0 does not send memories to voice.", "item-meta"));
      const controls = node("div", undefined, "item-actions");
      controls.append(action("Edit", () => editMemory(memory)), action("Delete", async () => {
        if (!await confirmChoice("Forget this memory?", memory.text, "Delete memory")) return;
        await api("/api/memory/" + encodeURIComponent(memory.id), {method: "DELETE"});
        if (state.editId === memory.id) resetMemoryForm();
        await refreshMemory(); tell("Memory deleted.");
      }));
      item.append(controls); list.append(item);
    }
  }
  function resetMemoryForm() {
    ++state.memoryFormRevision;
    state.editId = null; $("memory-form").reset();
    $("memory-form-title").textContent = "Add a memory"; $("cancel-memory-edit").hidden = true;
  }
  function editMemory(memory) {
    ++state.memoryFormRevision;
    state.editId = memory.id; $("memory-form-title").textContent = "Edit this memory";
    $("memory-text").value = memory.text; $("memory-category").value = memory.category;
    $("memory-approved").checked = false;
    const date = memory.expires_at ? new Date(memory.expires_at * 1000) : null;
    $("memory-expiry").value = date ? new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16) : "";
    $("cancel-memory-edit").hidden = false; $("memory-text").focus();
  }
  $("memory-enabled").addEventListener("change", guard(async () => {
    const enabled = $("memory-enabled").checked;
    try { await api("/api/memory/consent", {method: "POST", body: {enabled}}); tell(enabled ? "Local memory is enabled. You can review and delete saved details here." : "New memory saving is paused. Existing memories remain available for review or deletion."); }
    finally { await refreshMemory(); }
  }));
  $("memory-form").addEventListener("submit", guard(async (event) => {
    event.preventDefault();
    if (state.memorySaving) return;
    const editId = state.editId, revision = state.memoryFormRevision;
    const body = {text: $("memory-text").value, category: $("memory-category").value, approved: $("memory-approved").checked,
      expires_at: $("memory-expiry").value ? Math.floor(new Date($("memory-expiry").value).getTime() / 1000) : null};
    state.memorySaving = true;
    $("memory-form").setAttribute("aria-busy", "true");
    $("memory-form").querySelector('button[type="submit"]').disabled = true;
    try {
      await api(editId ? "/api/memory/" + encodeURIComponent(editId) : "/api/memory", {method: editId ? "PATCH" : "POST", body});
      if (state.memoryFormRevision === revision && state.editId === editId) resetMemoryForm();
      try { await refreshMemory(); }
      catch (_) { tell("Memory saved, but the list could not refresh. Choose Refresh to check saved details.", true); return; }
      tell("Memory saved on this computer.");
    } finally {
      state.memorySaving = false;
      $("memory-form").setAttribute("aria-busy", "false");
      $("memory-form").querySelector('button[type="submit"]').disabled = !state.memoryEnabled;
    }
  }));
  for (const type of ["input", "change"]) $("memory-form").addEventListener(type, () => { ++state.memoryFormRevision; });
  $("cancel-memory-edit").addEventListener("click", resetMemoryForm);
  $("memory-search").addEventListener("input", renderMemories);
  $("refresh-memory").addEventListener("click", guard(refreshMemory));
  $("clear-memory").addEventListener("click", guard(async () => {
    if (!await confirmChoice("Delete every saved memory?", "This removes all memories for this local owner. You can export a copy first. This cannot remove copies you exported or cloud-provider data.", "Delete all memories")) return;
    await api("/api/memory", {method: "DELETE"}); resetMemoryForm(); await refreshMemory(); tell("All local memories deleted.");
  }));
  $("export-memory").addEventListener("click", guard(async () => {
    prepareBackupPrivacy();
    const data = await api("/api/memory/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: "application/json"}));
    const link = node("a"); link.href = url; link.download = "wanda-private-memory-export.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000); tell("Plaintext memory export prepared. Anyone with the file can read it; keep it somewhere you trust.");
  }));

  function backupPrivacyActive() {
    return backup.busy || backup.payload !== null ||
      ["backup-password", "backup-password-confirm", "restore-password"].some((id) => $(id).value.length > 0) ||
      $("restore-file").files.length > 0;
  }
  function prepareBackupPrivacy() {
    stopBrowserSpeech();
    $("read-aloud").checked = false;
    if (voice.phase !== "off") {
      disconnectVoice("Backup controls opened · microphone off");
      tell("Live voice disconnected before handling your backup. The microphone and browser speech are off.");
    }
  }
  function clearBackupPasswords() {
    for (const id of ["backup-password", "backup-password-confirm", "restore-password"]) $(id).value = "";
  }
  function clearBackupPreview() {
    ++backup.generation;
    backup.payload = null; backup.summary = null; backup.page = 0;
    $("restore-preview").hidden = true;
    $("restore-memory-list").replaceChildren();
    $("restore-summary").textContent = "";
    $("restore-consent-note").textContent = "";
    $("restore-preview-limit").textContent = "";
    $("restore-preview-pages").hidden = true;
    $("restore-file").value = "";
    clearBackupPasswords();
    updateBackupControls();
  }
  function updateBackupControls() {
    $("backup-section").setAttribute("aria-busy", String(backup.busy));
    for (const id of ["create-backup", "preview-backup", "discard-backup-preview", "backup-password", "backup-password-confirm", "restore-password", "restore-file"]) $(id).disabled = backup.busy;
    $("merge-backup").disabled = backup.busy || !state.memoryEnabled || !backup.summary ||
      backup.summary.exceeds_capacity || backup.summary.restorable < 1;
    if (backup.payload) {
      $("restore-consent-note").textContent = !state.memoryEnabled ? "Enable local memory above before approving a restore. Existing memory and permissions are unchanged." :
        backup.summary?.exceeds_capacity ? "This merge exceeds local memory capacity. Nothing has been restored. Review existing memories before trying again." :
        "Local memory is enabled. Review these details and approve only information you have permission to store.";
    }
    $("connect-voice").disabled = voice.phase !== "off" || state.busy || backupPrivacyActive() || !state.status?.voice?.configured;
  }
  function setBackupBusy(busy, message = "") {
    backup.busy = busy;
    $("backup-operation-status").hidden = !message;
    $("backup-operation-status").textContent = message;
    updateBackupControls();
  }
  function downloadBackup(serialized) {
    const url = URL.createObjectURL(new Blob([serialized], {type: "application/json"}));
    const link = node("a"); link.href = url;
    link.download = "wanda-encrypted-memory-backup.json";
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function renderBackupPreview(payload, summary) {
    backup.payload = payload; backup.summary = summary; backup.page = 0;
    $("restore-preview").hidden = false;
    $("restore-summary").textContent = `${summary.total} memories in this backup · ${summary.restorable} can be merged · ${summary.duplicates} duplicates · ${summary.skipped_expired} expired. ${summary.existing} memories already on this computer.`;
    renderBackupPage(); updateBackupControls();
  }
  function renderBackupPage() {
    if (!backup.payload) return;
    const memories = backup.payload.memories;
    const start = backup.page * 50;
    const list = $("restore-memory-list"); list.replaceChildren();
    for (const memory of memories.slice(start, start + 50)) {
      const item = node("article", undefined, "list-item");
      item.append(node("p", memory.text), node("div", categoryLabel(memory.category) + " · " + timeLabel(memory.expires_at), "item-meta"));
      list.append(item);
    }
    if (!memories.length) empty(list, "This backup contains no memories.");
    $("restore-preview-limit").hidden = memories.length <= 50;
    $("restore-preview-limit").textContent = `Showing ${start + 1}–${Math.min(start + 50, memories.length)} of ${memories.length} memories. Use the page controls to review the rest. Approval merges all eligible entries.`;
    $("restore-preview-pages").hidden = memories.length <= 50;
    $("restore-previous-page").disabled = backup.page === 0;
    $("restore-next-page").disabled = start + 50 >= memories.length;
    list.scrollTop = 0;
  }
  $("restore-previous-page").addEventListener("click", () => { if (backup.page > 0) { --backup.page; renderBackupPage(); } });
  $("restore-next-page").addEventListener("click", () => {
    if (backup.payload && (backup.page + 1) * 50 < backup.payload.memories.length) { ++backup.page; renderBackupPage(); }
  });
  $("backup-section").addEventListener("focusin", prepareBackupPrivacy);
  for (const id of ["backup-password", "backup-password-confirm", "restore-password", "restore-file"]) {
    $(id).addEventListener("input", updateBackupControls);
    $(id).addEventListener("change", updateBackupControls);
  }
  $("backup-form").addEventListener("submit", guard(async (event) => {
    event.preventDefault();
    if (backup.busy) return;
    prepareBackupPrivacy();
    let password = $("backup-password").value;
    let confirmation = $("backup-password-confirm").value;
    clearBackupPreview();
    setBackupBusy(true, "Encrypting a backup in this browser…");
    try {
      if (!window.WandaBackup) throw new Error("Encrypted backups are unavailable in this browser. Please reload Wanda in a supported browser.");
      if (password !== confirmation) throw new Error("The passwords do not match. Enter both again; nothing was downloaded.");
      const payload = await api("/api/memory/backup");
      const serialized = await window.WandaBackup.encrypt(payload, password);
      downloadBackup(serialized);
      tell("Encrypted backup downloaded. Keep its password separately; Wanda cannot recover a lost password.");
    } finally {
      password = ""; confirmation = "";
      clearBackupPasswords(); setBackupBusy(false);
    }
  }));
  $("restore-form").addEventListener("submit", guard(async (event) => {
    event.preventDefault();
    if (backup.busy) return;
    prepareBackupPrivacy();
    let password = $("restore-password").value;
    const file = $("restore-file").files[0];
    clearBackupPreview(); setBackupBusy(true, "Decrypting and checking this backup locally…");
    const generation = backup.generation;
    try {
      if (!window.WandaBackup) throw new Error("Encrypted backups are unavailable in this browser. Please reload Wanda in a supported browser.");
      if (!file || file.size > window.WandaBackup.MAX_FILE_BYTES) throw new Error("Choose a Wanda encrypted backup file no larger than 12 MiB.");
      const payload = await window.WandaBackup.decrypt(await file.text(), password);
      password = "";
      if (backup.generation !== generation || state.panel !== "memory") {
        tell("Backup preview discarded because you left Memory. Nothing was restored."); return;
      }
      const summary = await api("/api/memory/restore/preview", {method: "POST", body: {backup: payload}});
      if (backup.generation !== generation || state.panel !== "memory") {
        tell("Backup preview discarded because you left Memory. Nothing was restored."); return;
      }
      renderBackupPreview(payload, summary);
      tell("Backup decrypted locally. Review the preview before approving a merge.");
    } finally {
      password = ""; clearBackupPasswords(); $("restore-file").value = ""; setBackupBusy(false);
    }
  }));
  $("discard-backup-preview").addEventListener("click", () => {
    clearBackupPreview(); tell("Backup preview discarded. No memories were restored.");
  });
  $("merge-backup").addEventListener("click", guard(async () => {
    if (backup.busy || !backup.payload || !backup.summary) return;
    const payload = backup.payload, generation = backup.generation;
    prepareBackupPrivacy(); setBackupBusy(true);
    try {
      const accepted = await confirmChoice("Merge these memories?", `${backup.summary.restorable} eligible memories will be added to this local owner's memory. Existing memories stay in place; duplicates and expired entries are skipped.\n\nOnly approve information you have permission to store. No cloud-disclosure rules or device permissions are restored.`, "Approve memory merge");
      if (!accepted) { clearBackupPreview(); tell("Restore cancelled. No memories were added."); return; }
      if (backup.generation !== generation || state.panel !== "memory") {
        tell("Backup preview was discarded before the merge started. Nothing was restored."); return;
      }
      const result = await api("/api/memory/restore", {method: "POST", body: {backup: payload, approved: true}});
      clearBackupPreview(); await refreshMemory();
      tell(`Restored ${result.restored} memories locally. Existing memories and permissions were preserved.`);
    } finally { clearBackupPasswords(); setBackupBusy(false); }
  }));

  async function refreshDisclosures() {
    const data = await api("/api/disclosures"); const list = $("disclosure-list"); list.replaceChildren();
    if (!data.grants?.length) { empty(list, "No disclosure rules. Saved memory stays local."); return; }
    for (const grant of data.grants) {
      const item = node("article", undefined, "list-item");
      item.append(node("p", `${grant.provider} · ${categoryLabel(grant.category)} · ${grant.allowed ? "Allowed" : "Denied"}`),
        node("div", `${grant.one_time ? "One use" : "Reusable"} · ${timeLabel(grant.expires_at)}`, "item-meta"),
        action("Revoke rule", async () => { await api("/api/disclosures/" + encodeURIComponent(grant.id), {method: "DELETE"}); await refreshDisclosures(); tell("Disclosure rule revoked."); }));
      list.append(item);
    }
  }
  $("disclosure-form").addEventListener("submit", guard(async (event) => {
    event.preventDefault();
    await api("/api/disclosures", {method: "POST", body: {provider: "openai", category: $("disclosure-category").value,
      allowed: $("disclosure-allowed").value === "true", one_time: $("disclosure-one-time").checked,
      expires_at: Math.floor(Date.now() / 1000) + Number($("disclosure-duration").value)}});
    await refreshDisclosures(); tell("Permission rule saved. V0 still sends no saved memories to cloud voice.");
  }));

  async function requestHomeAction(device, actionName) {
    if (state.homePending.has(device.entity_id)) return;
    state.homePending.add(device.entity_id);
    document.querySelectorAll("[data-device-action]").forEach((button) => {
      if (button.dataset.deviceAction === device.entity_id) button.disabled = true;
    });
    try {
    const body = {entity_id: device.entity_id, action: actionName, request_id: crypto.randomUUID()};
    let result = await api("/api/home/action", {method: "POST", body});
    if (result.status === "confirmation_required") {
      const accepted = await confirmChoice("Approve this home action?", `${device.name}: ${actionName.replaceAll("_", " ")}\n${state.home?.mode === "mock" ? "This operates a simulated device." : "This may operate a real configured device."}\nPermission and device state will be checked again.`, "Approve this action");
      if (!accepted) { tell("Action cancelled. No confirmation was sent."); return; }
      result = await api("/api/home/action", {method: "POST", body: {...body, confirmation_id: result.confirmation_id}});
    }
    tell(result.message || result.status, result.status !== "verified"); await refreshHome();
    } finally {
      state.homePending.delete(device.entity_id);
      document.querySelectorAll("[data-device-action]").forEach((button) => {
        if (button.dataset.deviceAction === device.entity_id) button.disabled = false;
      });
    }
  }
  async function refreshHome() {
    const data = await api("/api/home"); state.home = data;
    $("home-mode").textContent = data.mode === "mock" ? "MOCK HOME · SIMULATED DEVICES" : "HOME ASSISTANT · REAL ADAPTER";
    $("outage-control").hidden = data.mode !== "mock";
    $("home-description").textContent = data.mode === "mock" ? "Practice with simulated devices. Permissions start denied and each action is checked on the server." : "Home Assistant adapter configured. These controls may operate real allowlisted devices; verify reported state before proceeding. Live behavior needs manual verification.";
    const grid = $("devices"), selector = $("grant-device"); const selected = selector.value;
    grid.replaceChildren(); selector.replaceChildren();
    for (const device of data.devices || []) {
      const card = node("section", undefined, "device-card" + (device.state === "on" ? " on" : ""));
      card.append(node("span", "☼", "device-icon"), node("h2", device.name), node("p", "Reported state: " + device.state));
      const controls = node("div", undefined, "button-row");
      controls.append(action("Turn on", () => requestHomeAction(device, "turn_on"), "secondary-button"), action("Turn off", () => requestHomeAction(device, "turn_off"), "secondary-button"));
      for (const button of controls.children) { button.dataset.deviceAction = device.entity_id; button.disabled = state.homePending.has(device.entity_id); }
      card.append(controls); grid.append(card);
      const option = node("option", device.name); option.value = device.entity_id; selector.append(option);
    }
    if ([...selector.options].some((option) => option.value === selected)) selector.value = selected;
    if (!data.devices?.length) empty(grid, "No device state is available. The home adapter may be offline; no action is assumed successful.");
    const grants = $("home-grants"); grants.replaceChildren();
    for (const grant of data.grants || []) {
      const item = node("article", undefined, "list-item");
      const name = data.devices?.find((device) => device.entity_id === grant.entity_id)?.name || grant.entity_id;
      item.append(node("p", `${name} · ${String(grant.action).replaceAll("_", " ")}`), node("div", `${grant.confirmation ? "Confirmation required" : "No extra confirmation"} · ${timeLabel(grant.expires_at)}`, "item-meta"),
        action("Revoke permission", async () => { await api("/api/home/grants/" + encodeURIComponent(grant.id), {method: "DELETE"}); await refreshHome(); tell("Device permission revoked."); }));
      grants.append(item);
    }
    if (!data.grants?.length) empty(grants, "No permissions yet. Device actions are denied until you grant a scope.");
    const audit = $("home-audit"); audit.replaceChildren();
    for (const entry of (data.audit || []).slice().reverse().slice(0, 20)) {
      const item = node("article", undefined, "list-item");
      item.append(node("p", `${entry.entity_id || "Home"} · ${String(entry.action || "request").replaceAll("_", " ")} · ${entry.status || entry.result || "Recorded"}`));
      if (entry.message) item.append(node("div", entry.message, "item-meta"));
      audit.append(item);
    }
    if (!data.audit?.length) empty(audit, "Actions and denied requests will appear here. This activity list resets on restart.");
  }
  $("home-grant-form").addEventListener("submit", guard(async (event) => {
    event.preventDefault();
    await api("/api/home/grants", {method: "POST", body: {entity_id: $("grant-device").value, action: $("grant-action").value,
      confirmation: $("grant-confirmation").checked, expires_at: Math.floor(Date.now() / 1000) + Number($("grant-duration").value)}});
    await refreshHome(); tell("Permission granted for this device and action.");
  }));
  $("home-outage").addEventListener("change", guard(async () => {
    const offline = $("home-outage").checked;
    try { await api("/api/home/outage", {method: "POST", body: {offline}}); await refreshHome(); tell(offline ? "Simulated home outage enabled. Memory and the local chat still work." : "Simulated home connection restored."); }
    catch (error) { $("home-outage").checked = !offline; throw error; }
  }));
  $("refresh-home").addEventListener("click", guard(refreshHome));

  function setVoiceState(phase, text) {
    voice.phase = phase;
    $("voice-state").textContent = text;
    $("voice-state").classList.toggle("listening", phase === "live");
    $("microphone-label").textContent = phase === "live" ? "Mic on · OpenAI" : phase === "connecting" ? "Mic connecting" : "Mic off";
    $("connect-voice").disabled = phase !== "off" || state.busy || backupPrivacyActive() || !state.status?.voice?.configured;
    $("disconnect").disabled = phase === "off";
    $("send-chat").disabled = state.busy || voice.pendingTurn?.kind === "typed";
    $("chat-input").placeholder = phase === "live" ? "Message cloud voice (sent to OpenAI)…" : "What's on your mind?";
    document.body.classList.toggle("live", phase === "live");
    const banner = document.querySelector(".mode-banner");
    const localSummary = state.status?.home?.mode === "homeassistant" ? "Scripted local conversation and real local memory. A real Home Assistant adapter is configured; device states need verification." : "Scripted conversation, real local memory, and practice home devices.";
    banner.replaceChildren(node("span", phase === "live" ? "LIVE CLOUD VOICE" : "LOCAL DEMO", "pill"), node("p", phase === "live" ? "Microphone audio and typed messages go to OpenAI. No saved memories or home tools are connected. Session ends automatically after 5 minutes." : localSummary));
  }
  function sendLive(event) {
    if (voice.channel?.readyState !== "open") throw new Error("Live voice is not connected. Disconnect and try again.");
    voice.channel.send(JSON.stringify(event));
  }
  function voiceProtocolFailure() {
    disconnectVoice("Voice response stopped · microphone off");
    tell("The voice provider could not finish this turn safely. The microphone is off; reconnect to try again.", true);
  }
  function syncLiveTurn() {
    const cancelling = [...voice.responses.values()].filter((response) => response.cancelled);
    voice.responsePhase = voice.request?.cancelled || cancelling.length || voice.awaitingAutomatic ? "cancelling"
      : voice.request ? "requested" : voice.responses.size ? "active" : "idle";
    $("send-chat").disabled = state.busy || voice.pendingTurn?.kind === "typed";
    // A missing creation/cancellation acknowledgement must not leave capture
    // running forever or allow an overlapping replacement response.
    const key = [voice.request ? voice.request.id + ":" + voice.request.cancelled : "",
      ...cancelling.map((response) => response.id), voice.awaitingAutomatic ? "automatic" : ""].join("|");
    if (key === voice.ackKey) return;
    clearTimeout(voice.ackTimer); voice.ackKey = key;
    if (!voice.request && !cancelling.length && !voice.awaitingAutomatic) return;
    const epoch = voice.epoch;
    voice.ackTimer = setTimeout(() => {
      if (voice.epoch !== epoch) return;
      disconnectVoice("Voice acknowledgement timed out · mic off");
      tell("Wanda did not receive a response acknowledgement in time. The microphone is off. Unsent queued messages were discarded; anything already sent may have been processed.", true);
    }, 15000);
  }
  function discardPendingTurn() {
    if (voice.pendingTurn?.note) voice.pendingTurn.note.textContent = voice.pendingTurn.sent
      ? "Sent to cloud voice · response interrupted." : "Not sent · voice interrupted or disconnected.";
    voice.pendingTurn = null;
  }
  function cancelLiveResponse(response) {
    if (response.cancelled) return;
    response.cancelled = true;
    sendLive({type: "response.cancel", response_id: response.id});
    sendLive({type: "output_audio_buffer.clear"});
  }
  function interruptVoice(discardPending = true) {
    stopBrowserSpeech();
    if (discardPending) discardPendingTurn();
    if (voice.channel?.readyState === "open") {
      try {
        // response.created may still be in flight. Keep the request until its
        // ID is known, then cancel that ID and wait for its matching done event.
        if (voice.request) voice.request.cancelled = true;
        for (const response of voice.responses.values()) cancelLiveResponse(response);
        if (voice.playingId) {
          const playing = voice.responses.get(voice.playingId) || voice.finishedResponses.get(voice.playingId);
          if (playing) playing.cancelled = true;
        }
        if (voice.playingId && !voice.responses.size) sendLive({type: "output_audio_buffer.clear"});
        $("remote-audio").muted = true; voice.playingId = null;
        syncLiveTurn();
        $("voice-state").textContent = voice.pendingTurn ? "Stopping Wanda · one message waiting" : "Interrupted · microphone still on";
      } catch (_) { voiceProtocolFailure(); }
    }
  }
  function queueLiveTurn(turn) {
    // A style update can accompany the one queued typed message. Neither rapid
    // preference changes nor a second Enter silently replace a typed message.
    if (turn.kind === "style" && voice.pendingTurn?.kind === "typed") voice.pendingTurn.preferences = turn.text;
    else {
      if (turn.kind === "typed" && voice.pendingTurn?.kind === "style") turn.preferences = voice.pendingTurn.text;
      voice.pendingTurn = turn;
    }
    interruptVoice(false);
    flushLiveTurn();
  }
  function flushLiveTurn() {
    if (voice.phase !== "live" || voice.request || voice.responses.size || voice.awaitingAutomatic || !voice.pendingTurn) return;
    const turn = voice.pendingTurn; voice.pendingTurn = null;
    const id = `wanda-${voice.epoch}-${++voice.sequence}`;
    // Mark requested before sending anything: a second UI action must observe
    // the request even before the provider emits response.created.
    voice.request = {id, eventId: id, turn, cancelled: false, sawAutomatic: false};
    try {
      // A preference can change while an already-sent typed turn is waiting
      // after a conflict. Deliver that new preference without repeating text.
      if (turn.preferences) {
        sendLive({type: "conversation.item.create", item: {type: "message", role: "user", content: [{type: "input_text", text: turn.preferences}]}});
        turn.preferences = null;
      }
      if (!turn.sent) {
        sendLive({type: "conversation.item.create", item: {type: "message", role: "user", content: [{type: "input_text", text: turn.text}]}});
        turn.sent = true;
        if (turn.note) turn.note.textContent = "Sent to cloud voice.";
      }
      sendLive({type: "response.create", event_id: id, response: {metadata: {wanda_turn: id}}});
      syncLiveTurn(); $("voice-state").textContent = "Waiting for Wanda · mic on";
    } catch (_) { voiceProtocolFailure(); }
  }
  function disconnectVoice(message = "Microphone is off") {
    ++voice.epoch;
    clearTimeout(voice.timer); clearTimeout(voice.handshakeTimer);
    clearTimeout(voice.ackTimer); voice.ackKey = "";
    discardPendingTurn(); voice.request = null; voice.awaitingAutomatic = false;
    voice.responses.clear(); voice.finishedResponses.clear(); voice.responsePhase = "idle";
    clearInterval(voice.healthTimer); voice.healthTimer = null;
    voice.healthAbort?.abort(); voice.healthAbort = null;
    voice.abort?.abort(); voice.abort = null;
    const channel = voice.channel, pc = voice.pc, stream = voice.stream;
    voice.channel = null; voice.pc = null; voice.stream = null;
    // Release capture first. Closing peer/data channels also ends remote audio.
    stream?.getTracks().forEach((track) => track.stop());
    if (channel) { channel.onclose = null; channel.onerror = null; channel.onmessage = null; channel.close(); }
    if (pc) { pc.onconnectionstatechange = null; pc.ontrack = null; pc.close(); }
    const audio = $("remote-audio"); audio.pause(); audio.srcObject = null; audio.muted = false;
    voice.playingId = null; voice.transcripts.clear(); stopBrowserSpeech(); setVoiceState("off", message);
  }
  function monitorLocalServer(epoch) {
    const check = async () => {
      if (voice.epoch !== epoch || voice.healthAbort) return;
      const controller = new AbortController(); voice.healthAbort = controller;
      const timer = setTimeout(() => controller.abort(), 2000);
      try { await api("/api/status", {signal: controller.signal}); }
      catch (_) {
        if (voice.epoch === epoch) {
          disconnectVoice("Local app stopped · microphone off");
          tell("The local Wanda service is unavailable. Live voice was disconnected and the microphone is off.", true);
        }
      } finally {
        clearTimeout(timer);
        if (voice.healthAbort === controller) voice.healthAbort = null;
      }
    };
    check();
    voice.healthTimer = setInterval(check, 3000);
  }
  function liveEvent(event, epoch) {
    if (voice.epoch !== epoch || voice.phase !== "live") return;
    let data; try { data = JSON.parse(event.data); } catch (_) { return; }
    if (data.type === "error") {
      // A cancel can race completion, but this error is not a done ack. Keep
      // waiting for the matching response.done (or the bounded timeout).
      if (data.error?.code === "response_cancel_not_active") return;
      const request = voice.request;
      if (data.error?.code === "conversation_already_has_active_response" && request && data.error.event_id === request.eventId) {
        // Server VAD can start a response before our response.create arrives.
        // Retry at most once, after that automatic response has finished. The
        // conversation item was already sent and must never be appended twice.
        voice.request = null;
        if (!request.cancelled && !voice.pendingTurn && !request.turn.retried) {
          request.turn.retried = true; voice.pendingTurn = request.turn;
        } else if (!request.cancelled && !voice.pendingTurn && request.turn.retried) {
          voiceProtocolFailure(); return;
        }
        voice.awaitingAutomatic = !request.sawAutomatic;
        interruptVoice(false); syncLiveTurn(); flushLiveTurn(); return;
      }
      disconnectVoice("Voice stopped after a provider error"); tell("The voice provider reported an error. The microphone is off; the local demo still works.", true); return;
    }
    if (data.type === "input_audio_buffer.speech_started") $("voice-state").textContent = "Listening · audio goes to OpenAI";
    if (data.type === "output_audio_buffer.started") {
      const response = voice.responses.get(data.response_id) || voice.finishedResponses.get(data.response_id);
      if (response && !response.cancelled) voice.playingId = data.response_id;
    }
    if (["output_audio_buffer.stopped", "output_audio_buffer.cleared"].includes(data.type) && voice.playingId === data.response_id) voice.playingId = null;
    if (data.type === "response.created") {
      const id = data.response?.id;
      if (typeof id !== "string" || !id) { voiceProtocolFailure(); return; }
      if (voice.responses.has(id) || voice.finishedResponses.has(id)) return;
      const request = voice.request;
      const manual = request && data.response.metadata?.wanda_turn === request.id;
      const response = {id, cancelled: false};
      voice.responses.set(id, response);
      if (manual) voice.request = null;
      else {
        if (request) request.sawAutomatic = true;
        voice.awaitingAutomatic = false;
      }
      try {
        if (voice.pendingTurn || (manual ? request.cancelled : request || voice.responsePhase === "cancelling")) {
          cancelLiveResponse(response); $("remote-audio").muted = true;
        } else {
          $("remote-audio").muted = false; $("voice-state").textContent = "Wanda is responding · mic on";
        }
        syncLiveTurn();
      } catch (_) { voiceProtocolFailure(); }
      return;
    }
    if (data.type === "response.done") {
      const response = voice.responses.get(data.response?.id);
      if (!response) return;
      if (data.response.status === "cancelled") response.cancelled = true;
      voice.responses.delete(response.id); voice.finishedResponses.set(response.id, response);
      if (voice.finishedResponses.size > 128) voice.finishedResponses.delete(voice.finishedResponses.keys().next().value);
      if (data.response?.status === "failed") {
        disconnectVoice("Voice response failed · mic off"); tell("The provider could not complete its response. The microphone is off; local features remain available.", true); return;
      }
      syncLiveTurn(); flushLiveTurn();
      if (voice.responsePhase === "idle") $("voice-state").textContent = "Connected · ready for your next thought";
      return;
    }
    if (data.type === "response.output_audio_transcript.delta") {
      const response = voice.responses.get(data.response_id) || voice.finishedResponses.get(data.response_id);
      if (!response || response.cancelled) return;
      const id = data.item_id || data.response_id || "current";
      if (!voice.transcripts.has(id)) voice.transcripts.set(id, addMessage("assistant", "", "live").paragraph);
      const paragraph = voice.transcripts.get(id);
      paragraph.textContent = (paragraph.textContent + String(data.delta || "")).slice(0, 20000);
      $("messages").scrollTop = $("messages").scrollHeight;
    }
  }
  function preferencesPrompt() {
    const language = {en: "English", pt: "Portuguese", es: "Spanish"}[$("language").value];
    return `Please use ${language} to start, with a ${$("tone").value === "neutral" ? "neutral, direct" : "warm, thoughtful"} tone. Follow me if I switch languages. Keep replies brief.`;
  }
  async function connectVoice() {
    if (voice.phase !== "off" || state.busy || backupPrivacyActive() || !state.status?.voice?.configured) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.RTCPeerConnection) throw new Error("This browser cannot start WebRTC audio. Use a supported browser on this computer.");
    if (!await confirmChoice("Start a cloud voice conversation?", "Microphone audio, including voices nearby, and connection metadata will reach OpenAI. Typed messages during this session also go to OpenAI. Saved local memories are not sent. No model device tools are enabled.\n\nProvider processing and retention policies apply. Use non-sensitive examples for this experimental demo. This session ends after 5 minutes; API usage may cost money.", "Connect microphone", true)) return;
    if (state.busy || voice.phase !== "off" || backupPrivacyActive()) return;
    const epoch = ++voice.epoch;
    stopBrowserSpeech(); setVoiceState("connecting", "Waiting for microphone permission…");
    voice.abort = new AbortController();
    voice.handshakeTimer = setTimeout(() => {
      if (voice.epoch === epoch) { disconnectVoice("Connection timed out · mic off"); tell("Voice connection timed out. The local demo remains available.", true); }
    }, 40000);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: {echoCancellation: true, noiseSuppression: true, autoGainControl: true}, video: false});
      if (voice.epoch !== epoch) { stream.getTracks().forEach((track) => track.stop()); return; }
      voice.stream = stream;
      monitorLocalServer(epoch);
      const pc = new RTCPeerConnection(); voice.pc = pc;
      for (const track of stream.getTracks()) {
        pc.addTrack(track, stream);
        track.addEventListener("ended", () => { if (voice.epoch === epoch) disconnectVoice("Microphone ended · mic off"); });
      }
      pc.ontrack = (event) => {
        if (voice.epoch !== epoch) return;
        const audio = $("remote-audio"); audio.srcObject = event.streams[0] || new MediaStream([event.track]);
        audio.play().catch(() => { if (voice.epoch === epoch) { disconnectVoice("Playback blocked · mic off"); tell("The browser blocked audio playback. Reconnect after allowing audio.", true); } });
      };
      pc.onconnectionstatechange = () => {
        if (voice.epoch === epoch && ["failed", "closed", "disconnected"].includes(pc.connectionState)) {
          disconnectVoice("Connection lost · mic off"); tell("Live voice disconnected. The microphone is off and local features remain available.", true);
        }
      };
      const channel = pc.createDataChannel("oai-events"); voice.channel = channel;
      channel.onmessage = (event) => liveEvent(event, epoch);
      channel.onclose = () => { if (voice.epoch === epoch) disconnectVoice("Voice channel closed · mic off"); };
      channel.onerror = () => { if (voice.epoch === epoch) disconnectVoice("Voice connection failed · mic off"); };
      channel.onopen = () => {
        if (voice.epoch !== epoch) return;
        clearTimeout(voice.handshakeTimer); setVoiceState("live", "Connected · audio goes to OpenAI");
        voice.timer = setTimeout(() => { if (voice.epoch === epoch) { disconnectVoice("Five-minute session ended · mic off"); tell("Live voice ended at the five-minute limit. Connect again only when you're ready."); } }, 5 * 60 * 1000);
        try {
          queueLiveTurn({kind: "greeting", text: preferencesPrompt() + " Briefly introduce yourself and your current limits."});
        } catch (_) { disconnectVoice("Connection failed · mic off"); }
      };
      await pc.setLocalDescription(await pc.createOffer());
      if (voice.epoch !== epoch) return;
      const answer = await api("/api/voice/session", {method: "POST", body: {sdp: pc.localDescription.sdp, audio_consent: true}, signal: voice.abort.signal});
      if (voice.epoch !== epoch) return;
      await pc.setRemoteDescription({type: "answer", sdp: answer.sdp});
    } catch (error) {
      if (voice.epoch !== epoch) return;
      disconnectVoice("Could not connect · microphone off");
      if (error.name === "NotAllowedError") throw new Error("Microphone permission was declined. The local text demo still works.");
      if (error.name === "NotFoundError") throw new Error("No microphone is available. The local text demo still works.");
      throw new Error(error.message || "Live voice could not connect. The microphone is off.");
    }
  }
  $("connect-voice").addEventListener("click", guard(connectVoice));
  $("disconnect").addEventListener("click", () => { disconnectVoice(); tell("Disconnected. The microphone is off."); });
  $("interrupt").addEventListener("click", guard(() => { interruptVoice(); if (voice.phase === "off") tell("Browser speech stopped. The microphone is off."); }));
  for (const id of ["language", "tone"]) $(id).addEventListener("change", guard(() => {
    stopBrowserSpeech();
    if (voice.phase === "live") {
      queueLiveTurn({kind: "style", text: preferencesPrompt()});
    }
  }));
  window.addEventListener("pagehide", () => disconnectVoice());
  window.addEventListener("beforeunload", () => disconnectVoice());
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && voice.phase !== "off") disconnectVoice("Tab hidden · microphone off");
  });
  $("shutdown").addEventListener("click", guard(async () => {
    if (!await confirmChoice("Stop Wanda on this computer?", "This disconnects voice and stops the local app. Saved memories remain. No home devices will be changed. Run the launcher to start again.", "Stop Wanda")) return;
    disconnectVoice(); await api("/api/shutdown", {method: "POST", body: {}});
    $("connection-label").textContent = "Wanda is stopped"; $("connection-dot").classList.add("error");
    $("send-chat").disabled = true; $("connect-voice").disabled = true; capability = "";
    try { sessionStorage.removeItem("wanda-capability"); } catch (_) { /* Optional session storage. */ }
    tell("Wanda has stopped. Start the launcher when you want to return.");
  }));

  async function initialize() {
    greeting();
    try {
      state.status = await api("/api/status");
      setVoiceState("off", "Microphone is off");
      $("connection-label").textContent = "Running on this computer";
      $("connect-voice").disabled = !state.status.voice?.configured;
      $("voice-description").textContent = state.status.voice?.configured ? "OpenAI is configured. Connecting sends microphone audio to its cloud service, with separate consent for every session." : "Live voice is not configured. The local text demo works without an account or API key. See the morning handoff to enable optional cloud voice.";
      const results = await Promise.allSettled([refreshMemory(), refreshHome(), refreshDisclosures()]);
      for (const result of results) if (result.status === "rejected") tell(result.reason.message, true);
    } catch (error) {
      $("connection-label").textContent = "Session not connected"; $("connection-dot").classList.add("error");
      $("send-chat").disabled = true; tell(error.message, true);
    }
  }
  initialize();
})();
