"""Black-box backup HTTP tests using only synthetic local memories."""

import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import uuid

from wanda.config import Config
from wanda.server import Application, LocalServer


OWNER = "local-owner"


def record(text, *, identifier=None, category="preference", expires_at=None):
    return {
        "id": identifier or str(uuid.uuid4()),
        "text": text,
        "category": category,
        "created_at": time.time() - 60,
        "expires_at": expires_at,
    }


def archive(*memories):
    return {
        "format": "wanda-memory-backup",
        "version": 1,
        "created_at": time.time(),
        "memories": list(memories),
    }


class BackupHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wanda-backup-http-")
        self.app = Application(Config(data_dir=Path(self.temp.name), home_mode="mock", voice_enabled=False))
        self.server = LocalServer(self.app, port=0)
        self.port = self.server.server_address[1]
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=3)
        self.app.close()
        self.temp.cleanup()

    def request(self, method, path, payload=None, *, auth=True, headers=None, raw=False):
        body = payload if raw else (None if payload is None else json.dumps(payload).encode("utf-8"))
        request_headers = {"Host": f"127.0.0.1:{self.port}"}
        if auth:
            request_headers["Authorization"] = "Bearer " + self.app.token
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            wire = response.read()
            return response.status, json.loads(wire), response.headers, wire
        finally:
            connection.close()

    def enable(self):
        self.app.memory.set_enabled(OWNER, True)

    def test_backup_is_authenticated_private_and_available_while_disabled(self):
        self.enable()
        saved = self.app.memory.save(OWNER, "Synthetic preference", approved=True)
        self.app.memory.set_grant(OWNER, "synthetic", "preference", True)
        self.app.memory.set_enabled(OWNER, False)

        status, result, _, _ = self.request("GET", "/api/memory/backup", auth=False)
        self.assertEqual((status, result["code"]), (401, "unauthorized"))
        status, result, _, _ = self.request(
            "GET", "/api/memory/backup", headers={"Origin": "https://untrusted.invalid"}
        )
        self.assertEqual((status, result["code"]), (403, "invalid_origin"))

        status, result, headers, wire = self.request("GET", "/api/memory/backup")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(set(result), {"format", "version", "created_at", "memories"})
        self.assertEqual((result["format"], result["version"]), ("wanda-memory-backup", 1))
        self.assertEqual(len(result["memories"]), 1)
        self.assertEqual(set(result["memories"][0]),
                         {"id", "text", "category", "created_at", "expires_at"})
        self.assertEqual(result["memories"][0]["id"], saved["id"])
        for forbidden in (b"synthetic\"", b"grants", b"enabled", b"local-owner", b"disclosure_categories"):
            self.assertNotIn(forbidden, wire)

    def test_preview_is_read_only_and_commit_requires_explicit_boolean_approval(self):
        self.enable()
        payload = archive(record("Synthetic restored fact"))
        request = {"backup": payload}
        before = self.app.memory.list_memories(OWNER)

        status, result, _, _ = self.request("POST", "/api/memory/restore/preview", request, auth=False)
        self.assertEqual((status, result["code"]), (401, "unauthorized"))
        status, result, _, _ = self.request(
            "POST", "/api/memory/restore/preview", request,
            headers={"Sec-Fetch-Site": "cross-site"}
        )
        self.assertEqual((status, result["code"]), (403, "cross_site"))

        status, result, _, _ = self.request("POST", "/api/memory/restore/preview", request)
        self.assertEqual(status, 200)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["restorable"], 1)
        self.assertEqual(self.app.memory.list_memories(OWNER), before)

        for approved in (None, False, "true", 1):
            body = {"backup": payload}
            if approved is not None:
                body["approved"] = approved
            status, _, _, _ = self.request("POST", "/api/memory/restore", body)
            self.assertNotEqual(status, 200)
            self.assertEqual(self.app.memory.list_memories(OWNER), before)

        status, result, _, _ = self.request(
            "POST", "/api/memory/restore", {"backup": payload, "approved": True}
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["restored"], 1)
        self.assertEqual(len(self.app.memory.list_memories(OWNER)), 1)

        status, result, _, _ = self.request(
            "POST", "/api/memory/restore", {"backup": payload, "approved": True}
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["restored"], 0)
        self.assertEqual(len(self.app.memory.list_memories(OWNER)), 1)

    def test_restore_cannot_enable_memory_or_import_privileges(self):
        payload = archive(record("Synthetic offline item"))
        for extra in ({"enabled": True}, {"grants": [{"allowed": True}]}, {"owner": "other"}):
            status, result, _, wire = self.request(
                "POST", "/api/memory/restore/preview", {"backup": dict(payload, **extra)}
            )
            self.assertEqual(status, 400)
            self.assertNotIn(b"Synthetic offline item", wire)
            self.assertEqual(result["code"], "invalid_request")

        status, result, _, _ = self.request(
            "POST", "/api/memory/restore", {"backup": payload, "approved": True}
        )
        self.assertEqual((status, result["code"]), (403, "permission_required"))
        self.assertFalse(self.app.memory.is_enabled(OWNER))
        self.assertEqual(self.app.memory.list_memories(OWNER), [])
        self.assertEqual(self.app.memory.list_grants(OWNER), [])

    def test_malformed_records_are_rejected_without_partial_restore_or_echo(self):
        self.enable()
        valid = record("Synthetic valid")
        variants = [
            dict(valid, text=""),
            dict(valid, text="x" * 1001),
            dict(valid, category="administrator"),
            dict(valid, created_at=float("inf")),
            dict(valid, expires_at=float("nan")),
            dict(valid, grant=True),
        ]
        for invalid in variants:
            with self.subTest(invalid=tuple(invalid)):
                payload = archive(valid, invalid)
                status, result, _, wire = self.request(
                    "POST", "/api/memory/restore", {"backup": payload, "approved": True}
                )
                self.assertEqual((status, result["code"]), (400, "invalid_request"))
                self.assertNotIn(b"Synthetic valid", wire)
                self.assertEqual(self.app.memory.list_memories(OWNER), [])

    def test_preview_does_not_reserve_capacity_or_override_current_consent(self):
        self.enable()
        payload = archive(record("Synthetic future item"))
        status, result, _, _ = self.request("POST", "/api/memory/restore/preview", {"backup": payload})
        self.assertEqual(status, 200)
        self.assertEqual(result["restorable"], 1)

        self.app.memory.set_enabled(OWNER, False)
        status, result, _, _ = self.request(
            "POST", "/api/memory/restore", {"backup": payload, "approved": True}
        )
        self.assertEqual((status, result["code"]), (403, "permission_required"))
        self.assertEqual(self.app.memory.list_memories(OWNER), [])

    def test_stale_capacity_rejects_entire_merge_without_changing_existing_items(self):
        self.enable()
        payload = archive(*(record(f"Synthetic recovered item {index}") for index in range(1000)))
        status, preview, _, _ = self.request("POST", "/api/memory/restore/preview", {"backup": payload})
        self.assertEqual(status, 200)
        self.assertEqual((preview["restorable"], preview["available"], preview["exceeds_capacity"]),
                         (1000, 1000, False))

        existing = self.app.memory.save(OWNER, "Synthetic newer local item", approved=True)
        status, result, _, _ = self.request(
            "POST", "/api/memory/restore", {"backup": payload, "approved": True}
        )
        self.assertEqual((status, result["code"]), (400, "invalid_request"))
        current = self.app.memory.list_memories(OWNER)
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["id"], existing["id"])

    def test_restore_wrapper_rejects_unexpected_fields_and_owner_spoof(self):
        self.enable()
        payload = archive(record("Synthetic private recovery"))
        for method, path, body in (
            ("POST", "/api/memory/restore/preview", {"backup": payload, "owner": "other"}),
            ("POST", "/api/memory/restore", {"backup": payload, "approved": True, "owner": "other"}),
            ("POST", "/api/memory/restore", {"backup": payload, "approved": True, "grants": []}),
        ):
            status, result, _, wire = self.request(method, path, body)
            self.assertEqual((status, result["code"]), (400, "invalid_request"))
            self.assertNotIn(b"Synthetic private recovery", wire)
        self.assertEqual(self.app.memory.list_memories(OWNER), [])

    def test_large_restore_body_exception_is_scoped_to_two_routes(self):
        self.enable()
        items = [record("Synthetic item %04d: %s" % (index, "x" * 850)) for index in range(160)]
        payload = {"backup": archive(*items)}
        encoded = json.dumps(payload).encode("utf-8")
        self.assertGreater(len(encoded), 131072)
        self.assertLess(len(encoded), 8 * 1024 * 1024)

        status, result, _, _ = self.request(
            "POST", "/api/memory/restore/preview", encoded, raw=True
        )
        self.assertEqual(status, 200)
        self.assertEqual((result["total"], result["restorable"]), (160, 160))
        self.assertEqual(self.app.memory.list_memories(OWNER), [])

        status, result, _, _ = self.request("POST", "/api/chat", encoded, raw=True)
        self.assertEqual((status, result["code"]), (413, "body_too_large"))
        # Declare an oversized length without sending the body. The server must
        # reject from headers; sending 8 MiB races its early connection close.
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            connection.putrequest("POST", "/api/memory/restore/preview", skip_host=True)
            connection.putheader("Host", f"127.0.0.1:{self.port}")
            connection.putheader("Authorization", "Bearer " + self.app.token)
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", str(8 * 1024 * 1024 + 1))
            connection.endheaders()
            response = connection.getresponse()
            result = json.loads(response.read())
            self.assertEqual((response.status, result["code"]), (413, "body_too_large"))
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
