# Creating your own extension

With the new package structure in 0.4, it is easier than ever to create and publish your own extension to the AutoGen ecosystem. This page details some best practices so that your extension package  integrates well with the AutoGen ecosystem.

## Best practices

### Naming

There is no requirement about naming. But prefixing the package name with `autogen-` makes it easier to find.

### Common interfaces

Whenever possible, extensions should implement the provided interfaces from the `autogen_core` package. This will allow for a more consistent experience for users.

#### Dependency on AutoGen

To ensure that the extension works with the version of AutoGen that it was designed for, it is recommended to specify the version of AutoGen the dependency section of the `pyproject.toml` with adequate constraints.

```toml
[project]
# ...
dependencies = [
    "autogen-core>=0.4,<0.5"
]
```

### Usage of typing

AutoGen embraces the use of type hints to provide a better development experience. Extensions should use type hints whenever possible.

## Discovery

To make it easier for users to find your extension, sample, service or package, you can [add the topic](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics) [`autogen`](https://github.com/topics/autogen) to the GitHub repo.

More specific topics are also available:

- [`autogen-extension`](https://github.com/topics/autogen-extension) for extensions
- [`autogen-sample`](https://github.com/topics/autogen-sample) for samples

## Changes from 0.2

In AutoGen 0.2 it was common to merge 3rd party extensions and examples into the main repo. We are super appreciative of all of the users who have contributed to the ecosystem notebooks, modules and pages in 0.2. However, in general we are moving away from this model to allow for more flexibility and to reduce maintenance burden.

There is the `autogen-ext` package for 1st party supported extensions, but we want to be selective to manage maintenance load. If you would like to see if your extension makes sense to add into `autogen-ext`, please open an issue and let's discuss. Otherwise, we encourage you to publish your extension as a separate package and follow the guidance under [discovery](#discovery) to make it easy for users to find.
