# Chess Game Example

An example with two chess player agents that executes its own tools to demonstrate tool use and reflection on tool use.

## Running the example

### Prerequisites

First, you need a shell with AutoGen core and required dependencies installed.

```bash
pip install "autogen-core" "autogen-ext[openai,azure]" "chess"
```
### Model Configuration

The model configuration should defined in a `model_config.json` file.
Use `model_config_template.json` as a template.

### Running the example

```bash
python main.py
```