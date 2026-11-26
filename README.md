# Commit notifier

The Telegram bot for [paradise](https://t.me/+Pmh7P8NAR1QzOTdh).

It posts a channel message whenever a commit lands on a git forge. Forgejo, Gitea, Gogs, GitHub, and GitLab are supported. Every setting comes from the env file. Nothing is filled in for you.

It hears about commits two ways:

- **Webhook.** The forge pushes the event here as soon as it happens.
- **Poll.** Every `POLL_INTERVAL` seconds it asks the forge API, so it still works if this process is not reachable from the forge.

Seen commit ids are stored at `STATE_PATH`. The first run records the current history and does not replay it.

## Message

```
vael/paradise
main · 1 new commit · accurs

• 7bb593d Convert all submodules into regular directories — accurs
```

The branch name links to that branch. The short hash links to the commit. A push with several commits is one message.

## Setup

See [setup.md](setup.md).
