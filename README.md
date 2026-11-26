# Commit notifier

The Telegram bot for https://t.me/+Pmh7P8NAR1QzOTdh

Posts a Telegram channel message whenever a commit lands on a git forge.
Forgejo, Gitea, Gogs, GitHub, and GitLab are supported. Every setting comes
from the env file. The program does not fill in missing values.

Two ways it hears about commits:

- **Webhook** — the forge pushes the event here as soon as it happens.
- **Poll** — every `POLL_INTERVAL` seconds it asks the forge API, so it still works if this process is not reachable from the forge.

Seen commit ids are stored in `STATE_PATH`. The first run records the current history and does not replay it.

## Setup

1. Talk to [@BotFather](https://t.me/BotFather), run `/newbot`, and copy the token.
2. Create a channel (or pick an existing one). Add the bot as an **administrator** with permission to post messages.
3. Set the chat id:
   - Public channel: `@channelname`
   - Private channel: send a message in the channel, then open `https://api.telegram.org/bot<token>/getUpdates` and copy `chat.id` (it looks like `-100…`).
4. Copy the env file and fill in every line:

```bash
cp .env.example .env
```

5. Check the formatter against the live repo, then send the current latest commit once:

```bash
python3 bot.py --preview
python3 bot.py --send-latest
```

6. Leave it running:

```bash
python3 bot.py
```

Or with Docker:

```bash
docker compose up -d --build
```

## Webhook

| Forge | Where | Secret header |
| --- | --- | --- |
| Forgejo, Gitea, Gogs | Settings → Webhooks → Add webhook | HMAC, same string as `WEBHOOK_SECRET` |
| GitHub | Settings → Webhooks → Add webhook | `X-Hub-Signature-256`, same secret |
| GitLab | Settings → Webhooks | Secret token, sent as `X-Gitlab-Token` |

| Field | Value |
| --- | --- |
| Target URL | `https://<your-host>:<WEBHOOK_PORT><WEBHOOK_PATH>` |
| Content type | `application/json` |
| Trigger | Push events |
| Branch filter | the same branch as `FORGE_BRANCH`, or blank if that is `*` |

A successful delivery is HTTP 204. Unsigned requests are rejected. Ping and other non-push events are ignored.

If the bot is only reachable on your LAN, skip the webhook and set `POLL_INTERVAL` to something other than `0`. A public repo does not need `FORGE_TOKEN`.

## Message

```
vael/paradise
main · 1 new commit · accurs

• 7bb593d Convert all submodules into regular directories — accurs
```

The branch name links to that branch. The short hash links to the commit. A push with several commits is one message.
