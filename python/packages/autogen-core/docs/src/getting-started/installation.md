# Installation

The repo is private, so the installation process is a bit more involved than usual.

## Option 1: Install from a local clone

Make a clone of the repo:

```sh
git clone https://github.com/microsoft/autogen_core.git
```

You can install the package by running:

```sh
cd autogen_core/python
pip install .
```

## Option 2: Install from GitHub

To install the package from GitHub, you will need to authenticate with GitHub.

```sh
GITHUB_TOKEN=$(gh auth token)
pip install "git+https://oauth2:$GITHUB_TOKEN@github.com/microsoft/autogen_core.git#subdirectory=python"
```

### Using a Personal Access Token instead of `gh` CLI

If you don't have the `gh` CLI installed, you can generate a personal access token from the GitHub website.

1. Go to [New fine-grained personal access token](https://github.com/settings/personal-access-tokens/new)
2. Set `Resource Owner` to `Microsoft`
3. Set `Repository Access` to `Only select repositories` and select `Microsoft/autogen_core`
4. Set `Permissions` to `Repository permissions` and select `Contents: Read`
5. Use the generated token for `GITHUB_TOKEN` in the commad above
