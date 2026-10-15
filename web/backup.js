/* Local backup encryption. No network, storage, telemetry, or custom ciphers. */
"use strict";
(() => {
  const MAX_PAYLOAD_BYTES = 8 * 1024 * 1024;
  const MAX_FILE_BYTES = 12 * 1024 * 1024;
  const MIN_PASSWORD_LENGTH = 12;
  const MAX_PASSWORD_BYTES = 1024;
  const ITERATIONS = 600000;
  const encoder = new TextEncoder();
  const decoder = new TextDecoder("utf-8", {fatal: true});
  const aad = encoder.encode("wanda-encrypted-backup:1:PBKDF2:SHA-256:600000:AES-256-GCM:128");

  function exactKeys(value, keys) {
    return value !== null && typeof value === "object" && !Array.isArray(value)
      && Object.keys(value).length === keys.length
      && keys.every((key) => Object.hasOwn(value, key));
  }

  function checkPayload(value) {
    if (!exactKeys(value, ["format", "version", "created_at", "memories"])
        || value.format !== "wanda-memory-backup" || value.version !== 1
        || !Number.isFinite(value.created_at) || value.created_at <= 0
        || !Array.isArray(value.memories) || value.memories.length > 1000) {
      throw new Error("This is not a supported Wanda memory backup.");
    }
    // Detailed per-record validation is repeated by the local server before any
    // preview or atomic restore. Encryption never grants storage permission.
    return value;
  }

  function passwordBytes(password) {
    if (typeof password !== "string" || password.length > MAX_PASSWORD_BYTES
        || Array.from(password).length < MIN_PASSWORD_LENGTH) {
      throw new Error("Use a backup password of at least 12 characters, up to 1024 UTF-8 bytes.");
    }
    for (let index = 0; index < password.length; index++) {
      const code = password.charCodeAt(index);
      if (code >= 0xd800 && code <= 0xdbff) {
        const next = password.charCodeAt(++index);
        if (!(next >= 0xdc00 && next <= 0xdfff)) throw new Error("The backup password contains invalid Unicode.");
      } else if (code >= 0xdc00 && code <= 0xdfff) {
        throw new Error("The backup password contains invalid Unicode.");
      }
    }
    const bytes = encoder.encode(password);
    if (bytes.length > MAX_PASSWORD_BYTES) {
      bytes.fill(0);
      throw new Error("The backup password is too long (maximum 1024 UTF-8 bytes).");
    }
    return bytes;
  }

  function requireCrypto() {
    if (!globalThis.crypto?.subtle || !globalThis.crypto?.getRandomValues) {
      throw new Error("Encrypted backups need a browser with Web Crypto. Open Wanda from its local launcher in a current browser.");
    }
  }

  function encode64(bytes) {
    const parts = [];
    for (let offset = 0; offset < bytes.length; offset += 32768) {
      parts.push(String.fromCharCode(...bytes.subarray(offset, offset + 32768)));
    }
    return btoa(parts.join(""));
  }

  function decode64(value, minimum, maximum) {
    if (typeof value !== "string" || value.length % 4 !== 0
        || value.length > Math.ceil(maximum / 3) * 4
        || /[^A-Za-z0-9+/=]/.test(value)) throw new Error("Invalid encrypted backup.");
    let binary;
    try { binary = atob(value); }
    catch (_) { throw new Error("Invalid encrypted backup."); }
    if (binary.length < minimum || binary.length > maximum || btoa(binary) !== value) {
      throw new Error("Invalid encrypted backup.");
    }
    return Uint8Array.from(binary, (character) => character.charCodeAt(0));
  }

  async function derive(password, salt, usage) {
    const bytes = passwordBytes(password);
    try {
      const material = await crypto.subtle.importKey("raw", bytes, "PBKDF2", false, ["deriveKey"]);
      return await crypto.subtle.deriveKey(
        {name: "PBKDF2", salt, iterations: ITERATIONS, hash: "SHA-256"}, material,
        {name: "AES-GCM", length: 256}, false, [usage],
      );
    } finally { bytes.fill(0); }
  }

  async function encrypt(payload, password) {
    requireCrypto();
    checkPayload(payload);
    const serialized = JSON.stringify(payload);
    if (serialized.length > MAX_PAYLOAD_BYTES) throw new Error("This backup is too large.");
    const clear = encoder.encode(serialized);
    if (clear.length > MAX_PAYLOAD_BYTES) {
      clear.fill(0);
      throw new Error("This backup is too large.");
    }
    try {
      const salt = crypto.getRandomValues(new Uint8Array(16));
      const iv = crypto.getRandomValues(new Uint8Array(12));
      const key = await derive(password, salt, "encrypt");
      const encrypted = await crypto.subtle.encrypt(
        {name: "AES-GCM", iv, additionalData: aad, tagLength: 128}, key, clear,
      );
      return JSON.stringify({
        format: "wanda-encrypted-backup", version: 1,
        kdf: {name: "PBKDF2", hash: "SHA-256", iterations: ITERATIONS, salt: encode64(salt)},
        cipher: {name: "AES-GCM", iv: encode64(iv)}, ciphertext: encode64(new Uint8Array(encrypted)),
      });
    } finally { clear.fill(0); }
  }

  async function decrypt(serialized, password) {
    requireCrypto();
    if (typeof serialized !== "string" || serialized.length > MAX_FILE_BYTES
        || encoder.encode(serialized).length > MAX_FILE_BYTES) {
      throw new Error("The encrypted backup exceeds the 12 MiB limit.");
    }
    let envelope;
    try { envelope = JSON.parse(serialized); }
    catch (_) { throw new Error("Choose a valid encrypted Wanda backup file."); }
    if (!exactKeys(envelope, ["format", "version", "kdf", "cipher", "ciphertext"])
        || envelope.format !== "wanda-encrypted-backup" || envelope.version !== 1
        || !exactKeys(envelope.kdf, ["name", "hash", "iterations", "salt"])
        || envelope.kdf.name !== "PBKDF2" || envelope.kdf.hash !== "SHA-256"
        || envelope.kdf.iterations !== ITERATIONS
        || !exactKeys(envelope.cipher, ["name", "iv"]) || envelope.cipher.name !== "AES-GCM") {
      throw new Error("This encrypted backup format is not supported.");
    }
    // Fixed, validated parameters prevent untrusted files requesting expensive
    // KDF settings or unbounded allocations before authentication.
    const salt = decode64(envelope.kdf.salt, 16, 16);
    const iv = decode64(envelope.cipher.iv, 12, 12);
    const encrypted = decode64(envelope.ciphertext, 17, MAX_PAYLOAD_BYTES + 16);
    const key = await derive(password, salt, "decrypt");
    let clear;
    try {
      clear = new Uint8Array(await crypto.subtle.decrypt(
        {name: "AES-GCM", iv, additionalData: aad, tagLength: 128}, key, encrypted,
      ));
    } catch (_) {
      throw new Error("The password is incorrect or the backup was changed or damaged. Nothing was restored.");
    }
    try {
      return checkPayload(JSON.parse(decoder.decode(clear)));
    } catch (_) {
      throw new Error("The decrypted file is not a supported Wanda memory backup.");
    } finally { clear.fill(0); }
  }

  globalThis.WandaBackup = Object.freeze({
    encrypt, decrypt, MAX_PAYLOAD_BYTES, MAX_FILE_BYTES, MIN_PASSWORD_LENGTH, MAX_PASSWORD_BYTES,
  });
})();
