# Website

This website is built using [Docusaurus 3](https://docusaurus.io/), a modern static website generator.

## Prerequisites

To build and test documentation locally, begin by downloading and installing [Node.js](https://nodejs.org/en/download/), and then installing [Yarn](https://classic.yarnpkg.com/en/).
On Windows, you can install via the npm package manager (npm) which comes bundled with Node.js:

```console
npm install --global yarn
```

## Installation

```console
pip install pydoc-markdown pyyaml colored
cd website
yarn install
```

### Install Quarto

`quarto` is used to render notebooks.

Install it [here](https://quarto.org/docs/get-started/).

> Note: Support for Docusaurus 3.0 in Quarto is from version `1.4`. Ensure that your `quarto` version is `1.4` or higher.

## Local Development

Navigate to the `website` folder and run:

```console
pydoc-markdown
quarto render ./docs
python ./process_notebooks.py
yarn start
```

This command starts a local development server and opens up a browser window. Most changes are reflected live without having to restart the server.

## Running htmlproofer

`htmlproofer` is a tool to check for broken links and other issues in HTML files.

1. [Install `htmlproofer`](https://github.com/gjtorikian/html-proofer?tab=readme-ov-file#installation)
2. Ensure site is completely built
3. `htmlproofer REPO_ROOT/website/build/ --swap-urls '^/autogen/:/' --disable-external --ignore-missing-alt`
