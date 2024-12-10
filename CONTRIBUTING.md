# Contributing

The project welcomes contributions from developers and organizations worldwide. Our goal is to foster a collaborative and inclusive community where diverse perspectives and expertise can drive innovation and enhance the project's capabilities. Whether you are an individual contributor or represent an organization, we invite you to join us in shaping the future of this project. Possible contributions include but not limited to:

- Pushing patches.
- Code review of pull requests.
- Documentation, examples and test cases.
- Readability improvement, e.g., improvement on docstr and comments.
- Community participation in [issues](https://github.com/microsoft/autogen/issues), [discussions](https://github.com/microsoft/autogen/discussions), and [twitter](https://twitter.com/pyautogen).
- Tutorials, blog posts, talks that promote the project.
- Sharing application scenarios and/or related research.

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

## Running CI checks locally

It is important to use `uv` when running CI checks locally as it ensures that the correct dependencies and versions are used.

Please follow the instructions [here](./python/README.md#setup) to get set up.

For common tasks that are helpful during development and run in CI, see [here](./python/README.md#common-tasks).

## Roadmap

We use GitHub issues and milestones to track our roadmap. You can view the upcoming milestones [here]([Roadmap Issues](https://aka.ms/autogen-roadmap).

## Versioning

The set of `autogen-*` packages are generally all versioned together. When a change is made to one package, all packages are updated to the same version. This is to ensure that all packages are in sync with each other.

We will update verion numbers according to the following rules:

- Increase minor version (0.X.0) upon breaking changes
- Increase patch version (0.0.X) upon new features or bug fixes

## Release process

1. Create a PR that updates the version numbers across the codebase ([example](https://github.com/microsoft/autogen/pull/4359))
    2. The docs CI will fail for the PR, but this is expected and will be resolved in the next step
2. After merging the PR, create and push a tag that corresponds to the new verion. For example, for `0.4.0.dev10`:
    - `git tag 0.4.0.dev10 && git push origin 0.4.0.dev10`
3. Restart the docs CI by finding the failed [job corresponding to the `push` event](https://github.com/microsoft/autogen/actions/workflows/docs.yml) and restarting all jobs
4. Run [this](https://github.com/microsoft/autogen/actions/workflows/single-python-package.yml) workflow for each of the packages that need to be released and get an approval for the release for it to run

## Triage process

To help ensure the health of the project and community the AutoGen committers have a weekly triage process to ensure that all issues and pull requests are reviewed and addressed in a timely manner. The following documents the responsibilites while on triage duty:

- Issues
  - Review all new issues - these will be tagged with [`needs-triage`](https://github.com/microsoft/autogen/issues?q=is%3Aissue%20state%3Aopen%20label%3Aneeds-triage).
  - Apply appropriate labels:
    - One of `proj-*` labels based on the project the issue is related to
    - `documentation`: related to documentation
    - `x-lang`: related to cross language functionality
    - `dotnet`: related to .NET
  - Add the issue to a relevant milestone if necessary
  - If you can resolve the issue or reply to the OP please do.
  - If you cannot resolve the issue, assign it to the appropriate person.
  - If awaiting a reply add the tag `awaiting-op-response` (this will be auto removed when the OP replies).
  - Bonus: there is a backlog of old issues that need to be reviewed - if you have time, review these as well and close or refresh as many as you can.
- PRs
  - The UX on GH flags all recently updated PRs. Draft PRs can be ignored, otherwise review all recently updated PRs.
  - If a PR is ready for review and you can provide one please go ahead. If you cant, please assign someone. You can quickly spin up a codespace with the PR to test it out.
  - If a PR is needing a reply from the op, please tag it `awaiting-op-response`.
  - If a PR is approved and passes CI, its ready to merge, please do so.
  - If it looks like there is a possibly transient CI failure, re-run failed jobs.
- Discussions
  - Look for recently updated discussions and reply as needed or find someone on the team to reply.
- Security
  - Look through any securty alerts and file issues or dismiss as needed.

## Becoming a Reviewer

There is currently no formal reviewer solicitation process. Current reviewers identify reviewers from active contributors.
