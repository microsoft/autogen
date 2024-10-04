from pathlib import Path
from string import Template
import sys

THIS_FILE_DIR = Path(__file__).parent


# Contains single text template $to_url
HTML_PAGE_TEMPLATE_FILE = THIS_FILE_DIR / "redirect_template.html"
HTML_REDIRECT_TEMPLATE = HTML_PAGE_TEMPLATE_FILE.open("r").read()
REDIRECT_URLS_FILE = THIS_FILE_DIR / "redirect_urls.txt"

def generate_redirect(old_url: str, new_url: str, base_dir: Path):
    # Create a new redirect page
    redirect_page = Template(HTML_REDIRECT_TEMPLATE).substitute(to_url=new_url)

    # If the url ends with /, add index.html
    if old_url.endswith("/"):
        old_url += "index.html"
    else:
        old_url += "/index.html"

    if old_url.startswith("/"):
        old_url = old_url[1:]

    # Create the path to the redirect page
    redirect_page_path = base_dir / old_url

    # Create the directory if it doesn't exist
    redirect_page_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the redirect page
    with open(redirect_page_path, "w") as f:
        f.write(redirect_page)


def main():
    if len(sys.argv) != 2:
        print("Usage: python redirects.py <base_dir>")
        sys.exit(1)

    base_dir = Path(sys.argv[1])

    # Read file
    with open(REDIRECT_URLS_FILE, "r") as f:
        lines = f.readlines()

    for line in lines:
        # Replace /autogen/ with /autogen/0.2/ and generate redirect
        old_url = line.strip()
        new_url = old_url.replace("/autogen/", "/autogen/0.2/")
        generate_redirect(old_url, new_url, base_dir)

if __name__ == '__main__':
    main()