import os
import logging
import logging.handlers

import discord
from discord.ext import commands

from agent_utils import solve_task

logger = logging.getLogger("anny")
logger.setLevel(logging.INFO)
logging.getLogger("discord.http").setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename="autoanny.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
handler.setFormatter(formatter)
logger.addHandler(handler)

required_env_vars = ["OAI_CONFIG_LIST", "DISCORD_TOKEN", "GH_TOKEN", "ANNY_GH_REPO"]
for var in required_env_vars:
    if var not in os.environ:
        raise ValueError(f"{var} environment variable is not set.")

# read token from environment variable
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
REPO = os.environ["ANNY_GH_REPO"]
AUTHORIZED_USERS = os.environ.get("ANNY_AUTHORIZED_USERS", None)
if AUTHORIZED_USERS:
    AUTHORIZED_USERS = AUTHORIZED_USERS.split(",")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_message(message):
    logger.info({"message": message.content, "author": message.author, "id": message.id})
    if AUTHORIZED_USERS and str(message.author.name) not in AUTHORIZED_USERS:
        return
    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    logger.info(
        {
            "message": message.content,
            "author": message.author,
            "id": message.id,
            "reaction": reaction.emoji,
            "reactor": user,
        }
    )


@bot.event
async def on_ready():
    logger.info("Logged in", extra={"user": bot.user})


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
        "ghfaqs": ghfaqs,
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
- ghfaqs: Identify the top 3 frequently asked questions (FAQs) from the issues in the last week.

You can invoke me by typing `/heyanny <task>`.
"""
    return response


async def ghstatus(ctx):
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


async def ghfaqs(ctx):
    response = await solve_task(
        f"""
Based on the issues in the repo: `{REPO}` in the last week,
identify the top 3 frequently asked questions (FAQs).

When explaining a FAQ, cite links to the relevant issues.

Advice:
When analyzing and researching for the FAQs for the issues, consider the following:

1. Access the current date using python.
2. Then identify issues the that were created in the last week. Do not include PRs.
3. Restrict to the recent 50 issues.
4. Then, for each candidate print the following in a neat markdown format:
    - ID
    - Title
    - URL
    - Comments in the issue (The comments contain very valuable information)
      But only use the first 5 comments to avoid spamming the chat.

Then use the printed content to identify the top 3 FAQs.

You can access github token from the environment variable called GH_TOKEN.
"""
    )
    return response


bot.run(DISCORD_TOKEN, log_handler=None)
