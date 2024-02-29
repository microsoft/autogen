# Contributing

## How to get a notebook displayed on the website

Ensure the first cell is markdown and before absolutely anything else include the following yaml within a comment.

```markdown
<!--
tags: ["code generation", "debugging"]
description: |
    Use conversable language learning model agents to solve tasks and provide automatic feedback through a comprehensive example of writing, executing, and debugging Python code to compare stock price changes.
-->
```

The `tags` field is a list of tags that will be used to categorize the notebook. The `description` field is a brief description of the notebook.

## Best practices for authoring notebooks

The following points are best practices for authoring notebooks to ensure consistency and ease of use for the website.

- The Colab button will be automatically generated on the website for all notebooks where it is missing. Going forward, it is recommended to not include the Colab button in the notebook itself.
- Ensure the header is a `h1` header, - `#`
- Don't put anything between the yaml and the header

### Consistency for installation and LLM config

You don't need to explain in depth how to install AutoGen. Unless there are specific instructions for the notebook just use the following markdown snippet:

``````
````{=mdx}
:::info Requirements
Install `pyautogen`:
```bash
pip install pyautogen
```

For more information, please refer to the [installation guide](/docs/installation/).
:::
````
``````

Or if extras are needed:

``````
````{=mdx}
:::info Requirements
Some extra dependencies are needed for this notebook, which can be installed via pip:

```bash
pip install pyautogen[retrievechat] flaml[automl]
```

For more information, please refer to the [installation guide](/docs/installation/).
:::
````
``````

When specifying the config list, to ensure consistency it is best to use approximately the following code:

```python
import autogen

config_list = autogen.config_list_from_json(
    env_or_file="OAI_CONFIG_LIST",
)
```

Then after the code cell where this is used, include the following markdown snippet:

``````
````{=mdx}
:::tip
Learn more about configuring LLMs for agents [here](/docs/llm_configuration).
:::
````
``````

## Testing

Notebooks can be tested by running:

```sh
python website/process_notebooks.py test
```

This will automatically scan for all notebooks in the notebook/ and website/ dirs.

To test a specific notebook pass its path:

```sh
python website/process_notebooks.py test notebook/agentchat_logging.ipynb
```

Options:
- `--timeout` - timeout for a single notebook
- `--exit-on-first-fail` - stop executing further notebooks after the first one fails

### Skip tests

If a notebook needs to be skipped then add to the notebook metadata:
```json
{
    "...": "...",
    "metadata": {
        "test_skip": "REASON"
    }
}
```

Note: Notebook metadata can be edited by opening the notebook in a text editor (Or "Open With..." -> "Text Editor" in VSCode)
