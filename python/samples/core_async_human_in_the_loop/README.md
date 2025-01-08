# Async Human-in-the-Loop Example

An example showing human-in-the-loop which waits for human input before making the tool call.

## Running the examples

### Prerequisites

First, you need a shell with AutoGen core and required dependencies installed.

```bash
pip install "autogen-core==0.4.0.dev13" "autogen-ext[openai,azure]==0.4.0.dev13"
```

### Model Configuration

The model configuration should defined in a `model_config.json` file.
Use `model_config_template.json` as a template.

### Running the example

```bash
python main.py
```