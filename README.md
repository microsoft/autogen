# AutoGenNext

## Package layering

- `core` are the the foundational generic interfaces upon which all else is built. This module must not depend on any other module.
- `agent_components` are the building blocks for creating agents
- `core_components` are implementations of core components that are used to compose an application

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
