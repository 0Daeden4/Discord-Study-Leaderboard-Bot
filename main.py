import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import bot
import asyncio
from database_manager import DatabaseManager


async def main(token):
    print("Hello Discord!")
    db = DatabaseManager()
    await db.initialize()
    bot_instance: commands.Bot = bot.Bot(database=db)
    await bot_instance.load_extension("cogs.bot_core")

    await bot_instance.start(token)


if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    if TOKEN:
        asyncio.run(main(TOKEN))
    else:
        print("Error: DISCORD_TOKEN not found in .env file.")
