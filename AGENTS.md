# Agent Instructions

Monorepo with two independent toolchains: Python in `python/`, .NET in `dotnet/`.
Run all commands from the relevant directory, not the repo root.

## Package Managers
- Python: **uv** only (`uv sync --all-extras`). Never use pip or conda.
- .NET: **dotnet** SDK. A JS frontend under `python/packages/autogen-studio/frontend` uses **yarn**.

## Python (`python/`, uv workspace + `poe` task runner)
Activate the env first: `uv sync --all-extras && source .venv/bin/activate`.

| Task | Command |
|------|---------|
| All checks | `poe check` |
| Format / Lint | `poe format` / `poe lint` |
| Types | `poe mypy` / `poe pyright` |
| Test one package | `poe --directory ./packages/<pkg> test` |
| Test all | `poe test` |
| Docs build / check examples | `poe docs-build` / `poe docs-check-examples` |
| New package | `cookiecutter ./templates/new-package/` |

## .NET (`dotnet/`, solution `AutoGen.sln`)
Requires **both .NET 8.0 and 9.0** installed (SDK per `global.json`; tests need the 8.0 runtime).

| Task | Command |
|------|---------|
| Restore / Build | `dotnet restore` / `dotnet build --configuration Release` |
| Test | `dotnet test --configuration Release --filter "Category=UnitV2" --no-build` |
| Format check | `dotnet format --verify-no-changes` |
| Pack NuGet | `dotnet pack --configuration Release` |

## External References
| Need | File |
|------|------|
| Full agent/dev guide (timings, gotchas) | `.github/copilot-instructions.md` |
| Python setup, tasks, docstring & test rules | `python/README.md` |
| .NET usage / install | `dotnet/README.md`, `dotnet/website/articles/Installation.md` |
| .NET packaging | `dotnet/PACKAGING.md` |
| Contributing, versioning, release, triage | `CONTRIBUTING.md` |
| Distributed/event-driven architecture spec | `docs/design/` (`01`–`05`) |
| Security reporting | `SECURITY.md` |
| PR template | `.github/PULL_REQUEST_TEMPLATE.md` |

## Key Conventions
- `autogen-*` packages are versioned together: bump minor (0.X.0) for breaking changes, patch (0.0.X) for features/fixes.
- Python docstrings: Google style + Sphinx RST; `.. code-block:: python` examples are checked by `poe docs-check-examples`.
- Tests use `pytest` with fixtures/mocks; use `autogen_ext.models.replay.ReplayChatCompletionClient` instead of real model calls; guard API-dependent tests with `pytest.mark.skipif`.
- .NET has legacy `AutoGen.*` (0.2, being deprecated) and new event-driven `Microsoft.AutoGen.*`; prefer the new packages.
- PRs must fill the template (why / related issue) and check its boxes: include doc changes, add tests, ensure CI passes. First-time contributors sign the Microsoft CLA.
- Do not report security issues via public GitHub issues; follow `SECURITY.md`.

## Commit Attribution
AI-generated commits MUST include:
```
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
