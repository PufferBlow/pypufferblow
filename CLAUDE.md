# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`pypufferblow` is the official **Python SDK and bot framework** for talking to a Pufferblow server instance over its HTTP/WebSocket API. It is a client library (published to PyPI), not a server. It has no database, no Supabase, and no server-side logic of its own — all state lives on whatever Pufferblow instance the SDK is pointed at (`host`/`port` or `instance=` URL in `ClientOptions`).

This is one of several sibling repos in the `pufferblow-project` workspace (server instance, frontend client, Go media-SFU, and this SDK) — but don't assume details about the siblings; verify in their own repos if it matters.

## Commands

Dependency management is via **Poetry** (`pyproject.toml` + `poetry.lock`). There is no Makefile.

```bash
poetry install              # install dependencies (Python >= 3.11 required)
poetry run pytest           # run the full test suite
poetry run pytest tests/test_02_users_object.py            # run a single test file
poetry run pytest tests/test_02_users_object.py::test_name # run a single test
```

There is no configured linter/formatter (no ruff/flake8/black/mypy config in `pyproject.toml`) and no CI workflow that runs tests — the only GitHub Actions workflow (`.github/workflows/sphinx-docs.yaml`) builds and publishes Sphinx docs to `gh-pages` on push to `main`/`docs`. Don't assume a `ci.yml` exists even though the README badge references one.

Docs are built with Sphinx from `docs/` (`docs/conf.py`, `.rst` sources per module under `docs/` and `docs/tests/`). `scripts/docs.py` and `devtools/cond-envs/docs_env.yaml` support the docs build (conda env used in CI).

Tests use `pytest` with `monkeypatch` to stub out `requests.get/post/put/delete` — there is no live server or Docker Compose dependency for running tests. See `tests/conftest.py`.

## Architecture

### Facade pattern around `Client`

`pypufferblow/client.py` defines `Client`, the single entry point. Each API surface (`users`, `channels`, `storage`, `system`, `admin`, `decentralized_auth`, `federation`, `websocket`) is exposed as a method that, when called, **replaces itself on the instance with the constructed object** (e.g. `self.users()` builds a `Users` instance and reassigns `self.users = <that instance>`). This is why usage looks like `client.users.sign_in()` even though `users` started life as a bound method — calling `Client.__init__` already triggers `self.users()` once. Most other facades (`channels`, `storage`, `admin`, `websocket`, `federation`, `decentralized_auth`) require `users.sign_in()`/`sign_up()` to have happened first and raise a plain `Exception` or `FaildToInitChannels` if not.

### Routes are data, assigned dynamically

`pypufferblow/routes.py` defines route tables as lists of `Route` objects (`pypufferblow/models/route_model.py`: `api_route`, `methods`, `forward_to`) per domain (`users_routes`, `channels_routes`, `storage_routes`, `system_routes`, `admin_routes`, `decentralized_auth_routes`, `federation_routes`, `direct_messages_routes`). `Client._build_routes()` prefixes each with the resolved `api_base_url`, and `Client._assign_routes()` attaches them to the target object as named attributes (e.g. `SIGNIN_API_ROUTE`) by positional index into the route list — so the order of routes in `routes.py` and the order of attribute names passed to `_assign_routes` in `client.py` must stay in sync when adding/reordering routes.

### Options model and instance targeting

`pypufferblow/models/options_model.py`'s `OptionsModel` (base of `ClientOptions`, `UsersOptions`, etc.) normalizes `instance=` (a full URL, preferred for federated/production use) vs. legacy `host=`/`port=` into a single `instance_url`, infers `http` vs `https` (and `ws` vs `wss`) based on whether the host looks local (`normalize_instance`, `infer_scheme`, `http_to_websocket_base`), and wires up SDK-wide logging via `configure_sdk_logging` when `verbose=True` or `log_level` is set.

### Sync + async dual API

Nearly every network-calling method has a sync version (using `requests`) and an `..._async` sibling. The async version is almost always a thin wrapper: `async def X_async(self): return await asyncio.to_thread(self.X)`. When adding a new SDK method, follow this pattern rather than writing a separate async implementation — only deviate here if streaming/websocket behavior requires true async (see `websocket.py`, which uses the `websockets` library directly for `GlobalWebSocket`).

### Exceptions map to server failure modes

`pypufferblow/exceptions.py` defines one plain `Exception` subclass per server-side failure (`UsernameNotFound`, `InvalidPassword`, `BadAuthToken`, `ChannelNotFound`, `MessageIsTooLong`, etc.), each raised by inspecting HTTP status codes/response bodies in the relevant module (`users.py`, `channels.py`, ...). New server error cases should get a new exception class here rather than leaking raw `requests` exceptions or generic `Exception`s (the handful of generic `raise Exception(...)` calls in `client.py` for "not signed in" are the existing exception).

### Bot framework (`bot.py`, ~1500 lines)

`Bot`/`BotOptions` wrap a `Client` and provide a Discord.py-style decorator API: `@bot.command(...)`, `@bot.message(...)`, lifecycle hooks (`@bot.startup()`, `@bot.connect()`, `@bot.started()`, `@bot.shutdown()`, matching the `LIFECYCLE_EVENTS` set), `@bot.cooldown(...)`, `@bot.check(...)`, `@bot.loop(...)`, command groups (`bot.group(...)`), and `bot.wait_for(...)`/`bot.wait_until_ready()`. Commands are introspected via `inspect`/`get_type_hints` to coerce typed positional/keyword args (`str`, `int`, `bool`, `*args`) from the raw message text (tokenized with `shlex`). Registration dataclasses (`CommandRegistration`, `MessageRegistration`, `ConditionalEventRegistration`, `LoopTask`, `EventWaiter`) hold the decorator metadata; `BotContext` is what every handler receives (`ctx.content`, `ctx.reply()`, `ctx.author_id`, etc. — see the table in `README.md`).

### Models

`pypufferblow/models/` holds plain data classes for `UserModel`, channel/message payloads (`channel_model.py`, `message_model.py`, including `WebSocketMessage` used by the bot's websocket dispatch), `OptionsModel`, and `Route`. These are hand-written (not pydantic, despite `pydantic` being a listed dependency) — check `models/user_model.py`/`message_model.py` for the actual field set before assuming a field exists (e.g. `*_lqip_url` fields are planned per `SDK_ROADMAP.md` but not yet implemented).

### Where the SDK is behind the server

`SDK_ROADMAP.md` tracks known gaps between the Pufferblow server's API surface and what this SDK exposes (reactions, LQIP media helpers, search, voice, moderation, roles, local DMs, global rate-limit handling). Check it before assuming a feature is unsupported vs. simply not yet requested, and update it when closing a gap.

## Conventions worth matching

- Numbered test files (`tests/test_01_client_object.py` ... `test_13_storage_sdk.py`) indicate intended read/run order by subsystem introduction, not strict dependency — follow the numbering convention for new test files.
- Route endpoint paths and HTTP methods are the contract with the server; don't change an existing `Route` entry without confirming the server-side route actually matches (there is no server code in this repo to check against — check `SDK_ROADMAP.md` or ask).
- `instance=` is the preferred way to configure `ClientOptions`/`BotOptions` for anything beyond local dev; `host=`/`port=` is legacy/local-dev compatibility, not the primary path for new examples or docs.
