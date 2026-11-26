#!/bin/sh
# Docker creates a missing bind mount as root:root, which the bot user cannot
# write. Fix the state directory, then drop privileges.
set -eu

if [ -z "${STATE_PATH:-}" ]; then
    echo "STATE_PATH is not set. Fill it in from the env file." >&2
    exit 1
fi

case "$STATE_PATH" in
    /*) state_dir=$(dirname "$STATE_PATH") ;;
    *) state_dir="/app/$(dirname "$STATE_PATH")" ;;
esac

mkdir -p "$state_dir"

if [ "$(id -u)" = 0 ]; then
    chown bot:bot "$state_dir"
    chmod 755 "$state_dir"
    exec setpriv --reuid=bot --regid=bot --clear-groups --inh-caps=-all "$@"
fi

exec "$@"
