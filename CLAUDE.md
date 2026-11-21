# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegramusic is a Telegram bot that downloads music from Deezer, YouTube, and SoundCloud. Users interact via inline search queries or by sending direct links. Built with Python 3.13, aiogram 3, and yt-dlp.

The feature set is intentionally minimal — no persistence/database, no per-user settings. Most users download single tracks via Deezer.

## Running the Bot

### Docker (production)
```bash
./update.sh  # pulls, builds, and starts the container
# or manually: docker compose up -d --build
```

### Local development
```bash
# Set environment variables (or source token.env)
export DEEZER_TOKEN=... TELEGRAM_TOKEN=...
python3.13 -m pip install -r requirements.txt
python3.13 main.py
```

### Linting
```bash
ruff check .
```

No test suite exists.

## Architecture

**Entry point:** `main.py` — registers routers, handles `/start` deep-links (for inline download buttons), starts aiogram polling.

**Bot singleton:** `bot.py` — creates the shared `Bot` and `Dispatcher` instances from `TELEGRAM_TOKEN`.

**Handlers (aiogram Routers):**
- `handlers/deezer.py` — Deezer track/album/shortlink message handlers + inline query search. Manages download lifecycle (retry logic, session refresh, zip creation, Telegram upload). This is by far the largest module.
  - **Inline search** supports `track <query>` (default) and `album <query>` prefixes. Results are shown with a "Download" button that deep-links back to the bot via `/start`.
  - **Shortlink resolution** handles `deezer.page.link` and `link.deezer.com` URLs, resolving them to track/album links.
  - Playlist support existed but was **intentionally removed** — the regex `PLAYLIST_REGEX` remains but is unused. Do not re-implement.
- `handlers/yt_dlp.py` — YouTube and SoundCloud handlers via yt-dlp. Two separate routers (`youtube_router`, `soundcloud_router`).

**Download core:**
- `dl_utils/deezer_download.py` — Deezer session management (ARL cookie auth), Blowfish decryption of streams, metadata tagging (mutagen), search API. **Forked from [kmille/deezer-downloader](https://github.com/kmille/deezer-downloader)** with local modifications: `get_file_format()` with per-track quality fallback (FLAC → MP3_320 → MP3_128), `deezer_format` passed as parameter instead of relying on the global, `DeezerApiException` vs `RuntimeError` distinction for session auto-refresh, `ALB_ART_NAME` fetch in `get_song_infos_from_deezer_website`, expired ARL detection (`USER.USER_ID == 0` raises `DeezerArlExpiredException`, a `DeezerApiException`), `require_session()`, HTTP timeouts on every request, `DEEZER_PROXY` passed to the `get_url` call, and `new_http_session()`, which retries a request once when Deezer has closed an idle connection (used for the main session and the `get_url` call). When syncing with upstream, preserve these differences. Uses global `session` and `license_token` state: `init_deezer_session` builds the new session first and only then replaces the globals, so download threads never see a half-built session.
- `dl_utils/deezer_utils.py` — Filename sanitization and audio duration helpers.

**Shared state:** `utils.py` — i18n via `langs.json` (the `__()` function), per-user download lock (`DOWNLOADING_USERS` list), `TMP_DIR` constant.

## Key Design Patterns

- Deezer downloads use Blowfish CBC decryption with a per-song key derived from `SNG_ID`. Every third 2048-byte block is encrypted.
- The Deezer session auto-refreshes after `DEEZER_SESSION_REINIT_THRESHOLD` consecutive failures (default 3). Refreshes run one at a time, and a refresh asked for while another was running is skipped. A failed refresh is logged and the retry loop goes on.
- An expired ARL does not stop the bot at startup: it logs an error, downloads fail with a clear message, and inline search shows that the token expired.
- Album tracks download in parallel via `asyncio.gather`, each with its own retry loop, at most `ALBUM_DOWNLOAD_CONCURRENCY` (4) at a time.
- Every blocking call in async code runs in a thread (`asyncio.to_thread` / `run_in_executor`): Deezer page and stream downloads, Deezer API metadata and covers, zip creation, yt-dlp.
- Every HTTP request uses `HTTP_TIMEOUT` from `utils.py` (connect 10 s, read 60 s per read, so long streams still work).
- Each download gets its own temp directory (`tempfile.mkdtemp` under `tmp/deezer/`), so 2 users can download the same item at once.
- Without `FORMAT=zip`, a FLAC track too big for Telegram's 50 MB upload limit is downloaded as MP3 instead. YouTube videos over 20 minutes are refused before download for the same reason.
- An album of 2 to 10 tracks is sent as one media group (Telegram allows 10 at most). A bigger album is sent one track per message. Tracks are sorted by disc then track number.
- Output format is controlled by `FORMAT=zip` env var; when set, tracks are bundled in zip archives (auto-split at 48MB for Telegram's limit).

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_TOKEN` | Yes | Telegram Bot API token |
| `DEEZER_TOKEN` | Yes | Deezer ARL cookie |
| `BOT_LANG` | No | Language code for bot messages (default: `en`, available in `langs.json`) |
| `ENABLE_FLAC` | No | Set to `1` for FLAC downloads (requires Deezer Premium) |
| `FORMAT` | No | Set to `zip` to bundle downloads as zip archives |
| `COPY_FILES_PATH` / `FILE_LINK_TEMPLATE` | No | Serve zips via HTTP instead of Telegram upload |
| `MAX_RETRIES` | No | Download retry count (default: 5) |
| `COOKIES_PATH` | No | Path to `cookies.txt` for yt-dlp (YouTube auth) |
| `YT_PLAYER_CLIENT` | No | Comma-separated yt-dlp player clients |
| `DEEZER_PROXY` | No | HTTPS proxy for Deezer requests |
| `SEND_ALBUM_COVER` | No | Set to `false` to skip sending album art |

## yt-dlp & YouTube status

YouTube has deployed 3 layers of protection that affect yt-dlp:

1. **JS challenges (sig/nsig)** — stream URLs are encrypted by obfuscated JS in the YouTube player, changing with each update.
2. **poToken (BotGuard)** — an attestation token proving the request comes from a real client (browser/mobile app).
3. **Datacenter IP blocking** — YouTube detects server IPs and requires login ("Sign in to confirm you're not a bot").

**Without EJS** (current bot setup): uses `JSInterp`, a Python-based JS interpreter that is deprecated and no longer follows YouTube changes. Still works for some very popular videos (via `android_vr` client), but fails with `LOGIN_REQUIRED` on many videos from datacenter IPs.

**With EJS** (real JS runtime — Node/Deno/Bun): resolves JS challenges by executing YouTube's actual JS, gives access to more formats and clients. However, **does not solve datacenter IP blocking** — same `LOGIN_REQUIRED` errors occur.

The core issue is IP-level blocking, not yt-dlp itself. Without cookies or a residential proxy, many videos won't work from a datacenter, regardless of runtime or bot configuration.

**SoundCloud** restricts full track downloads to Go+ subscribers. Without authentication, yt-dlp only retrieves ~30-second previews. The YouTube/SoundCloud code is kept in the codebase.

## Auxiliary Tools

`arl_fetcher/` — standalone Bun/TypeScript script using Puppeteer to extract a Deezer ARL cookie from email/password login. Run with `bun start` (separate from the bot).

## Design Decisions

- **No persistence/database** — the bot is stateless by design. No download history, no per-user preferences, no favorites. Users have their music in Telegram chats.
- **No playlist support** — was implemented and removed. Not worth the complexity.
- **Quality is global, not per-user** — determined by the Deezer account (ARL token) and `ENABLE_FLAC` env var. Per-user quality selection is not feasible without persistence and wouldn't make sense since it depends on the Deezer subscription.
- **Cross-platform link matching (Spotify → Deezer, etc.) is unreliable** — even dedicated services like Odesli/song.link produce frequent false positives (remastered versions, live/studio mismatches, featuring order differences).

## Debugging

Filter bot logs for user activity:
```bash
docker logs telegramusic 2>/dev/null | grep "USER_DEBUG"
```
