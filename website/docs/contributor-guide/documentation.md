# Documentation

## How to get a notebook rendered on the website

See [here](https://github.com/microsoft/autogen/blob/main/notebook/contributing.md#how-to-get-a-notebook-displayed-on-the-website) for instructions on how to get a notebook in the `notebook` directory rendered on the website.

## Build documentation locally

1\. To build and test documentation locally, first install [Node.js](https://nodejs.org/en/download/). For example,

```bash
nvm install --lts
```

Then, install `yarn` and other required packages:

```bash
npm install --global yarn
pip install pydoc-markdown pyyaml termcolor
```

2\. You also need to install quarto. Please click on the `Pre-release` tab from [this website](https://quarto.org/docs/download/) to download the latest version of `quarto` and install it. Ensure that the `quarto` version is `1.5.23` or higher.

3\. Finally, run the following commands to build:

```console
cd website
yarn install --frozen-lockfile --ignore-engines
pydoc-markdown
python process_notebooks.py render
yarn start
```

The last command starts a local development server and opens up a browser window.
Most changes are reflected live without having to restart the server.

## Build with Docker

To build and test documentation within a docker container. Use the Dockerfile in the `dev` folder as described above to build your image:

```bash
docker build -f .devcontainer/dev/Dockerfile -t autogen_dev_img https://github.com/microsoft/autogen.git#main
```

Then start the container like so, this will log you in and ensure that Docker port 3000 is mapped to port 8081 on your local machine

```bash
docker run -it -p 8081:3000 -v `pwd`/autogen-newcode:newstuff/ autogen_dev_img bash
```

Once at the CLI in Docker run the following commands:

```bash
cd website
yarn install --frozen-lockfile --ignore-engines
pydoc-markdown
python process_notebooks.py render
yarn start --host 0.0.0.0 --port 3000
```

Once done you should be able to access the documentation at `http://127.0.0.1:8081/autogen`
