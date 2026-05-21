# pypufferblow roadmap

A prioritized plan of features to add to the SDK so it matches the
server's current surface area. Each item lists what the gap is,
what the API change looks like, the affected modules, and a
rough effort estimate.

The ordering reflects user demand (reactions and voice are the
two biggest "where is X?" complaints from integrators today) and
dependency order (LQIP plumbing needs to happen first because
several other features want to surface it).

## Status

Today the SDK wraps signup/signin, profile + appearance,
channels + members, message send + load + delete + read marks,
storage uploads, system telemetry, admin (IP blocking +
background tasks), decentralized auth, federation
(follow / federated DMs), and the WebSocket transport (with
auto-reconnect). The bot framework supports commands, listeners,
groups, and lifecycle hooks.

Notable gaps relative to the server:

| Area                       | Server  | SDK         |
|----------------------------|---------|-------------|
| Message reactions          | ✅      | ❌ missing  |
| LQIP-aware media           | ✅      | ❌ missing  |
| Banner retrieval           | ✅      | ⚠️ upload-only |
| Message / channel search   | ✅      | ❌ missing  |
| Voice (v2)                 | ✅      | ❌ missing  |
| Moderation (ban / timeout) | ✅      | ❌ missing  |
| Role + privilege management| ✅      | ❌ missing  |
| Webhooks / RPC bridges     | ⚠️ none | n/a         |
| Rate-limit (`Retry-After`) | ✅      | ⚠️ no global handler |
| Local DM channels          | ✅      | ❌ missing  |

The rest of this doc lays out a sequenced plan for closing the
gaps in priority order.

---

## Tier 1 — must land next release

The Tier-1 items are blocking real bot use cases that maintainers
have already raised. None of these need a server change; the
endpoints exist today.

### 1. Message reactions

**Why it matters.** Reactions are the second-most-used message
verb after "send". A bot framework that can't react to its own or
others' messages can't power "react with 👍 to opt in" workflows,
moderation triage flows, or basic emoji-roll games.

**Server endpoints**:

- `POST /api/v1/channels/{channel_id}/messages/{message_id}/reactions`
  with `{ auth_token, emoji }`.
- `DELETE /api/v1/channels/{channel_id}/messages/{message_id}/reactions`
  with the same body.

**SDK proposal**:

```python
# pypufferblow/reactions.py — new module
class Reactions:
    async def add(self, channel_id: str, message_id: str, emoji: str) -> ReactionResult: ...
    async def remove(self, channel_id: str, message_id: str, emoji: str) -> ReactionResult: ...
    async def toggle(self, channel_id: str, message_id: str, emoji: str) -> ReactionResult: ...

# Expose via the existing Channels facade:
channels.reactions.add(channel_id, message_id, "🎉")
# AND on the Message model:
message.react("🎉")          # sugar over the above
message.unreact("🎉")
```

**Bot integration**:

```python
@bot.on_event("reaction_added")
async def on_reaction(payload): ...

@bot.on_reaction(emoji="🎉")    # narrowing decorator
async def on_cheer(payload): ...
```

The WebSocket already emits `reaction_added` / `reaction_removed`
frames; the bot just needs the decorator + handler plumbing.

**Estimated effort**: 1–2 days. Touches `reactions.py` (new),
`channels.py` (facade), `bot.py` (decorator + dispatch),
`models/message_model.py` (sugar methods), tests in
`tests/test_14_reactions.py` (new).

### 2. LQIP-aware media helpers

**Why it matters.** The server now emits `*_lqip_url` siblings
to every avatar / banner / attachment URL. SDK consumers don't
know they exist — model fields silently absorb the extra payload
but no helper surfaces them. Bots that render previews or upload
asset summaries don't get the placeholder for free.

**Server surface** (already shipping): every `User`,
`MessageAttachment`, and `ServerInfo` payload includes
`*_lqip_url` fields. The variant URL works at
`/storage/{hash}?variant=lqip`.

**SDK proposal**:

```python
# pypufferblow/models/user_model.py
class UserModel:
    avatar_url: str | None
    avatar_lqip_url: str | None   # NEW — already on the wire
    banner_url: str | None
    banner_lqip_url: str | None   # NEW

# pypufferblow/models/message_model.py
class MessageAttachment:
    url: str
    lqip_url: str | None          # NEW
    filename: str
    type: str
    size: int | None

# Helpers
class Storage:
    async def fetch_lqip(self, hash_or_url: str) -> bytes: ...
    def lqip_url_for(self, full_url: str) -> str | None:
        """Compose a LQIP URL from a full storage URL, or None
        if the file has no placeholder."""
```

**Estimated effort**: half a day. Pure plumbing — fields plus
two helper methods.

### 3. Message + channel search

**Why it matters.** Mods and bot authors regularly need "find
the message that said X." The server already supports it; the
SDK doesn't expose it.

**Server endpoint**:
`GET /api/v1/channels/{channel_id}/search?auth_token=...&query=...`

**SDK proposal**:

```python
class Channels:
    async def search(
        self, channel_id: str, query: str, *, limit: int = 50
    ) -> SearchResult:
        """Server-side scan. Returns matches + `truncated_scan` flag
        when the channel was too big to scan exhaustively — call
        sites should fall back to local filtering for live data."""
```

A future iteration can add a global search (across all
channels the bot has access to) by parallelizing the call,
but the single-channel scan is the only thing the server
supports today.

**Estimated effort**: half a day. New method on `Channels`,
fixture in tests.

### 4. Moderation (ban / timeout)

**Why it matters.** Mod-bot use cases need ban + timeout. The
SDK currently exposes only IP blocking, which is a different
operator-level concern.

**Server endpoints** (already on the server):

- `POST /api/v1/moderation/ban` — `{ auth_token, target_user_id, reason }`
- `POST /api/v1/moderation/timeout` — `{ auth_token, target_user_id, duration_minutes, reason }`
- `POST /api/v1/moderation/unban` — `{ auth_token, target_user_id }`
- `POST /api/v1/moderation/report-message` — `{ auth_token, message_id, reason }`
- `POST /api/v1/moderation/report-user` — `{ auth_token, target_user_id, reason }`

**SDK proposal**:

```python
# pypufferblow/moderation.py — new module
class Moderation:
    async def ban(self, user_id: str, *, reason: str = "") -> ModerationResult: ...
    async def unban(self, user_id: str) -> ModerationResult: ...
    async def timeout(
        self, user_id: str, *, duration_minutes: int, reason: str = ""
    ) -> ModerationResult: ...
    async def report_message(self, message_id: str, *, reason: str) -> ModerationResult: ...
    async def report_user(self, user_id: str, *, reason: str) -> ModerationResult: ...

# Bot sugar:
@bot.command(name="ban")
@bot.requires_privilege("ban_users")
async def ban_cmd(ctx, user: UserArg, *, reason: str = ""):
    await ctx.moderation.ban(user.id, reason=reason)
```

**Estimated effort**: 1 day. New module + bot decorator
(`requires_privilege` is also new — see Tier 2).

---

## Tier 2 — high value, lands in the release after

### 5. Role + privilege management

**Why it matters.** Moderation, role-granting bots, and onboarding
flows all need to read and modify roles. The server exposes a
full catalog at `/api/v1/system/roles` and per-user privilege
checks via the resolved `roles_ids` + `resolved_privileges` on
profile responses, but the SDK has no helpers.

**Server endpoints**:

- `GET  /api/v1/system/roles`                          — privilege catalog
- `POST /api/v1/system/roles/{role_id}/assign`         — `{ auth_token, user_id }`
- `POST /api/v1/system/roles/{role_id}/revoke`         — `{ auth_token, user_id }`
- `POST /api/v1/system/roles/create`                   — custom role
- `PUT  /api/v1/system/roles/{role_id}`                — edit
- `DELETE /api/v1/system/roles/{role_id}`              — delete

**SDK proposal**:

```python
class Roles:
    async def list(self) -> list[Role]: ...
    async def assign(self, role_id: str, user_id: str) -> None: ...
    async def revoke(self, role_id: str, user_id: str) -> None: ...
    async def create(self, *, name: str, privileges: list[str], color: str | None = None) -> Role: ...
    async def update(self, role_id: str, *, name: str | None = None, privileges: list[str] | None = None) -> Role: ...
    async def delete(self, role_id: str) -> None: ...

# Bot decorator that gates a command on a privilege:
@bot.command(name="purge")
@bot.requires_privilege("delete_messages")
async def purge(ctx, count: int): ...
```

`requires_privilege` reads the `resolved_privileges` field on the
bot's own profile (cached) and the command sender's profile, then
short-circuits the handler with a permission error if the
privilege is absent.

**Estimated effort**: 2 days including the `requires_privilege`
decorator and profile-cache plumbing.

### 6. Voice (v2)

**Why it matters.** Voice is shipping on the server, and any
"join my voice channel" bot or AFK-detector wants the v2
endpoints. The SDK is currently silent on voice entirely.

**Server endpoints** (under `/api/v2/voice/*`):

- `POST /api/v2/voice/sessions`              — provision
- `POST /api/v2/voice/sessions/{id}/join`    — accept invite, get SFU credentials
- `POST /api/v2/voice/sessions/{id}/leave`
- `GET  /api/v2/voice/sessions/{id}/state`   — participants + media quality
- `POST /api/v2/voice/sessions/{id}/mute`
- `POST /api/v2/voice/sessions/{id}/deafen`
- `POST /api/v2/voice/sessions/{id}/quality` — bitrate / codec hints

**SDK proposal**: a thin wrapper that issues + tears down voice
sessions and surfaces participant state. **Out of scope**:
actually transcoding or mixing audio (that's the SFU's job, and
running a WebRTC stack in Python is a separate project — see
"open question" at the end of this doc).

```python
class Voice:
    async def provision(self, channel_id: str) -> VoiceSession: ...
    async def join(self, session_id: str) -> VoiceCredentials: ...
    async def leave(self, session_id: str) -> None: ...
    async def state(self, session_id: str) -> VoiceState: ...
    async def mute(self, session_id: str, *, muted: bool = True) -> None: ...
    async def deafen(self, session_id: str, *, deafened: bool = True) -> None: ...
```

**Estimated effort**: 2–3 days for the HTTP wrapper + tests.
Excludes any actual audio plumbing.

### 7. Local DMs (non-federated)

**Why it matters.** Federated DMs are already wrapped, but
**local** DM channels (a user-to-user channel on the same
instance) aren't. Most bot DM workflows want this — "DM me my
weekly summary."

**Server endpoints**:

- `POST /api/v1/users/{user_id}/dm`                  — open or fetch the DM channel
- `GET  /api/v1/users/dms`                           — list active DM channels
- `POST /api/v1/channels/{dm_channel_id}/send_message` — same as channel send

**SDK proposal**:

```python
class Users:
    async def dm_channel(self, user_id: str) -> ChannelModel: ...
    async def list_dms(self) -> list[ChannelModel]: ...

# Convenience:
await user.dm("Hello!")    # opens the channel if needed, then sends
```

**Estimated effort**: half a day.

### 8. Global rate-limit handler

**Why it matters.** Bots that hammer the signin / send / refresh
routes can hit `429 Too Many Requests`. The server sets
`Retry-After`; the SDK currently propagates the error but doesn't
back off. Bots written against the SDK that get rate-limited
look broken when they're actually being polite-shamed.

**SDK proposal**:

- Add a retry policy to the shared HTTP layer (`client.py`):
  honor `Retry-After` (seconds or HTTP-date) on 429, sleep, and
  retry up to N times. Configurable via `Client(retry_policy=...)`
  with a sensible default.
- Surface a `RateLimitedError` after the retry budget is
  exhausted so callers can react.

**Estimated effort**: half a day.

---

## Tier 3 — quality of life / framework polish

### 9. Strongly-typed event payloads

Bot event handlers currently take a raw `payload: dict`.
Consumers have to look at the WebSocket protocol doc to know
what to dereference. Add typed Pydantic-or-dataclass payloads:

```python
@bot.on_event("message_created")
async def on_message(event: MessageCreated):
    event.message.channel_id   # IDE autocomplete works
    event.message.author       # populated UserModel
```

`MessageCreated`, `MessageUpdated`, `MessageDeleted`,
`ReactionAdded`, `ReactionRemoved`, `UserPresence`, `UserTyping`,
`Notification`. ~1 day.

### 10. Pagination helpers

`channels.load_messages` returns a single page; callers wanting
the next page have to thread `before=<oldest_message_id>`
manually. Add an iterator helper:

```python
async for batch in channels.iter_messages(channel_id, batch_size=100, max_pages=10):
    for message in batch:
        ...
```

Bounded by `max_pages` to avoid infinite walks. ~half a day.

### 11. `wait_for_message`, `wait_for_reaction`

Already-present `bot.wait_for` is generic. Add typed convenience
wrappers that match Discord-bot vocabulary:

```python
msg = await bot.wait_for_message(channel_id=..., timeout=30.0)
react = await bot.wait_for_reaction(message_id=..., emoji="🎉", timeout=60.0)
```

~half a day.

### 12. Webhooks-style outbound integrations

Pufferblow doesn't have inbound webhooks (the server can't be
"posted to" by external services in the GitHub / Slack sense).
But many bots want to **emit** outbound notifications when
something happens — "post to Discord when a Pufferblow
message matches this regex." Provide a small webhook outbox
helper:

```python
@bot.outbound_webhook(name="discord")
def discord_sink(event): ...

bot.register_webhook_sink("https://discord.com/api/webhooks/...", events=["message_created"])
```

This is opinionated and could grow; ship the simple sink list
first. ~1 day.

---

## Open questions

1. **WebRTC audio in Python**. Tier 2 voice support stops at
   HTTP signaling. Actually consuming the SFU's audio stream
   from Python requires either aiortc or a bridge to a native
   build. Punt for now; pick this up when a real bot use case
   appears.
2. **Async-only vs sync wrappers**. Bot authors sometimes want
   blocking calls from a small script. A `pypufferblow.sync`
   shim that wraps the async surface with `asyncio.run` calls
   would be ~250 LOC and cover the "I'm in a Jupyter notebook,
   give me a synchronous send_message" case. Not blocking
   anything; track as a Tier 3.5 nice-to-have.
3. **Plug-in surface for the bot framework**. Today `bot.py`
   is 1300+ LOC in a single file. As Tier 1–3 features land,
   the framework grows. Worth splitting `bot/` into a package
   (commands, events, lifecycle, dispatch) before adding more.

---

## Suggested sequence

A four-release plan that keeps each release useful on its own:

| Release | Includes |
|---------|----------|
| 0.x+1   | Tier 1 — reactions, LQIP plumbing, search, moderation |
| 0.x+2   | Tier 2 — roles + privileges, voice signaling, local DMs, rate-limit retry |
| 0.x+3   | Tier 3 — typed events, pagination helpers, wait_for sugar, outbound webhooks |
| 0.x+4   | Bot framework split into a package; sync-shim consideration |

Each release should ship with a smoke-test suite that exercises
the new endpoints against a live instance (the CI workflow
already runs against a Docker-Compose Pufferblow — extend the
fixture set rather than mocking the server).
