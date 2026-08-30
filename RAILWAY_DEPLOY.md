# 🚀 Railway Deployment Guide

This bot is a **long-running Telegram poller** — it does not expose any HTTP
port. Railway simply has to keep `python main.py` alive, which is already
configured for you.

## What's already prepared

| File             | Purpose                                                        |
|------------------|----------------------------------------------------------------|
| `railway.json`   | Railway uses the **Nixpacks** builder and runs `python main.py`; auto-restarts on crash (10 retries) |
| `runtime.txt`    | Pins Python **3.11.9** so the cloud runtime matches the local env |
| `requirements.txt` | The exact, tested dependency set (aiogram, aiosqlite, python-dotenv, pydantic-settings) |
| `.env.example`   | Template for the required env vars                              |
| `.gitignore`     | Keeps `.env`, `*.db`, `__pycache__`, caches out of git          |

## 1. Create the GitHub repository

Run from this folder:

```powershell
git remote add origin https://github.com/dimaplayuz-hash/kodli-bot.git
git branch -M main
git push -u origin main
```

(Replace the URL with the repo you actually create under your GitHub account
`dimaplayuz-hash`.)

Or create an empty repo on github.com first, then push with the URL GitHub shows.

## 2. Deploy on Railway

1. Log in to [railway.app](https://railway.app) with the GitHub account `dimaplayuz-hash`.
2. **New Project → Deploy from GitHub repo →** select `kodli-bot`.
3. Railway auto-detects the Python app (Nixpacks) and uses `railway.json` to launch `python main.py`.
4. Add the required **Variables**:

   | Variable     | Value                                                  |
   |--------------|--------------------------------------------------------|
   | `BOT_TOKEN`  | Token from @BotFather (e.g. `1234567890:AA...`)        |
   | `ADMIN_IDS`  | Comma-separated Telegram IDs, e.g. `123456789,987654321` |

5. **HIGHLY RECOMMENDED — persist the SQLite database:**
   - Railway's filesystem is **ephemeral**: without extra setup the database
     resets every time the service redeploys.
   - Add a **Volume** mounted at **`/data`** (Settings → Volumes → mount path `/data`).
   - Add the variable `DATABASE_PATH=/data/kodli.db`.
   - Now all movies/users/logs survive redeploys.

6. Click **Deploy** and open **Logs**.
   - Success looks like:
     `Database ready: kodli.db` → `Polling boshlandi...`
7. Send `/start` to your bot in Telegram to verify.

## Notes / caveats

- **Polling mode**: `main.py` calls `delete_webhook()` + `start_polling()`.
  No public URL, webhook or port config is needed. Do **not** set one up on
  Railway — it would fail because there is no HTTP server.
- **Secrets**: `.env` is git-ignored and never reaches the repo. On Railway the
  values come from Variables, which `config.py` reads automatically
  (pydantic-settings maps `BOT_TOKEN`/`ADMIN_IDS` to the settings).
- **Restarts**: Railway restarts the service on failure up to 10 times. With
  the Volume in place, bans/flood counters survive restarts too.
- **Small delay at boot** is normal: Nixpacks installs dependencies from
  `requirements.txt` on the first build.