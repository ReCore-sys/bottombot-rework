import datetime
import json
import os
import random
import secrets
import sqlite3
import string
import sys
import time
from secrets import *

import async_cse
import discord
import fuzzywuzzy
# from captcha.image import ImageCaptcha
from discord.ext import commands, tasks

filepath = os.path.abspath(os.path.dirname(__file__))
db = sqlite3.connect(f"{filepath}/database.db")
cursor = db.cursor()
# image = ImageCaptcha()
start, end = None, None


def getbal(ctx):
    id = ctx.author.id
    cursor.execute("select bal from users where id = ?", (id,))
    b = cursor.fetchone()
    return b[0]


def change(type, amount, action="+"):
    start = time.time()
    """Calculates change when buying/selling multiple stocks at once

     Parameters
     ----------
     type : str
     The tag of the targeted stock

     amount : int
     How many stocks to buy

     action : str
     Whether to increase or decrease the price

     Returns
     -------
     dprice: int
     The resulting cost/profit of the sold stocks"""
    cursor.execute("select price from coms where tag = ?", (type,))
    price = cursor.fetchone()[0]
    uprice = price
    if action in ["decrease", "down", "-"]:
        for x in range(amount):
            uprice /= 1.05
    else:
        for x in range(amount):
            uprice *= 1.05
    dprice = (price * (amount - 1)) + uprice
    diff = dprice - (price * amount)
    print("-" * 20)
    print(f"Original price: ${price * amount}\nNew Price: ${dprice}\nChange: ${diff}")
    print("-" * 20)
    dprice = round(dprice, 2)
    cursor.execute("""UPDATE coms SET price = price + ? WHERE tag = ?""", (diff, type))
    db.commit()
    end = time.time()
    print(f"Time taken: {end - start}")
    return dprice


def price(x):
    return f'{x:,}'


def account(ctx):
    global cursor
    cursor.execute("select id from users")
    ids = [x[0] for x in cursor.fetchall()]
    try:
        if ctx.message.author.id not in ids:
            cursor.execute(f'INSERT INTO users VALUES (?, 100, null, null)',
                           (ctx.author.id,))
            db.commit()
            print(f"Created account for id {ctx.author.id}")
    except:
        pass
    return True


def add(id, amount):
    cursor.execute("UPDATE users SET bal = bal + ? WHERE id = ?", (amount, id))
    db.commit()


opendms = {}
res1 = ""
res2 = ""
res3 = ""


class cmd(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.flux.start()

    try:
        # try create the database if it does not exist
        cursor.execute("""CREATE TABLE `users` (
        `id` INT NOT NULL,
        `bal` INT,
        `stock` INT,
        `ownedcomp` TEXT,
        `ownedbank` TEXT
        );""")
    except:
        # looks like it does exist
        pass
    try:
        cursor.execute("""CREATE TABLE "coms" (
        "tag"	TEXT,
        "owner"	INT,
        "worth"	INT,
        "price"	INT,
        "name"	TEXT
        );""")
        db.commit()
    except:
        pass

    @commands.check(account)
    @commands.command()
    async def test(self, ctx):
        await ctx.send("we back bitches!")

    @commands.check(account)
    @commands.command()
    async def bal(self, ctx, target: discord.Member = None):
        if target == None:
            user = ctx.message.author
            cursor.execute("select * from users where id = ?", (user.id,))
            val = cursor.fetchone()
        else:
            user = target
            cursor.execute("select * from users where id = ?", (user.id,))
            val = cursor.fetchone()
            if val == None:
                await ctx.send("That user does not have an account")
                return None
        embed = discord.Embed(title=f"{user}",
                              description="Account info",
                              color=random.randint(0, 0xFFFFFF))
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="ID", value=f"{user.id}", inline=True)
        embed.add_field(name="Balance",
                        value=f"${val[1]}",
                        inline=False)
        cursor.execute("select count from holds where owner = ?", (ctx.message.author.id,))
        results = [x[0] for x in cursor.fetchall()]
        totalowned = sum(results)
        embed.add_field(name="Owned stocks",
                        value=f"{totalowned}",
                        inline=False)
        await ctx.send(embed=embed)

    @ commands.check(account)
    @ commands.command()
    async def company(self, ctx, action=None, action2=None):
        global opendms
        bal = getbal(ctx)
        user = ctx.message.author
        if action == None:
            await ctx.send("Invalid message.contentut. Try using some arguments")
        else:
            if action == "start":
                if (bal >= 100000) or (ctx.author.id == admins):
                    channel = await user.create_dm()
                    opendms[user.id] = 0
                    await channel.send("What would you like to call your company?")
                else:
                    await ctx.send("You don't have enough money")
            elif action == "info":
                # //////////////////////////////////////////////////////////////////////////// #

                # FFS ADD FUZZY SEARCH TO THIS BIT, EVEN IF IT KILLS YOU

                # //////////////////////////////////////////////////////////////////////////// #
                if action2 == None:
                    cursor.execute("SELECT * from coms")
                    results = cursor.fetchall()
                    embed = discord.Embed(
                        title="Company details", description="Active companies")
                    for x in results:
                        embed.add_field(name=x[0], value=f"```Name: {x[4]} \nStock price: ${price(x[3])}```")
                    await ctx.send(embed=embed)
                else:
                    cursor.execute("SELECT * from coms where tag = ?", (action2.upper(),))
                    results = cursor.fetchone()
                    if results == None:
                        await ctx.send("That company does not exist")
                    else:
                        embed = discord.Embed(
                            title=results[4], description=f"({results[0]})")
                        embed.add_field(name="Stock price:", value=f"${price(results[3])}")
                        embed.add_field(name="Value:", value=f"${price(results[2])}")
                        await ctx.send(embed=embed)

    @ commands.check(account)
    @ commands.command()
    async def buy(self, ctx, type=None, count=1):
        cursor.execute("SELECT tag from coms")
        tags = cursor.fetchall()
        tags = [x[0] for x in tags]
        if type.isalpha() == False:
            await ctx.send("That is not a valid stock")
        elif type.upper() not in tags:
            await ctx.send("That is not a valid stock")
        else:
            cost = change(type.upper(), count)
            cursor.execute("SELECT bal FROM users WHERE id = ?", (ctx.message.author.id,))
            bal = cursor.fetchone()[0]
            if cost > bal:
                await ctx.send("You can't afford that")
            elif count > 5000:
                await ctx.send("Sorry, you can't buy that many at once")
            else:
                cursor.execute("SELECT count from holds where owner = ? AND tag = ?", (ctx.message.author.id, type.upper()))
                owned = cursor.fetchone()
                if owned == None:
                    cursor.execute("INSERT INTO holds VALUES (?, ?, ?)", (type.upper(), ctx.message.author.id, count))
                else:
                    cursor.execute("update holds set count = count + ? where owner = ?", (count, ctx.message.author.id,))
                add(ctx.message.author.id, cost)
                db.commit()
                await ctx.send(f"You have bought {count} stocks from {type.upper()} for ${price(cost)}")

    @ commands.check(account)
    @ commands.command()
    async def sell(self, ctx, type=None, count=1):
        cursor.execute("SELECT tag from coms")
        tags = cursor.fetchall()
        tags = [x[0] for x in tags]
        if type.isalpha() == False:
            await ctx.send("That is not a valid stock")
        elif type.upper() not in tags:
            await ctx.send("That is not a valid stock")
        else:
            cost = change(type.upper(), count)
            cursor.execute("SELECT count FROM holds WHERE owner = ? AND tag = ?", (ctx.message.author.id, type.upper()))
            owned = cursor.fetchone()[0]
            if owned < count:
                await ctx.send("You don't own that many stocks")
            elif count > 5000:
                await ctx.send("Sorry, you can't sell that many at once")
            else:
                cursor.execute("SELECT count from holds where owner = ? AND tag = ?", (ctx.message.author.id, type.upper()))
                owned = cursor.fetchone()
                if owned == None:
                    cursor.execute("INSERT INTO holds VALUES (?, ?, ?)", (type.upper(), ctx.message.author.id, count))
                else:
                    cursor.execute("update holds set count = count - ? where owner = ?", (count, ctx.message.author.id,))
                add(ctx.message.author.id, cost)
                db.commit()
                await ctx.send(f"You have sold {count} stocks to {type.upper()} for ${price(cost)}")

    @ commands.Cog.listener("on_message")
    # region company setup
    async def on_message(self, message):
        global opendms, res1, res2, res3
        if message.author.id != 758912539836547132:
            if message.author.id in opendms and isinstance(ctx.channel, discord.channel.DMChannel):
                stage = opendms[message.author.id]
                if stage == 0:
                    opendms[message.author.id] = opendms[message.author.id] + 1
                if stage == 1:
                    if message.content == "exit":
                        opendms.pop(message.author)
                    else:
                        res1 = message.content
                        if len(message.content) > 50:
                            await message.channel.send("Sorry, that name is too long")
                        else:
                            opendms[message.author.id] = opendms[message.author.id] + 1
                            await message.channel.send("What 3 letter tag would you like to identify it as?")

                if stage == 2:
                    if message.content == "exit":
                        opendms.pop(message.author)
                    else:
                        cursor.execute("SELECT tag FROM coms")
                        existing = [x[0] for x in cursor.fetchall()]
                        if message.content.isalpha() == False:
                            await message.channel.send("Sorry, that tag is not valid")
                        elif len(message.content) != 3:
                            await message.channel.send("Sorry, that tag has an invalid length")
                        elif message.content.upper() in existing:
                            await message.channel.send("Sorry, that tag is taken")
                        else:
                            res2 = message.content.upper()
                            opendms[message.author.id] = opendms[message.author.id] + 1
                            await message.channel.send("What do you want to set the current stock price to?")

                if stage == 3:
                    if message.content == "exit":
                        opendms.pop(message.author)
                    else:
                        res3 = message.content.strip()
                        if res3.isnumeric() == False:
                            await message.channel.send("Sorry, that value is not valid. Please only use an integer")
                        elif res3 < 1:
                            await message.channel.send("Haha, very funny")

                        elif int(res3) > 5000000:
                            await message.channel.send("Sorry, You can't set the starting price that high")
                        else:
                            opendms[message.author.id] = opendms[message.author.id] + 1
                            await message.channel.send("Does this look ok?")
                            await message.channel.send(f"Name: {res1}")
                            await message.channel.send(f"Tag: {res2}")
                            await message.channel.send(f"Starting price: ${int(res3)}")
                            await message.channel.send("Type 'confirm' to finish. Type anything else to start over")

                if stage == 4:
                    if message.content == "confirm":
                        add(message.author.id, -100000)
                        cursor.execute("select ownedcomp from users where id = ?", (message.author.id,))
                        owned = cursor.fetchone()[0]
                        if owned == None:
                            owned = [res2]
                        else:
                            owned = owned.split(",")
                            owned.append(res2)
                        owned = ",".join(owned)
                        cursor.execute("update users set ownedcomp = ? where id = ?", (owned, message.author.id,))
                        cursor.execute("select bal from users where id = ?", (message.author.id,))
                        b = cursor.fetchone()[0]
                        cursor.execute("""INSERT INTO 'coms' VALUES (?, ?, ?, ?, ?);""", (res2.strip(), message.author.id, b, int(res3), res1.strip(),))
                        db.commit()
                        await message.channel.send("Done!")
                        opendms.pop(message.author.id)
                    else:
                        await message.channel.send("Ok, cancelled")
                        opendms.pop(message.author.id)

    @ commands.command()
    async def joe(self, ctx):
        await ctx.send("https://tenor.com/view/dick-penis-dildo-forest-running-gif-16272085")
    word = ""
    diff = None

    @commands.command()
    async def sql(self, ctx, *, args):
        if ctx.message.author.id in admins:
            try:
                print(args)
                cursor.execute(args)
                res = cursor.fetchall()
                print(res)
                if res == []:
                    await ctx.send("Success")
                else:
                    await ctx.send(f"Success:\n```{res}```")
            except Exception as e:
                await ctx.send(f"Error:\n```{e}```")

    @commands.command()
    async def help(self, ctx, menu=None):
        with open(f"{filepath}/help.json") as d:
            result = json.load(d)
            result2 = {}
            for x in result:
                list = []
                for v in result[x]:
                    result2[v] = result[x][v]
            if menu not in result2:
                embed = discord.Embed(
                    title="Help", description="Welcome to the help menu. Do -help <command> to see what an individual command does", color=0x1e00ff)
                for x in result:
                    list = []
                    for v in result[x]:
                        list.append(v)
                    nicelist = (', '.join(list))
                    embed.add_field(name=x, value=f"`{nicelist}`", inline=True)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title=menu, description=result2[menu], color=0x1e00ff)
                await ctx.send(embed=embed)

    @ tasks.loop(seconds=60)
    async def flux(self):
        cursor.execute("select tag from coms")
        results = [x[0] for x in cursor.fetchall()]
        for x in results:
            increase = random.uniform(0.95, 1.05)
            cursor.execute("select price from coms where tag = ?", (x,))
            pr = cursor.fetchone()[0]
            cursor.execute("UPDATE coms SET price = ? WHERE tag = ?", (round(pr * increase, 2), x))
        db.commit()


def setup(bot: commands.Bot):
    bot.add_cog(cmd(bot))
