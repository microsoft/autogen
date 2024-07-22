# AGNext

- [Documentation](http://microsoft.github.io/agnext)
- [Examples](https://github.com/microsoft/agnext/tree/main/python/samples)

## Package layering

- `core` are the the foundational generic interfaces upon which all else is built. This module must not depend on any other module.
- `application` are implementations of core components that are used to compose an application.
- `components` are the building blocks for creating agents.

## Development

**TL;DR**, run all checks with:

```sh
hatch run check
```

### Setup

- [Install `hatch`](https://hatch.pypa.io/1.12/install/).

### Virtual environment

To get a shell with the package available (virtual environment),
in the current directory,
run:

```sh
hatch shell
```

### Common tasks

- Format: `hatch run check`
- Lint: `hatch run lint`
- Test: `hatch run pytest -n auto`
- Mypy: `hatch run mypy`
- Pyright: `hatch run pyright`
- Build docs: `hatch run docs:build`
- Auto rebuild+serve docs: `hatch run docs:serve`

> [!NOTE]
> These don't need to be run in a virtual environment, `hatch` will automatically manage it for you.
