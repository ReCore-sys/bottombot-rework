import datetime
import json
import os
import random
import secrets
import sqlite3
import time

import async_cse
import discord
from discord.ext import commands

filepath = os.path.abspath(os.path.dirname(__file__))
token = secrets.token
client = discord.Client()
client = commands.Bot(command_prefix="$")
client.remove_command('help')


@client.event
async def on_ready():
    client.load_extension("cmd")
    print(  # noqa: W506,E261,E291
    """

     ______                            ______
    |  __  \       _   _              |  __  \       _
    | |__)  ) ___ | |_| |_  ___  ____ | |__)  ) ___ | |_
    |  __  ( / _ \|  _)  _)/ _ \|    \|  __  ( / _ \|  _)
    | |__)  ) |_| | |_| |_| |_| | | | | |__)  ) |_| | |__
    |______/ \___/ \___)___)___/|_|_|_|______/ \___/ \___)


    """)


@client.command()
async def reload(ctx):
    try:
        client.unload_extension("cmd")
    except:
        pass
    client.load_extension("cmd")
    await ctx.send("Reloaded")


client.run(token)
