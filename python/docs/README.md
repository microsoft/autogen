## Building the AutoGen Documentation

AutoGen documentation is based on the sphinx documentation system and uses the myst-parser to render markdown files. It uses the [pydata-sphinx-theme](https://pydata-sphinx-theme.readthedocs.io/en/latest/) to style the documentation.

### Prerequisites

Ensure you have all of the dev dependencies for the `autogen-core` package installed. You can install them by running the following command from the root of the python repository:

```bash
uv sync
source .venv/bin/activate
```

## Building Docs

To build the documentation, run the following command from the root of the python directory:

```bash
poe docs-build
```

To serve the documentation locally, run the following command from the root of the python directory:

```bash
poe docs-serve
```

[!NOTE]
Sphinx will only rebuild files that have changed since the last build. If you want to force a full rebuild, you can delete the `./docs/build` directory before running the `docs-build` command.
