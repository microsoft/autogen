# websites domain
import os

REDDIT = os.environ.get("REDDIT", "")
SHOPPING = os.environ.get("SHOPPING", "")
SHOPPING_ADMIN = os.environ.get("SHOPPING_ADMIN", "")
GITLAB = os.environ.get("GITLAB", "")
WIKIPEDIA = os.environ.get("WIKIPEDIA", "")
MAP = os.environ.get("MAP", "")
HOMEPAGE = os.environ.get("HOMEPAGE", "")

REDDIT_USERNAME = os.environ.get("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.environ.get("REDDIT_PASSWORD", "")

GITLAB_USERNAME = os.environ.get("GITLAB_USERNAME", "")
GITLAB_PASSWORD = os.environ.get("GITLAB_PASSWORD", "")

SHOPPING_USERNAME = os.environ.get("SHOPPING_USERNAME", "")
SHOPPING_PASSWORD = os.environ.get("SHOPPING_PASSWORD", "")

SHOPPING_ADMIN_USERNAME = os.environ.get("SHOPPING_ADMIN_USERNAME", "")
SHOPPING_ADMIN_PASSWORD = os.environ.get("SHOPPING_ADMIN_PASSWORD", "")

assert REDDIT and SHOPPING and SHOPPING_ADMIN and GITLAB and WIKIPEDIA and MAP and HOMEPAGE, (
    "Please setup the URLs to each site. Current: \n"
    + f"Reddit: {REDDIT}\n"
    + f"Shopping: {SHOPPING}\n"
    + f"Shopping Admin: {SHOPPING_ADMIN}\n"
    + f"Gitlab: {GITLAB}\n"
    + f"Wikipedia: {WIKIPEDIA}\n"
    + f"Map: {MAP}\n"
    + f"Homepage: {HOMEPAGE}\n"
)

ACCOUNTS = {
    "reddit": {"username": REDDIT_USERNAME, "password": REDDIT_PASSWORD},
    "gitlab": {"username": GITLAB_USERNAME, "password": GITLAB_PASSWORD},
    "shopping": {"username": SHOPPING_USERNAME, "password": SHOPPING_PASSWORD},
    "shopping_admin": {"username": SHOPPING_ADMIN_USERNAME, "password": SHOPPING_ADMIN_PASSWORD},
    "shopping_site_admin": {"username": SHOPPING_ADMIN_USERNAME, "password": SHOPPING_ADMIN_PASSWORD},
}

URL_MAPPINGS = {
    REDDIT: "http://reddit.com",
    SHOPPING: "http://onestopmarket.com",
    SHOPPING_ADMIN: "http://luma.com/admin",
    GITLAB: "http://gitlab.com",
    WIKIPEDIA: "http://wikipedia.org",
    MAP: "http://openstreetmap.org",
    HOMEPAGE: "http://homepage.com",
}
