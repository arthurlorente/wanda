"""Optional OpenAI WebRTC SDP exchange; no audio persistence or model tools.

Schema verified against official docs on 2026-10-15. Live integration unverified.
"""

import json
import re
import secrets
import urllib.error
import urllib.request

from wanda.persona import instructions

ENDPOINT = "https://api.openai.com/v1/realtime/calls"
MAX_SDP_BYTES = 100_000


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VoiceProvider:
    def __init__(self, api_key, model="gpt-realtime-2.1", transport=None):
        if not isinstance(api_key, str) or any(char in api_key for char in "\r\n"):
            raise ValueError("Invalid voice provider configuration.")
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", model):
            raise ValueError("Invalid voice model configuration.")
        self._api_key = api_key
        self.model = model
        # Do not send credentials to an environment-configured proxy or redirect.
        self._transport = transport or urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        ).open

    def create_session(self, sdp):
        if not self._api_key:
            raise RuntimeError("Cloud voice is not configured. The local demo is available.")
        if not isinstance(sdp, str) or not sdp.startswith("v=0") or len(sdp.encode("utf-8")) > MAX_SDP_BYTES:
            raise ValueError("Invalid voice connection offer.")
        config = {
            "type": "realtime", "model": self.model, "instructions": instructions(),
            "output_modalities": ["audio"], "max_output_tokens": 1024,
            "audio": {
                "input": {"turn_detection": {
                    "type": "semantic_vad", "eagerness": "low",
                    "create_response": True, "interrupt_response": True,
                }},
                "output": {"voice": "marin"},
            },
            "tools": [],
        }
        boundary = "wanda-" + secrets.token_hex(24)
        parts = []
        for name, value in (("sdp", sdp), ("session", json.dumps(config))):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n')
        body = ("".join(parts) + f"--{boundary}--\r\n").encode("utf-8")
        request = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
            "Authorization": "Bearer " + self._api_key,
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "Accept": "application/sdp",
        })
        try:
            with self._transport(request, timeout=25) as response:
                if getattr(response, "status", 200) not in (200, 201):
                    raise RuntimeError("Cloud voice could not connect. The local demo is available.")
                data = response.read(MAX_SDP_BYTES + 1)
                if len(data) > MAX_SDP_BYTES:
                    raise RuntimeError("Cloud voice returned an invalid connection response.")
                answer = data.decode("utf-8")
                if not answer.startswith("v=0"):
                    raise RuntimeError("Cloud voice returned an invalid connection response.")
                return answer
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                message = "Cloud voice access was denied. Check the configured API key and model access."
            elif error.code == 429:
                message = "Cloud voice is at its account or rate limit. The local demo is available."
            else:
                message = "Cloud voice could not connect. The local demo is available."
            error.close()
            raise RuntimeError(message) from None
        except (urllib.error.URLError, TimeoutError, OSError, UnicodeError):
            raise RuntimeError("Cloud voice is unavailable. Check connectivity; the local demo is available.") from None
