# AutoGenNext

- [Documentation](http://microsoft.github.io/agnext)
- [Examples](https://github.com/microsoft/agnext/tree/main/examples)


## Package layering

- `core` are the the foundational generic interfaces upon which all else is built. This module must not depend on any other module.
- `components` are the building blocks for creating single agents
- `application` are implementations of core components that are used to compose an application
- `chat` is the concrete implementation of multi-agent interactions. Most users will deal with this module.


## Development

### Setup

```sh
python -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

### Running tests

```sh
pytest
```

### Type checking

```sh
mypy
```

```sh
pyright
```

### Linting

```sh
ruff check
```

### Formatting

```sh
ruff format
```

### Build docs

```sh
pip install -e ".[docs]"

sphinx-build docs/src docs/build

# To view the docs:
python -m http.server -d docs/build
```
