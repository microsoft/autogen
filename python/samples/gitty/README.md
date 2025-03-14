# gitty (Warning: WIP)

This is an AutoGen powered CLI that generates draft replies for issues and pull requests
to reduce maintenance overhead for open source projects.

Simple installation and CLI:

   ```bash
   gitty --repo microsoft/autogen issue 5212
   ```

*Important*: Install the dependencies and set OpenAI API key:

   ```bash
   uv sync --all-extras
   source .venv/bin/activate
   export OPENAI_API_KEY=sk-....
   ```
