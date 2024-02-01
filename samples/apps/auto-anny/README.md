<div align="center">
  <img src="images/icon.png" alt="Repo Icon" width="100" height="100">
</div>

# AutoAnny

AutoAnny is a Discord bot built using AutoGen to help with AutoGen's Discord server.

## Features

- **`/heyanny help`**: Lists commands.
- **`/heyanny ghstatus`**: Summarizes GitHub activity.
- **`/heyanny ghgrowth`**: Shows GitHub repo growth indicators.
- **`/heyanny ghunattended`**: Lists unattended issues and PRs.

## Installation

1. Clone this repository: `git clone https://github.com/gagb/AutoAnny.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Export Discord token and GitHub API token,
    ```
    export OAI_CONFIG_LIST=your-autogen-config-list
    export DISCORD_TOKEN=your-bot-token
    export GH_TOKEN=your-gh-token
    ```
4. Start the bot: `python bot.py`

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
