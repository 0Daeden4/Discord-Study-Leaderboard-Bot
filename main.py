import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import bot
import asyncio
from database_manager import DatabaseManager
import argparse


async def main(args):
    print("Hello Discord!")
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    if TOKEN:
        asyncio.run(main(TOKEN))
    else:
        print("Error: DISCORD_TOKEN not found in .env file.")

    is_testing = args.testing
    testing_guild_id = args.testing_guild_id

    if is_testing and testing_guild_id is None:
        raise ValueError(
            "You must pass in value for -tgid after enabling testing.")

    db = DatabaseManager()
    await db.initialize()
    bot_instance: commands.Bot = bot.Bot(
        database=db, testing_guild_id=testing_guild_id)
    await bot_instance.load_extension("cogs.bot_core")

    await bot_instance.start(TOKEN)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-t", "--testing", type=bool, default=False, help="Enable testing. Pass in the testing guild id with -tgid or" +
                            " --testing_guild_id", required=False)
    arg_parser.add_argument("-tgid", "--testing_guild_id", type=int,
                            help="Set the testing guild id for instant command updates.", required=False)
    arg_parser.parse_args()
