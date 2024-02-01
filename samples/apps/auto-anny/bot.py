import os
import discord
from discord.ext import commands

from agent_utils import solve_task

required_env_vars = [
    "OAI_CONFIG_LIST",
    "DISCORD_TOKEN",
    "GH_TOKEN",
]
for var in required_env_vars:
    if var not in os.environ:
        raise ValueError(f"{var} environment variable is not set.")

# read token from environment variable
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.command(description="Invoke Anny to solve a task.")
async def heyanny(ctx, task: str = None):
    if not task or task == "help":
        response = help_msg()
        await ctx.send(response)
        return

    task_map = {
        "ghstatus": ghstatus,
        "ghgrowth": ghgrowth,
        "ghunattended": ghunattended,
        "ghstudio": ghstudio,
    }

    if task in task_map:
        await ctx.send("Working on it...")
        response = await task_map[task](ctx)
        await ctx.send(response)
    else:
        response = "Invalid command! Please type /heyanny help for the list of commands."
        await ctx.send(response)


def help_msg():
    response = """
Hi this is Anny a AutoGen-powered, Discord bot. I can help you with the following tasks:
- ghstatus: Find the most recent issues and PRs from microsoft/autogen today.
- ghgrowth: Find the number of stars, forks, and indicators of growth of
 microsoft/autogen.
- ghunattended: Find the most issues and PRs from today from microsoft/autogen
that haven't received a response/comment.

You can invoke me by typing /heyanny <task>.
"""
    return response


async def ghstatus(ctx):
    # await ctx.send('Here is the summary of GitHub activity')
    message = ctx.message
    print(f"{message.guild} - {message.channel} - {message.author} - {message.content}")
    response = await solve_task(
        """
    Find the most recent issues and PRs from microsoft/autogen in last 24 hours.
    Separate issues and PRs.
    Final response should contains title, number, date/time, URLs of the issues and PRs.
    Markdown formatted response will make it look nice.
    Make sure date/time is in PST and readily readable.
    You can access github token from the environment variable called GH_TOKEN.
    """
    )
    return response


async def ghgrowth(ctx):
    # await ctx.send('Here is the summary of GitHub activity')
    message = ctx.message
    print(f"{message.guild} - {message.channel} - {message.author} - {message.content}")
    response = await solve_task(
        """
    Find the number of stars, forks, and indicators of growth of microsoft/autogen.
    Compare the stars of microsoft/autogen this week vs last week.
    Make sure date/time is in PST and readily readable.
    You can access github token from the environment variable called GH_TOKEN.
    """
    )
    return response


async def ghunattended(ctx):
    # await ctx.send('Here is the summary of GitHub activity')
    message = ctx.message
    print(f"{message.guild} - {message.channel} - {message.author} - {message.content}")
    response = await solve_task(
        """
    Find the issues *created* in the last 24 hours from microsoft/autogen that haven't
    received a response/comment. Modified issues don't count.
    Final response should contains title, number, date/time, URLs of the issues and PRs.
    Make sure date/time is in PST and readily readable.
    You can access github token from the environment variable called GH_TOKEN.
    """
    )
    return response


async def ghstudio(ctx):
    # await ctx.send('Here is the summary of GitHub activity')
    message = ctx.message
    print(f"{message.guild} - {message.channel} - {message.author} - {message.content}")
    response = await solve_task(
        """
    Find issues and PRs from microsoft/autogen that are related to the AutoGen Studio.
    The title or the body of the issue or PR should give you a hint whether its related.
    Summarize the top 5 common complaints or issues. Cite the issue/PR number and URL.
    Explain why you think this is a common issue in 2 sentences.
    You can access github token from the environment variable called GH_TOKEN.
    """
    )
    return response


bot.run(DISCORD_TOKEN)
