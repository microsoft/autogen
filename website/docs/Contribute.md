# Contributing

This project welcomes (and encourages) all forms of contributions, including but not limited to:

-  Pushing patches.
-  Code review of pull requests.
-  Documentation, examples and test cases.
-  Readability improvement, e.g., improvement on docstr and comments.
-  Community participation in [issues](https://github.com/microsoft/FLAML/issues), [discussions](https://github.com/microsoft/FLAML/discussions), and [gitter](https://gitter.im/FLAMLer/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge).
-  Tutorials, blog posts, talks that promote the project.
-  Sharing application scenarios and/or related research.

You can take a look at the [Roadmap for Upcoming Features](https://github.com/microsoft/FLAML/wiki/Roadmap-for-Upcoming-Features) to identify potential things to work on.

Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit <https://cla.opensource.microsoft.com>.

If you are new to GitHub [here](https://help.github.com/categories/collaborating-with-issues-and-pull-requests/) is a detailed help source on getting involved with development on GitHub.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Becoming a Reviewer

There is currently no formal reviewer solicitation process. Current reviewers identify reviewers from active contributors. If you are willing to become a reviewer, you are welcome to let us know on gitter.

## Developing

### Setup

```bash
git clone https://github.com/microsoft/FLAML.git
pip install -e FLAML[test,notebook]
```

### Docker

We provide a simple [Dockerfile](https://github.com/microsoft/FLAML/blob/main/Dockerfile).

```bash
docker build git://github.com/microsoft/FLAML -t flaml-dev
docker run -it flaml-dev
```

### Develop in Remote Container

If you use vscode, you can open the FLAML folder in a [Container](https://code.visualstudio.com/docs/remote/containers).
We have provided the configuration in [devcontainer](https://github.com/microsoft/FLAML/blob/main/.devcontainer).

### Pre-commit

Run `pre-commit install` to install pre-commit into your git hooks. Before you commit, run
`pre-commit run` to check if you meet the pre-commit requirements. If you use Windows (without WSL) and can't commit after installing pre-commit, you can run `pre-commit uninstall` to uninstall the hook. In WSL or Linux this is supposed to work.

### Coverage

Any code you commit should not decrease coverage. To run all unit tests:

```bash
coverage run -m pytest test
```

Then you can see the coverage report by
`coverage report -m` or `coverage html`.
If all the tests are passed, please also test run [notebook/automl_classification](https://github.com/microsoft/FLAML/blob/main/notebook/automl_classification.ipynb) to make sure your commit does not break the notebook example.

### Documentation

To build and test documentation locally, install [Node.js](https://nodejs.org/en/download/). For example,

```bash
nvm install --lts
```

Then:

```console
npm install --global yarn  # skip if you use the dev container we provided
pip install pydoc-markdown==4.5.0  # skip if you use the dev container we provided
cd website
yarn install --frozen-lockfile --ignore-engines
pydoc-markdown
yarn start
```

The last command starts a local development server and opens up a browser window.
Most changes are reflected live without having to restart the server.
