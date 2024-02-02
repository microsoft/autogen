import os
import discord
from discord.ext import commands

from agent_utils import solve_task

required_env_vars = ["OAI_CONFIG_LIST", "DISCORD_TOKEN", "GH_TOKEN", "ANNY_GH_REPO"]
for var in required_env_vars:
    if var not in os.environ:
        raise ValueError(f"{var} environment variable is not set.")

# read token from environment variable
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
REPO = os.environ["ANNY_GH_REPO"]

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
    response = f"""
Hi this is Anny an AutoGen-powered Discord bot to help with `{REPO}`. I can help you with the following tasks:
- ghstatus: Find the most recent issues and PRs from today.
- ghgrowth: Find the number of stars, forks, and indicators of growth.
- ghunattended: Find the most issues and PRs from today from today that haven't received a response/comment.

You can invoke me by typing `/heyanny <task>`.
"""
    return response


async def ghstatus(ctx):
    # await ctx.send('Here is the summary of GitHub activity')
    message = ctx.message
    print(f"{message.guild} - {message.channel} - {message.author} - {message.content}")
    response = await solve_task(
        f"""
    Find the most recent issues and PRs from `{REPO}` in last 24 hours.
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
        f"""
    Find the number of stars, forks, and indicators of growth of `{REPO}`.
    Compare the stars of `{REPO}` this week vs last week.
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
        f"""
    Find the issues *created* in the last 24 hours from `{REPO}` that haven't
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
    # TODO: Generalize to feature name
    response = await solve_task(
        f"""
    Find issues and PRs from `{REPO}` that are related to the AutoGen Studio.
    The title or the body of the issue or PR should give you a hint whether its related.
    Summarize the top 5 common complaints or issues. Cite the issue/PR number and URL.
    Explain why you think this is a common issue in 2 sentences.
    You can access github token from the environment variable called GH_TOKEN.
    """
    )
    return response


bot.run(DISCORD_TOKEN)
