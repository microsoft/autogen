# Guidance for Maintainers

## General

- Be a member of the community and treat everyone as a member. Be inclusive.
- Help each other and encourage mutual help.
- Actively post and respond.
- Keep open communication.
- Identify good maintainer candidates from active contributors.

## Pull Requests

- For new PR, decide whether to close without review. If not, find the right reviewers. One source to refer to is the roles on Discord. Another consideration is to ask users who can benefit from the PR to review it.

- For old PR, check the blocker: reviewer or PR creator. Try to unblock. Get additional help when needed.
- When requesting changes, make sure you can check back in time because it blocks merging.
- Make sure all the checks are passed.
- For changes that require running OpenAI tests, make sure the OpenAI tests pass too. Running these tests requires approval.
- In general, suggest small PRs instead of a giant PR.
- For documentation change, request snapshot of the compiled website, or compile by yourself to verify the format.
- For new contributors who have not signed the contributing agreement, remind them to sign before reviewing.
- For multiple PRs which may have conflict, coordinate them to figure out the right order.
- Pay special attention to:
  - Breaking changes. Don’t make breaking changes unless necessary. Don’t merge to main until enough headsup is provided and a new release is ready.
  - Test coverage decrease.
  - Changes that may cause performance degradation. Do regression test when test suites are available.
  - Discourage **change to the core library** when there is an alternative.

## Issues and Discussions

- For new issues, write a reply, apply a label if relevant. Ask on discord when necessary. For roadmap issues, add to the roadmap project and encourage community discussion. Mention relevant experts when necessary.

- For old issues, provide an update or close. Ask on discord when necessary. Encourage PR creation when relevant.
- Use “good first issue” for easy fix suitable for first-time contributors.
- Use “task list” for issues that require multiple PRs.
- For discussions, create an issue when relevant. Discuss on discord when appropriate.
