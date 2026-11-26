"""
Limits and names that do not come from the environment.
"""

# Telegram will not deliver a message longer than this.
TELEGRAM_MESSAGE_LIMIT = 4096

# How many commit ids we keep, so a restart still knows what it already posted.
SEEN_LIMIT = 1000

# Drop webhook bodies larger than this instead of reading them all.
MAX_WEBHOOK_BODY = 2 * 1024 * 1024

# A branch delete arrives as a push whose "after" sha is all zeros.
DELETED_SHA = "0" * 40

# How long a commit subject can be before it is cut off.
MESSAGE_LINE = 180

# How many times to try a Telegram send before giving up.
ATTEMPTS = 4

# HTTP client.
TIMEOUT_SECONDS = 20
USER_AGENT = "tg-commit-notifier"

# Backup poll.
PAGE_SIZE = 50
SEED_COUNT = 20
MAX_PAGES = 5

FORGE_KINDS = ("forgejo", "gitea", "gogs", "github", "gitlab")

# Must be set, and must not be blank.
REQUIRED = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "FORGE",
    "FORGE_WEB",
    "FORGE_API",
    "FORGE_REPO",
    "FORGE_BRANCH",
    "WEBHOOK_SECRET",
    "WEBHOOK_HOST",
    "WEBHOOK_PORT",
    "WEBHOOK_PATH",
    "POLL_INTERVAL",
    "STATE_PATH",
)

# Must be present in the env file, but may be left blank.
OPTIONAL = (
    "TELEGRAM_THREAD_ID",
    "FORGE_TOKEN",
)

EVENT_HEADERS = ("x-forgejo-event", "x-gitea-event", "x-gogs-event")

DELIVERY_HEADERS = (
    "x-forgejo-delivery",
    "x-gitea-delivery",
    "x-github-delivery",
    "x-gitlab-event-uuid",
)
