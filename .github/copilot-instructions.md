# AutoGen Multi-Agent AI Framework

AutoGen is a multi-language framework for creating AI agents that can act autonomously or work alongside humans. The project has separate Python and .NET implementations with their own development workflows.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Prerequisites and Environment Setup

**CRITICAL**: Install both .NET 8.0 and 9.0 for full compatibility:
- Install uv package manager: `python3 -m pip install uv` 
- Install .NET 9.0 SDK: `wget https://dot.net/v1/dotnet-install.sh && chmod +x dotnet-install.sh && ./dotnet-install.sh --channel 9.0`
- Install .NET 8.0 runtime: `./dotnet-install.sh --channel 8.0 --runtime dotnet && ./dotnet-install.sh --channel 8.0 --runtime aspnetcore`
- Update PATH: `export PATH="$HOME/.dotnet:$PATH"`

### Python Development Workflow

**Bootstrap and build Python environment:**
```bash
cd /home/runner/work/autogen/autogen/python
uv sync --all-extras  # NEVER CANCEL: Takes 2 minutes. Set timeout to 300+ seconds.
source .venv/bin/activate
```

**Validate Python development:**
```bash
# Quick validation (under 1 second each)
poe format  # Code formatting
poe lint    # Linting with ruff

# Type checking - NEVER CANCEL these commands
poe mypy     # Takes 6 minutes. Set timeout to 600+ seconds.
poe pyright  # Takes 41 seconds. Set timeout to 120+ seconds.

# Individual package testing (core package example)
poe --directory ./packages/autogen-core test  # Takes 10 seconds. Set timeout to 60+ seconds.

# Documentation - NEVER CANCEL
poe docs-build  # Takes 1 minute 16 seconds. Set timeout to 300+ seconds.
```

**CRITICAL TIMING EXPECTATIONS:**
- **NEVER CANCEL**: Python environment setup takes 2 minutes minimum
- **NEVER CANCEL**: mypy type checking takes 6 minutes 
- **NEVER CANCEL**: Documentation build takes 1+ minutes
- Format/lint tasks complete in under 1 second
- Individual package tests typically complete in 10-60 seconds

### .NET Development Workflow

**Bootstrap and build .NET environment:**
```bash
cd /home/runner/work/autogen/autogen/dotnet
export PATH="$HOME/.dotnet:$PATH"
dotnet restore  # NEVER CANCEL: Takes 53 seconds. Set timeout to 300+ seconds.
dotnet build --configuration Release  # NEVER CANCEL: Takes 53 seconds. Set timeout to 300+ seconds.
```

**Validate .NET development:**
```bash
# Unit tests - NEVER CANCEL
dotnet test --configuration Release --filter "Category=UnitV2" --no-build  # Takes 25 seconds. Set timeout to 120+ seconds.

# Format check (if build fails) 
dotnet format --verify-no-changes

# Run samples
cd samples/Hello
dotnet run
```

**CRITICAL TIMING EXPECTATIONS:**
- **NEVER CANCEL**: .NET restore takes 53 seconds minimum
- **NEVER CANCEL**: .NET build takes 53 seconds minimum  
- **NEVER CANCEL**: .NET unit tests take 25 seconds minimum
- All build and test commands require appropriate timeouts

### Complete Validation Workflow

**Run full check suite (Python):**
```bash
cd /home/runner/work/autogen/autogen/python
source .venv/bin/activate
poe check  # NEVER CANCEL: Runs all checks. Takes 7+ minutes total. Set timeout to 900+ seconds.
```

## Validation Scenarios

### Manual Validation Requirements
Always manually validate changes by running complete user scenarios after making modifications:

**Python validation scenarios:**
1. **Import test**: Verify core imports work:
   ```python
   from autogen_agentchat.agents import AssistantAgent
   from autogen_core import AgentRuntime
   from autogen_ext.models.openai import OpenAIChatCompletionClient
   ```

2. **AutoGen Studio test**: Verify web interface can start:
   ```bash
   autogenstudio ui --help  # Should show help without errors
   ```

3. **Documentation test**: Build and verify docs generate without errors:
   ```bash
   poe docs-build && ls docs/build/index.html
   ```

**.NET validation scenarios:**
1. **Sample execution**: Run Hello sample to verify runtime works:
   ```bash
   cd dotnet/samples/Hello && dotnet run --help
   ```

2. **Build validation**: Ensure all projects compile:
   ```bash
   dotnet build --configuration Release --no-restore
   ```

3. **Test execution**: Run unit tests to verify functionality:
   ```bash
   dotnet test --filter "Category=UnitV2" --configuration Release --no-build
   ```

## Common Issues and Workarounds

### Network-Related Issues
- **Python tests may fail** with network errors (tiktoken downloads, Playwright browser downloads) in sandboxed environments - this is expected
- **Documentation intersphinx warnings** due to inability to reach external documentation sites - this is expected
- **Individual package tests work better** than full test suite in network-restricted environments

### .NET Runtime Issues  
- **Requires both .NET 8.0 and 9.0**: Build uses 9.0 SDK but tests need 8.0 runtime
- **Global.json specifies 9.0.100**: Must install exact .NET 9.0 version or later
- **Path configuration critical**: Ensure `$HOME/.dotnet` is in PATH before system .NET

### Python Package Issues
- **Use uv exclusively**: Do not use pip/conda for dependency management
- **Virtual environment required**: Always activate `.venv` before running commands
- **Package workspace structure**: Project uses uv workspace with multiple packages

## Timing Reference

### Python Commands
| Command | Expected Time | Timeout | Notes |
|---------|---------------|---------|-------|
| `uv sync --all-extras` | 2 minutes | 300+ seconds | NEVER CANCEL |
| `poe mypy` | 6 minutes | 600+ seconds | NEVER CANCEL |
| `poe pyright` | 41 seconds | 120+ seconds | NEVER CANCEL |
| `poe docs-build` | 1 min 16 sec | 300+ seconds | NEVER CANCEL |
| `poe format` | <1 second | 30 seconds | Quick |
| `poe lint` | <1 second | 30 seconds | Quick |
| Individual package test | 10 seconds | 60+ seconds | May have network failures |

### .NET Commands  
| Command | Expected Time | Timeout | Notes |
|---------|---------------|---------|-------|
| `dotnet restore` | 53 seconds | 300+ seconds | NEVER CANCEL |
| `dotnet build --configuration Release` | 53 seconds | 300+ seconds | NEVER CANCEL |
| `dotnet test --filter "Category=UnitV2"` | 25 seconds | 120+ seconds | NEVER CANCEL |
| `dotnet format --verify-no-changes` | 5-10 seconds | 60 seconds | Quick validation |

## Repository Structure

### Python Packages (`python/packages/`)
- `autogen-core`: Core agent runtime, model interfaces, and base components
- `autogen-agentchat`: High-level multi-agent conversation APIs  
- `autogen-ext`: Extensions for specific model providers and tools
- `autogen-studio`: Web-based IDE for agent workflows
- `agbench`: Benchmarking suite for agent performance
- `magentic-one-cli`: Multi-agent team CLI application

### .NET Projects (`dotnet/src/`)
- `AutoGen`: Legacy 0.2-style .NET packages (being deprecated)
- `Microsoft.AutoGen.*`: New event-driven .NET packages
- `AutoGen.Core`: Core .NET agent functionality
- Multiple provider packages: OpenAI, Anthropic, Ollama, etc.

### Key Configuration Files
- `python/pyproject.toml`: Python workspace and tool configuration
- `dotnet/global.json`: .NET SDK version requirements  
- `dotnet/AutoGen.sln`: .NET solution file
- `python/uv.lock`: Locked Python dependencies

## Development Best Practices

### Before Committing Changes
**ALWAYS run these validation steps:**

**Python:**
```bash
cd python && source .venv/bin/activate
poe format    # Fix formatting
poe lint      # Check code quality  
poe mypy      # Type checking (6 minutes)
poe docs-build # Verify docs build (1+ minutes)
```

**.NET:**
```bash  
cd dotnet && export PATH="$HOME/.dotnet:$PATH"
dotnet format --verify-no-changes  # Check formatting
dotnet build --configuration Release --no-restore  # Build (53 seconds)
dotnet test --configuration Release --filter "Category=UnitV2" --no-build  # Test (25 seconds)
```

### Key Directories Reference
```
autogen/
├── python/                    # Python implementation
│   ├── packages/             # Individual Python packages
│   ├── docs/                 # Sphinx documentation
│   ├── samples/              # Example code
│   └── pyproject.toml        # Workspace configuration
├── dotnet/                   # .NET implementation  
│   ├── src/                  # Source projects
│   ├── test/                 # Test projects
│   ├── samples/              # Sample applications
│   └── AutoGen.sln          # Solution file
├── .github/workflows/        # CI/CD pipelines
└── docs/                     # Additional documentation
```

This framework supports creating both simple single-agent applications and complex multi-agent workflows with support for various LLM providers, tools, and deployment patterns.