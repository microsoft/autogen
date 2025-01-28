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

# ADDED BY MSR Frontiers
#########################
SITE_URLS = {
    "reddit": REDDIT,
    "gitlab": GITLAB, 
    "shopping": SHOPPING,
    "shopping_admin": SHOPPING_ADMIN,
    "shopping_site_admin": SHOPPING_ADMIN,
    "map": MAP,
    "wikipedia": WIKIPEDIA,
}

LOGIN_PROMPTS = {
    "reddit": f"Type '{REDDIT}' into the address bar to navigate to the site. Click 'Log in', type the username '{ACCOUNTS['reddit']['username']}', and password is '{ACCOUNTS['reddit']['password']}'. Finally click the login button.",
    "gitlab": f"Type '{GITLAB}' into the address bar to navigate to the site. At the log in prompt, type the username '{ACCOUNTS['gitlab']['username']}', and the password '{ACCOUNTS['gitlab']['password']}'. Finally click the 'Sign in' button.",
    "shopping": f"Type '{SHOPPING}' into the address bar to navigate to the site. Click 'Sign In' at the top of the page. Enter the Email '{ACCOUNTS['shopping']['username']}', and password '{ACCOUNTS['shopping']['password']}'. Finally click the 'Sign In' button.",
    "shopping_admin": f"Type '{SHOPPING_ADMIN}' into the address bar to navigate to the site. At the log in prompt, enter the username '{ACCOUNTS['shopping_admin']['username']}', and the password '{ACCOUNTS['shopping_admin']['password']}'. Finally click the 'Sign In' button.",
}

SITE_DESCRIPTIONS = {
    "reddit": "a Postmill forum populated with a large sample of data crawled from Reddit. Postmill is similar to Reddit, but the UI is distinct, and 'subreddits' begin with /f/ rather than /r/",
    "gitlab": "a Gitlab site populated with various programming projects. Gitlab is similar to GitHub, though the UIs are slightly different",
    "shopping": "an online store built with the Magento open source eCommerce platform",
    "shopping_admin": "the content management admin portal for an online store running the Magento open source eCommerce software",
}


def url_to_sitename(url):
    if url.startswith(REDDIT):
        return "reddit"
    elif url.startswith(GITLAB):
        return "gitlab"
    elif url.startswith(SHOPPING):
        return "shopping"
    elif url.startswith(SHOPPING_ADMIN):
        return "shopping_admin"
    else:
        return None
