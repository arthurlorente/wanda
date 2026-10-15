"""Bounded, permissioned home control for Wanda's local V0.

Only synthetic mock devices are active by default. The Home Assistant adapter is
opt-in and deliberately limited to allowlisted lights. No adapter receives a
request until HomeService has checked the owner, grant, and confirmation.
"""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
import json
import math
import re
import secrets
import threading
import time
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener
from uuid import uuid4

from wanda.tls import create_https_context


_ENTITY = re.compile(r"^light\.[a-z0-9_]+$")
_ACTIONS = frozenset(("turn_on", "turn_off"))
_CONFIRM_SECONDS = 60
_MAX_GRANTS = 256
_MAX_REQUESTS = 1024
_MAX_AUDIT = 256


def _valid_owner(owner: str) -> str:
    if not isinstance(owner, str) or not owner or len(owner) > 128:
        raise ValueError("Invalid owner")
    return owner


def _valid_entity(entity_id: str) -> str:
    if not isinstance(entity_id, str) or not _ENTITY.fullmatch(entity_id):
        raise ValueError("Only light entities are supported")
    return entity_id


def _valid_action(action: str) -> str:
    if action not in _ACTIONS:
        raise ValueError("Unsupported home action")
    return action


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        # Never forward a bearer credential to a redirect target.
        return None


def _transport(method: str, url: str, headers: dict[str, str], payload: dict | None) -> tuple[int, object]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with build_opener(ProxyHandler({}), _NoRedirect,
                          HTTPSHandler(context=create_https_context())).open(request, timeout=5) as response:
            data = response.read(1024 * 1024)
            return response.status, json.loads(data) if data else None
    except HTTPError as error:
        # The response body may contain private instance information or a token.
        return error.code, None


class MockHomeAdapter:
    """Two synthetic lights, with a switchable simulated outage."""

    mode = "mock"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._offline = False
        self._devices = {
            "light.demo_lamp": {"entity_id": "light.demo_lamp", "name": "Demo lamp", "state": "off"},
            "light.demo_desk": {"entity_id": "light.demo_desk", "name": "Demo desk light", "state": "off"},
        }

    def supports(self, entity_id: str, action: str) -> bool:
        return entity_id in self._devices and action in _ACTIONS

    def list_devices(self) -> list[dict]:
        with self._lock:
            return [dict(device, state="unavailable" if self._offline else device["state"])
                    for device in self._devices.values()]

    def perform(self, entity_id: str, action: str) -> dict:
        with self._lock:
            if self._offline:
                return {"status": "unavailable", "message": "Mock home is offline."}
            if not self.supports(entity_id, action):
                return {"status": "denied", "message": "Device or action is not allowed."}
            state = "on" if action == "turn_on" else "off"
            self._devices[entity_id]["state"] = state
            return {"status": "verified", "message": f"Demo light is {state}.", "state": state}

    def set_outage(self, offline: bool) -> None:
        if not isinstance(offline, bool):
            raise ValueError("offline must be a boolean")
        with self._lock:
            self._offline = offline


class HomeAssistantAdapter:
    """REST adapter restricted to an explicit list of light entities.

    ``transport(method, url, headers, payload)`` returns ``(status, JSON)``.
    Injection makes all tests entirely local; the default uses urllib.
    """

    mode = "homeassistant"

    def __init__(
        self,
        url: str,
        token: str,
        allowed_entities: list[str] | tuple[str, ...] | set[str],
        *,
        transport: Callable[[str, str, dict[str, str], dict | None], tuple[int, object]] | None = None,
        allow_insecure_http: bool = False,
    ) -> None:
        if not isinstance(url, str):
            raise ValueError("Invalid Home Assistant URL")
        try:
            parts = urlsplit(url)
            port = parts.port
        except ValueError as error:
            raise ValueError("Invalid Home Assistant URL") from error
        if (parts.scheme not in {"http", "https"} or not parts.hostname or
                parts.username or parts.password or parts.query or parts.fragment or
                parts.path not in {"", "/"} or port == 0):
            raise ValueError("Invalid Home Assistant URL")
        if parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1", "::1"} and not allow_insecure_http:
            raise ValueError("HTTP to a non-loopback Home Assistant requires explicit opt-in")
        if not isinstance(allow_insecure_http, bool):
            raise ValueError("allow_insecure_http must be a boolean")
        if not isinstance(token, str) or not token or any(char.isspace() for char in token):
            raise ValueError("A Home Assistant token is required")
        try:
            entities = tuple(allowed_entities)
        except TypeError as error:
            raise ValueError("Select 1 to 256 allowed lights") from error
        if not entities or len(entities) > 256:
            raise ValueError("Select 1 to 256 allowed lights")
        for entity in entities:
            _valid_entity(entity)
        if len(set(entities)) != len(entities):
            raise ValueError("Duplicate allowed light")
        self._base = url.rstrip("/")
        self._token = token
        self._allowed = frozenset(entities)
        self._ordered = entities
        self._transport = transport or _transport

    def supports(self, entity_id: str, action: str) -> bool:
        return entity_id in self._allowed and action in _ACTIONS

    def _request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, object]:
        return self._transport(
            method,
            self._base + path,
            {"Authorization": "Bearer " + self._token, "Content-Type": "application/json"},
            payload,
        )

    def _read(self, entity_id: str) -> dict | None:
        status, data = self._request("GET", "/api/states/" + quote(entity_id, safe=""))
        if status != 200 or not isinstance(data, dict) or data.get("entity_id") != entity_id:
            return None
        state = data.get("state")
        if state not in {"on", "off"}:
            return None
        attributes = data.get("attributes")
        name = attributes.get("friendly_name") if isinstance(attributes, dict) else None
        return {"entity_id": entity_id, "name": name if isinstance(name, str) and name else entity_id, "state": state}

    def list_devices(self) -> list[dict]:
        devices = []
        for index, entity_id in enumerate(self._ordered):
            try:
                device = self._read(entity_id)
            except Exception:
                # A transport failure normally affects the whole instance.
                # Do not wait for the same timeout on every allowlisted light.
                devices.extend({"entity_id": remaining, "name": remaining, "state": "unavailable"}
                               for remaining in self._ordered[index:])
                break
            devices.append(device or {"entity_id": entity_id, "name": entity_id, "state": "unavailable"})
        return devices

    def perform(self, entity_id: str, action: str) -> dict:
        if not self.supports(entity_id, action):
            return {"status": "denied", "message": "Device or action is not allowed."}
        try:
            status, _ = self._request("POST", "/api/services/light/" + action, {"entity_id": entity_id})
        except Exception:
            # A timeout can occur after Home Assistant accepted the command.
            return {"status": "unverified", "message": "Home Assistant command outcome is unknown; check the light before retrying."}
        if status not in {200, 201}:
            return {"status": "unverified", "message": "Home Assistant did not confirm the command; check the light before retrying."}
        try:
            device = self._read(entity_id)
        except Exception:
            device = None
        expected = "on" if action == "turn_on" else "off"
        if device is None or device["state"] != expected:
            return {"status": "unverified", "message": "The light state could not be verified; check it before retrying."}
        return {"status": "verified", "message": f"Light is {expected}.", "state": expected}


@dataclass
class _Pending:
    nonce: str
    expires_at: float


class HomeService:
    """Deny-default grant and confirmation gate for one selected adapter.

    The owning HTTP layer must authenticate the local user and supply its owner
    key; untrusted requests must never select a different owner.
    """

    def __init__(self, adapter: MockHomeAdapter | HomeAssistantAdapter, *, clock: Callable[[], float] = time.time) -> None:
        self.adapter = adapter
        self._clock = clock
        self._lock = threading.RLock()
        self._grants: OrderedDict[str, dict] = OrderedDict()
        self._requests: OrderedDict[tuple[str, str], dict] = OrderedDict()
        self._audit: deque[dict] = deque(maxlen=_MAX_AUDIT)

    def _active_grant(self, owner: str, entity_id: str, action: str) -> dict | None:
        now = self._clock()
        for grant in self._grants.values():
            if (grant["owner"] == owner and grant["entity_id"] == entity_id and
                    grant["action"] == action and
                    (grant["expires_at"] is None or grant["expires_at"] > now)):
                return grant
        return None

    @staticmethod
    def _public_grant(grant: dict) -> dict:
        return {key: grant[key] for key in ("id", "entity_id", "action", "confirmation", "expires_at")}

    def _record(self, owner: str, entity_id: str, action: str, status: str) -> None:
        self._audit.append({"at": self._clock(), "owner": owner, "entity_id": entity_id,
                            "action": action, "status": status})

    def snapshot(self, owner: str) -> dict:
        _valid_owner(owner)
        try:
            devices = self.adapter.list_devices()
        except Exception:
            devices = []
        with self._lock:
            return {
                "mode": self.adapter.mode,
                "devices": devices,
                "grants": [self._public_grant(g) for g in self._grants.values()
                           if g["owner"] == owner and (g["expires_at"] is None or g["expires_at"] > self._clock())],
                "audit": [dict(a) for a in self._audit if a["owner"] == owner],
            }

    def grant(self, owner: str, entity_id: str, action: str, confirmation: bool = True,
              expires_at: float | None = None) -> dict:
        _valid_owner(owner)
        _valid_entity(entity_id)
        _valid_action(action)
        if not self.adapter.supports(entity_id, action):
            raise ValueError("Device or action is not allowed")
        if not isinstance(confirmation, bool):
            raise ValueError("confirmation must be a boolean")
        if expires_at is not None and (isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)) or
                                       not math.isfinite(expires_at) or expires_at <= self._clock()):
            raise ValueError("expires_at must be a future Unix timestamp")
        with self._lock:
            for grant_id in tuple(self._grants):
                expiry = self._grants[grant_id]["expires_at"]
                if expiry is not None and expiry <= self._clock():
                    del self._grants[grant_id]
            if self._active_grant(owner, entity_id, action) is not None:
                raise ValueError("Revoke the existing permission before changing it")
            if len(self._grants) >= _MAX_GRANTS:
                raise ValueError("Too many home grants")
            grant = {"id": str(uuid4()), "owner": owner, "entity_id": entity_id,
                     "action": action, "confirmation": confirmation, "expires_at": expires_at}
            self._grants[grant["id"]] = grant
            return self._public_grant(grant)

    def revoke(self, owner: str, id: str) -> bool:
        _valid_owner(owner)
        with self._lock:
            grant = self._grants.get(id)
            if grant is None or grant["owner"] != owner:
                return False
            del self._grants[id]
            return True

    def act(self, owner: str, entity_id: str, action: str, request_id: str,
            confirmation_id: str | None = None) -> dict:
        _valid_owner(owner)
        _valid_entity(entity_id)
        _valid_action(action)
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            raise ValueError("request_id must be a nonempty string")
        if confirmation_id is not None and not isinstance(confirmation_id, str):
            raise ValueError("confirmation_id must be a string")
        with self._lock:
            key = (owner, request_id)
            record = self._requests.get(key)
            payload = (entity_id, action)
            if record is not None and record["payload"] != payload:
                return {"status": "denied", "message": "Request ID was already used for a different action."}
            if record is not None and record["result"] is not None:
                return dict(record["result"])

            grant = self._active_grant(owner, entity_id, action)
            if grant is None or not self.adapter.supports(entity_id, action):
                result = {"status": "denied", "message": "No active permission for this light and action."}
                self._record(owner, entity_id, action, "denied")
                return result

            if record is None:
                if len(self._requests) >= _MAX_REQUESTS:
                    # Fail closed: eviction could let an old request execute twice.
                    return {"status": "unavailable", "message": "Action history is full; restart Wanda before issuing more controls."}
                record = {"payload": payload, "result": None, "pending": None,
                          "grant_id": grant["id"]}
                self._requests[key] = record

            if record["grant_id"] != grant["id"]:
                record["result"] = {"status": "denied", "message": "Permission changed; start a new request."}
                self._record(owner, entity_id, action, "denied")
                return dict(record["result"])

            if grant["confirmation"]:
                pending = record["pending"]
                if pending is None:
                    pending = _Pending(secrets.token_urlsafe(24), self._clock() + _CONFIRM_SECONDS)
                    record["pending"] = pending
                if self._clock() >= pending.expires_at:
                    record["result"] = {"status": "denied", "message": "Confirmation expired; start a new request."}
                    self._record(owner, entity_id, action, "denied")
                    return dict(record["result"])
                if confirmation_id is None:
                    return {"status": "confirmation_required", "message": "Confirm this light action in the browser.",
                            "confirmation_id": pending.nonce}
                if not secrets.compare_digest(confirmation_id, pending.nonce):
                    return {"status": "denied", "message": "Confirmation did not match this action."}
            elif confirmation_id is not None:
                return {"status": "denied", "message": "Unexpected confirmation."}

            try:
                result = self.adapter.perform(entity_id, action)
            except Exception:
                result = {"status": "unverified", "message": "The home action outcome is unknown; check the device before retrying."}
            if result.get("status") not in {"verified", "denied", "unavailable", "unverified"}:
                result = {"status": "unverified", "message": "The home action outcome is unknown; check the device before retrying."}
            record["result"] = dict(result)
            record["pending"] = None
            self._record(owner, entity_id, action, result["status"])
            return dict(result)

    def set_outage(self, offline: bool) -> None:
        if not isinstance(self.adapter, MockHomeAdapter):
            raise ValueError("Outage simulation is available only in demo mode")
        self.adapter.set_outage(offline)
