<div align="center">
  <img src="images/icon.png" alt="Repo Icon" width="100" height="100">
</div>

# AutoAnny

AutoAnny is a Discord bot built using AutoGen to help with AutoGen's Discord server.
Actually Anny can help with any OSS GitHub project (set `ANNY_GH_REPO` below).

## Features

- **`/heyanny help`**: Lists commands.
- **`/heyanny ghstatus`**: Summarizes GitHub activity.
- **`/heyanny ghgrowth`**: Shows GitHub repo growth indicators.
- **`/heyanny ghunattended`**: Lists unattended issues and PRs.

## Installation

1. Clone the AutoGen repository and `cd samples/apps/auto-anny`
2. Install dependencies: `pip install -r requirements.txt`
3. Export Discord token and GitHub API token,
    ```
    export OAI_CONFIG_LIST=your-autogen-config-list
    export DISCORD_TOKEN=your-bot-token
    export GH_TOKEN=your-gh-token
    export ANNY_GH_REPO=microsoft/autogen  # you may choose a different repo name
    ```
    To get a Discord token, you will need to set up your Discord bot using these [instructions](https://discordpy.readthedocs.io/en/stable/discord.html).
4. Start the bot: `python bot.py`

Note: By default Anny will log data to `autoanny.log`.


## Roadmap

- Enable access control
- Enable a richer set of commands
- Enrich agents with tool use


## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
