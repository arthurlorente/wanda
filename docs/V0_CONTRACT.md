# V0 integration contract (provisional)

Python 3.11+ standard library only. Native JS browser, no external assets/packages.
Owner account server-side is `local-owner`; requests never select their owner.
All API calls need `Authorization: Bearer <launch capability>`. JSON errors use
`{"error":"safe description","code":"stable_code"}` and HTTP 4xx/5xx.

## HTTP interface

- GET `/api/status`: `{version,mode:"demo",memory_enabled,voice:{configured,provider,model},home:{mode},persona_version}`.
- POST `/api/chat` `{text,language:"en"|"pt"|"es",tone:"warm"|"neutral"}`:
  `{reply,mode:"demo",memory_saved:[],memory_candidates:[],suggestions:[]}`.
  Conversation stays in client memory; mock service does not claim open-domain AI.
- GET `/api/memory`: `{enabled,memories:[{id,text,category,created_at,expires_at}]}`.
- POST `/api/memory/consent` `{enabled:boolean}`.
- POST `/api/memory` `{text,category:"preference"|"project"|"temporary"|"sensitive",approved:boolean,expires_at:number|null}`.
- PATCH `/api/memory/<id>` same fields; DELETE `/api/memory/<id>`; DELETE `/api/memory`.
- GET `/api/memory/export`: JSON export download via authorized fetch.
- GET `/api/disclosures`: `{grants:[]}`. POST `/api/disclosures`
  `{provider:"openai",category,allowed:boolean,one_time:boolean,expires_at:number|null}`.
  DELETE `/api/disclosures/<id>`. No memory is automatically sent to cloud in V0.
- GET `/api/home`: `{mode,devices:[{entity_id,name,state}],grants:[],audit:[]}`.
- POST `/api/home/grants` `{entity_id,action:"turn_on"|"turn_off",confirmation:boolean,expires_at:number|null}`.
- DELETE `/api/home/grants/<id>`.
- POST `/api/home/action` `{entity_id,action,request_id,confirmation_id?:string}`:
  `{status:"verified"|"confirmation_required"|"denied"|"unavailable"|"unverified",message,confirmation_id?,state?}`.
  Confirmation is a second explicit UI click. A chat/voice request cannot approve it.
- POST `/api/home/outage` `{offline:boolean}`: mock adapter only.
- POST `/api/voice/session` `{sdp,audio_consent:true}` returns `{sdp}`; optional live provider.
- POST `/api/shutdown` stops local service, no devices affected.

## Python module interfaces

`wanda.memory.MemoryStore(path)` owns SQLite connection/locking and migrations.
`is_enabled(owner)`, `set_enabled(owner,enabled)`, `list_memories(owner)`,
`save(owner,text,category="preference",approved=False,expires_at=None)`,
`update(owner,id,text,category,approved=False,expires_at=None)`, `delete(owner,id)`,
`clear(owner)`, `export(owner)`, `extract(owner,text)` returns `{saved:[],candidates:[]}`,
`list_grants(owner)`, `set_grant(owner,provider,category,allowed,one_time=False,expires_at=None)`,
`revoke_grant(owner,id)`, `disclose(owner,provider,memory_ids)` (enforce and consume
single-use grants atomically; never called automatically), `close()`.
Raise ValueError for invalid inputs, PermissionError for denied consent/access.
Use Unix seconds for times, UUID strings for IDs. Reentrant lock for HTTP threads.
Additive `recall(owner)` checks consent and reads atomically, bounded to eight
records/4000 text characters; conversational callers use it instead of inspection.

`wanda.home.HomeService(adapter)` exposes `snapshot(owner)`,
`grant(owner,entity_id,action,confirmation=True,expires_at=None)`,
`revoke(owner,id)`, `act(owner,entity_id,action,request_id,confirmation_id=None)`,
`set_outage(offline)`. Permissions/audit ephemeral for V0, default denied.
`MockHomeAdapter()` and `HomeAssistantAdapter(url,token,allowed_entities)` are
replaceable. Deny unsupported domains. Tests must inject HTTP transport, never live.

`wanda.voice.VoiceProvider(api_key,model)` exposes `create_session(sdp)` -> SDP answer;
timeouts and sanitized errors, no persistence. `wanda.persona` exports
`PERSONA_VERSION`, `instructions(tone="warm")`, `demo_reply(text,language="en",tone="warm")`.

Orchestrator owns HTTP server, config, launchers, integration tests, project docs.
Voice agent owns `web/`, `wanda/voice.py`, `wanda/persona.py`, respective unit tests.
Memory agent owns `wanda/memory.py`, `tests/test_memory.py`, `docs/MEMORY.md`.
Home agent owns `wanda/home.py`, `tests/test_home.py`, `docs/HOME.md`.
