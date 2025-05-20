# AutoGen Python 包

[![0.4 文档](https://img.shields.io/badge/Docs-0.4-blue)](https://microsoft.github.io/autogen/dev/)
[![PyPi autogen-core](https://img.shields.io/badge/PyPi-autogen--core-blue?logo=pypi)](https://pypi.org/project/autogen-core/) [![PyPi autogen-agentchat](https://img.shields.io/badge/PyPi-autogen--agentchat-blue?logo=pypi)](https://pypi.org/project/autogen-agentchat/) [![PyPi autogen-ext](https://img.shields.io/badge/PyPi-autogen--ext-blue?logo=pypi)](https://pypi.org/project/autogen-ext/)

本目录作为单个 `uv` 工作空间包含所有项目包。请查看 [`packages`](./packages/) 目录了解所有项目包。

## 从 0.2.x 版本迁移？

请参考[迁移指南](./migration_guide.md)了解如何将代码从 0.2.x 迁移到 0.4.x。

## 开发

**简而言之**，通过以下命令运行所有检查：

```sh
uv sync --all-extras
source .venv/bin/activate
poe check
```

### 设置

`uv` 是一个包管理器，可帮助创建必要的环境并安装运行 AutoGen 所需的包。

- [安装 `uv`](https://docs.astral.sh/uv/getting-started/installation/)。

**注意：** 为防止版本不兼容，应使用与 CI 中运行的 UV 相同的版本。可以通过查看 `setup-uv` 操作来检查 CI 中的版本，例如[这里](https://github.com/microsoft/autogen/blob/main/.github/workflows/checks.yml#L40)。

例如，要将版本更改为 `0.5.18`，请运行：
```sh
uv self update 0.5.18
```

### 虚拟环境

在开发过程中，您可能需要测试对任何包所做的更改。
为此，请创建一个虚拟环境，其中安装基于目录当前状态的 AutoGen 包。
在 Python 目录的根级别运行以下命令：

```sh
uv sync --all-extras
source .venv/bin/activate
```

- `uv sync --all-extras` 将在当前级别创建一个 `.venv` 目录，并安装来自当前目录的包以及任何其他依赖项。`all-extras` 标志添加可选依赖项。
- `source .venv/bin/activate` 激活虚拟环境。

### 常见任务

创建拉取请求 (PR) 前，请确保满足以下检查。您可以单独运行每个检查：

- 格式化：`poe format`
- 代码检查：`poe lint`
- 测试：`poe test`
- Mypy 类型检查：`poe mypy`
- Pyright 类型检查：`poe pyright`
- 构建文档：`poe --directory ./packages/autogen-core/ docs-build`
- 自动重建并提供文档：`poe --directory ./packages/autogen-core/ docs-serve`
- 检查 `python/samples` 中的示例：`poe samples-code-check`

或者，您可以使用以下命令运行所有检查：
- `poe check`

> [!注意]
> 这些命令需要在虚拟环境中运行。

### 同步依赖项

拉取新更改时，可能需要更新依赖项。
为此，首先确保您处于虚拟环境中，然后在 `python` 目录中运行：

```sh
uv sync --all-extras
```

这将更新虚拟环境中的依赖项。

### 创建新包

要创建类似于 `autogen-core` 或 `autogen-chat` 的新包，请使用以下命令：

```sh
uv sync --python 3.12
source .venv/bin/activate
cookiecutter ./templates/new-package/