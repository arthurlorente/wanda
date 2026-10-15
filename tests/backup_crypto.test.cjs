"use strict";
const assert = require("node:assert/strict");
const {test} = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const {pbkdf2Sync, createDecipheriv, createCipheriv, randomBytes, webcrypto} = require("node:crypto");
if (!globalThis.crypto) globalThis.crypto = webcrypto;
require("../web/backup.js");
const backup = globalThis.WandaBackup;
const password = "synthetic purple lanterns";
const payload = {
  format: "wanda-memory-backup", version: 1, created_at: 1770000000,
  memories: [{id: "dc679269-3fcd-47a2-a1af-4496d6f37d96", text: "Synthetic chá preference",
    category: "preference", created_at: 1760000000, expires_at: null}],
};
const aad = Buffer.from("wanda-encrypted-backup:1:PBKDF2:SHA-256:600000:AES-256-GCM:128");

test("actual Web Crypto roundtrip is randomized and contains no cleartext", async () => {
  const one = await backup.encrypt(payload, password);
  const two = await backup.encrypt(payload, password);
  assert.notEqual(one, two);
  assert.equal(one.includes(payload.memories[0].text), false);
  assert.equal(one.includes(password), false);
  assert.deepEqual(await backup.decrypt(one, password), payload);
  const first = JSON.parse(one), second = JSON.parse(two);
  assert.notEqual(first.kdf.salt, second.kdf.salt);
  assert.notEqual(first.cipher.iv, second.cipher.iv);
});

test("archive interoperates with independent Node crypto decryption", async () => {
  const envelope = JSON.parse(await backup.encrypt(payload, password));
  const key = pbkdf2Sync(password, Buffer.from(envelope.kdf.salt, "base64"), 600000, 32, "sha256");
  const encrypted = Buffer.from(envelope.ciphertext, "base64");
  const decipher = createDecipheriv("aes-256-gcm", key, Buffer.from(envelope.cipher.iv, "base64"));
  decipher.setAAD(aad);
  decipher.setAuthTag(encrypted.subarray(-16));
  const clear = Buffer.concat([decipher.update(encrypted.subarray(0, -16)), decipher.final()]);
  assert.deepEqual(JSON.parse(clear.toString("utf8")), payload);
  key.fill(0); clear.fill(0);
});

test("independently produced encrypted archive decrypts with the browser module", async () => {
  const salt = randomBytes(16), iv = randomBytes(12);
  const key = pbkdf2Sync(password, salt, 600000, 32, "sha256");
  const cipher = createCipheriv("aes-256-gcm", key, iv);
  cipher.setAAD(aad);
  const data = Buffer.concat([cipher.update(JSON.stringify(payload), "utf8"), cipher.final(), cipher.getAuthTag()]);
  const serialized = JSON.stringify({format: "wanda-encrypted-backup", version: 1,
    kdf: {name: "PBKDF2", hash: "SHA-256", iterations: 600000, salt: salt.toString("base64")},
    cipher: {name: "AES-GCM", iv: iv.toString("base64")}, ciphertext: data.toString("base64")});
  assert.deepEqual(await backup.decrypt(serialized, password), payload);
  key.fill(0);
});

test("wrong password and ciphertext tampering fail authentication without plaintext", async () => {
  const serialized = await backup.encrypt(payload, password);
  await assert.rejects(backup.decrypt(serialized, "another synthetic password"), /incorrect or.*damaged/);
  const envelope = JSON.parse(serialized);
  const bytes = Buffer.from(envelope.ciphertext, "base64"); bytes[0] ^= 1;
  envelope.ciphertext = bytes.toString("base64");
  await assert.rejects(backup.decrypt(JSON.stringify(envelope), password), /incorrect or.*damaged/);
});

test("password and plaintext format boundaries are enforced", async () => {
  for (const invalid of [null, "short", "x".repeat(1025), "🟢".repeat(257), "synthetic pass\ud800", "\udc00synthetic pass"]) {
    await assert.rejects(backup.encrypt(payload, invalid), /password/i);
  }
  const unicode = "🟢".repeat(12);
  assert.deepEqual(await backup.decrypt(await backup.encrypt(payload, unicode), unicode), payload);
  await assert.rejects(backup.encrypt({...payload, grants: []}, password), /supported/);
  await assert.rejects(backup.encrypt({...payload, version: 2}, password), /supported/);
  await assert.rejects(backup.encrypt({...payload, memories: Array(1001).fill({})}, password), /supported/);
});

test("untrusted parameters and oversized envelopes fail before expensive key derivation", async () => {
  let keyCalls = 0;
  const context = {TextEncoder, TextDecoder, atob, btoa,
    crypto: {getRandomValues: () => {}, subtle: {importKey: () => {keyCalls++; throw Error("Unexpected KDF");}}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../web/backup.js"), "utf8"), context);
  const valid = JSON.parse(await backup.encrypt(payload, password));
  const variants = [
    {...valid, version: 2}, {...valid, owner: "other"},
    {...valid, kdf: {...valid.kdf, iterations: 1}},
    {...valid, kdf: {...valid.kdf, iterations: 1e12}},
    {...valid, kdf: {...valid.kdf, hash: "SHA-1"}},
    {...valid, kdf: {...valid.kdf, salt: "AAAA"}},
    {...valid, cipher: {...valid.cipher, iv: "AAAA"}},
    {...valid, cipher: {...valid.cipher, extra: true}},
    {...valid, ciphertext: "not base64"}, {...valid, ciphertext: "AAAA"},
  ];
  for (const value of variants) await assert.rejects(context.WandaBackup.decrypt(JSON.stringify(value), password));
  await assert.rejects(context.WandaBackup.decrypt("x".repeat(backup.MAX_FILE_BYTES + 1), password));
  assert.equal(keyCalls, 0);
});
