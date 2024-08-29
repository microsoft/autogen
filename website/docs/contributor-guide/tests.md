# Tests

Tests are automatically run via GitHub actions. There are two workflows:

1. [build.yml](https://github.com/microsoft/autogen/blob/main/.github/workflows/build.yml)
1. [openai.yml](https://github.com/microsoft/autogen/blob/main/.github/workflows/openai.yml)

The first workflow is required to pass for all PRs (and it doesn't do any OpenAI calls). The second workflow is required for changes that affect the OpenAI tests (and does actually call LLM). The second workflow requires approval to run. When writing tests that require OpenAI calls, please use [`pytest.mark.skipif`](https://github.com/microsoft/autogen/blob/b1adac515931bf236ac59224269eeec683a162ba/test/oai/test_client.py#L19) to make them run in only when `openai` package is installed. If additional dependency for this test is required, install the dependency in the corresponding python version in [openai.yml](https://github.com/microsoft/autogen/blob/main/.github/workflows/openai.yml).

Make sure all tests pass, this is required for [build.yml](https://github.com/microsoft/autogen/blob/main/.github/workflows/build.yml) checks to pass

## Running tests locally

To run tests, install the [test] option:

```bash
pip install -e."[test]"
```

Then you can run the tests from the `test` folder using the following command:

```bash
pytest test
```

Tests for the `autogen.agentchat.contrib` module may be skipped automatically if the
required dependencies are not installed. Please consult the documentation for
each contrib module to see what dependencies are required.

See [here](https://github.com/microsoft/autogen/blob/main/notebook/contributing.md#testing) for how to run notebook tests.

## Skip flags for tests

- `--skip-openai` for skipping tests that require access to OpenAI services.
- `--skip-docker` for skipping tests that explicitly use docker
- `--skip-redis` for skipping tests that require a Redis server

For example, the following command will skip tests that require access to
OpenAI and docker services:

```bash
pytest test --skip-openai --skip-docker
```

## Coverage

Any code you commit should not decrease coverage. To ensure your code maintains or increases coverage, use the following commands after installing the required test dependencies:

```bash
pip install -e ."[test]"

pytest test --cov-report=html
```

Pytest generated a code coverage report and created a htmlcov directory containing an index.html file and other related files. Open index.html in any web browser to visualize and navigate through the coverage data interactively. This interactive visualization allows you to identify uncovered lines and review coverage statistics for individual files.
