<h1 align="center">
  <br>
  Telegramusic
  <br>
</h1>

<h4 align="center">A Telegram bot and Mini App to search and download music from Deezer, YouTube and SoundCloud</h4>

> [!WARNING]
> For educational purposes only. Downloading from Deezer is against **Deezer's terms of service**.

## What it does

- Search Deezer from any chat with inline mode, then download a track or a whole album.
- Search, preview and browse albums in an optional [Mini App](#mini-app) opened from the bot.
- Send a Deezer, YouTube or SoundCloud link to the bot to get the audio file.
- Files come with tags and album art. FLAC is available with Deezer Premium.

<p align="center">
  <img src="https://user-images.githubusercontent.com/24623168/141982877-ca7589d4-fe47-4b5a-b751-6d945c21f944.png" height="360" alt="Inline search results">
  &nbsp;
  <img src="https://user-images.githubusercontent.com/24623168/141983477-b7692d78-134a-4176-98ba-d6388ac4b80b.png" height="360" alt="A downloaded track in Telegram">
  <br>
  <sub>Inline search, and the track the bot sends</sub>
</p>

## Quick start

You need 2 tokens:

1. A Deezer `arl` cookie. See [how to find your Deezer ARL cookie](https://github.com/nathom/streamrip/wiki/Finding-Your-Deezer-ARL-Cookie).
2. A Telegram bot token from [BotFather](https://t.me/botfather). In BotFather, also turn on **Inline Mode** for your bot.

Create a `token.env` file next to `docker-compose.yml`:

```dotenv
DEEZER_TOKEN=your_arl_cookie
TELEGRAM_TOKEN=123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ
BOT_LANG=en
```

Then start the bot with [Docker](https://docs.docker.com/engine/install/):

```bash
./update.sh
```

This pulls the latest code, builds the image and starts the container. Run it again to update the bot.

### Without Docker

With [uv](https://docs.astral.sh/uv/), which also installs the right Python version:

```bash
export DEEZER_TOKEN=... TELEGRAM_TOKEN=...
uv venv
uv pip install -r requirements.txt
uv run main.py
```

Or with Python 3.13 and a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## How to use it

Search in any chat with inline mode. `track` is the default:

```
@your_bot track <search>
@your_bot album <search>
```

Pick a result, then press **Download**. You can also send a Deezer, YouTube or SoundCloud link to the bot directly.

If you set up the [Mini App](#mini-app), tap the menu button next to the message field to search, preview and download from a full page.

## Mini App

The Mini App is a search page that opens inside Telegram, from the button next to the message field or the **Open** button in the chat list. It lets you:

- search tracks and albums as you type, or browse the Deezer charts
- open an album to see its track list
- play a 30-second preview
- download a track or an album with one tap

It is optional. The bot works the same without it.

The page is one static file, `webapp/index.html`. It talks to the public Deezer API from the browser and needs no server of its own. A download opens a `/start` link to your bot, which sends the file to the chat as usual. The text follows each user's Telegram language.

### Set up the Mini App

1. Host the `webapp` folder on any static host with HTTPS, such as [Netlify](https://www.netlify.com/) or [Cloudflare Pages](https://pages.cloudflare.com/). With the Netlify CLI:

   ```bash
   npx netlify-cli deploy --dir webapp --prod
   ```

2. In [BotFather](https://t.me/botfather), open your bot, then **Bot Settings → Configure Mini App**:
   - **Main App**: turn it on and set the URL to `https://<your-site>/<your_bot_username>`, without the `@`. Choose the **Fullsize** launch mode.
   - **Menu Button**: set the same URL, with a short title such as `Search`.

The page reads your bot username from the URL, so you can host it publicly without naming your bot in the code. The URL must be 64 characters or fewer, so pick a short site name.

`webapp/_redirects` sends every path to `index.html`. Netlify and Cloudflare Pages read this file. On another host, either set up the same rewrite or use `https://<your-site>/?bot=<your_bot_username>`.

`webapp/_headers` asks search engines not to index the page.

To force a language, add `?lang=fr` (or `en`, `de`, `es`, `pt`, `in`, `zh`, `ar`) to the URL.

## Configuration

Set these variables in `token.env`. Run `./update.sh` after each change.

| Variable | Default | What it does |
|---|---|---|
| `DEEZER_TOKEN` | required | Deezer `arl` cookie |
| `TELEGRAM_TOKEN` | required | Telegram bot token |
| `BOT_LANG` | `en` | Bot language: `en`, `fr`, `de`, `es`, `pt`, `in`, `zh` or `ar` |
| `ENABLE_FLAC` | `0` | Set to `1` for FLAC downloads (needs Deezer Premium) |
| `FORMAT` | | Set to `zip` to send downloads as zip files, cover included |
| `COPY_FILES_PATH` | | Folder where zip files are saved, to share them by link (see below) |
| `FILE_LINK_TEMPLATE` | | Download link for those files, for example `https://example.com/dl/{0}` |
| `SEND_ALBUM_COVER` | `true` | Set to `false` to stop sending the album cover with each download |
| `MAX_RETRIES` | `5` | Download attempts per track |
| `DEEZER_PROXY` | | HTTPS proxy for Deezer requests |
| `YT_PLAYER_CLIENT` | `tv,web_safari,web_embedded,android_vr` | yt-dlp player clients, separated by commas |

### File size limit

Telegram bots can upload files up to 50 MB:

- a FLAC track over this limit is sent as MP3 instead
- zip files over the limit are split into several parts
- YouTube and SoundCloud audio over 20 minutes is refused

### Share zip files by link

To avoid the 50 MB limit, the bot can save zip files to a folder and send a link instead. Serve that folder with a web server such as Nginx or Caddy.

```dotenv
FORMAT=zip
COPY_FILES_PATH=/files
FILE_LINK_TEMPLATE=https://example.com/dl/{0}
```

The bot replaces `{0}` with the file name. With Docker, mount your folder on `/files` in `docker-compose.yml`:

```yaml
volumes:
  - /path/to/your/folder:/files
```

## YouTube and SoundCloud limits

These sources work less well than Deezer. The bot uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) for both.

**YouTube** blocks many requests that come from servers, and asks to "sign in to confirm you're not a bot". Popular videos often still work. For the others, you need cookies from a YouTube account or a residential proxy.

**SoundCloud** only gives 30-second previews without a Go+ subscription.

### Use YouTube cookies

1. Export a `cookies.txt` file. See [how to pass cookies to yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp).
2. Put it in `./local_resources/cookies.txt`.

The bot reads the file on each YouTube download, so you do not need to restart it.

> [!WARNING]
> YouTube may ban the account the cookies come from.

## Debugging

User actions are logged with a `USER_DEBUG` prefix:

```bash
docker logs telegramusic 2>/dev/null | grep "USER_DEBUG"                     # all user actions
docker logs telegramusic 2>/dev/null | grep "USER_DEBUG.*user_id=123456789"  # one user
docker logs telegramusic 2>/dev/null | grep "USER_DEBUG.*Error"              # errors only
```

## Translations

Bot messages are in `langs.json`. To add your language, open a pull request or send me a message.
