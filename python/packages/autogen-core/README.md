# AutoGen Core

- [Documentation](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/index.html)

## Package layering

- `base` are the the foundational generic interfaces upon which all else is built. This module must not depend on any other module.
- `application` are implementations of core components that are used to compose an application.
- `components` are the building blocks for creating agents.
