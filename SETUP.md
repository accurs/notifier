# Setup

1. Talk to [@BotFather](https://t.me/BotFather), run `/newbot`, and copy the token.
2. Create a channel, or pick an existing one. Add the bot as an **administrator** with permission to post messages.
3. Set the chat id:
   - Public channel: `@channelname`
   - Private channel: send a message in the channel, then open `https://api.telegram.org/bot<token>/getUpdates` and copy `chat.id`. It looks like `-100…`.
4. Copy the env file and fill in every line:

```bash
cp .env.example .env
```

`FORGE` is `forgejo`, `gitea`, `gogs`, `github`, or `gitlab`. `FORGE_WEB` is the site you open in a browser. `FORGE_API` is the API root:

| Forge | `FORGE_API` |
| --- | --- |
| Forgejo, Gitea, Gogs | `https://host/api/v1` |
| GitHub | `https://api.github.com` |
| GitLab | `https://gitlab.com/api/v4` |

`FORGE_BRANCH=*` watches every branch. Leave `FORGE_TOKEN` blank for a public repo. Leave `TELEGRAM_THREAD_ID` blank if you are not posting into a forum topic.

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

| Forge | Where | Secret |
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

If the bot is only reachable on your LAN, skip the webhook and set `POLL_INTERVAL` to something other than `0`.
