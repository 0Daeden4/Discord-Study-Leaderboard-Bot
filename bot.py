from discord.ext import commands
import discord
from database_manager import DatabaseManager


class Bot(commands.Bot):

    def __init__(self, database: DatabaseManager, testing_guild_id: int, testing: bool = False, **options) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="]", intents=intents, **options)
        self.db = database
        self._testing_guild_id = testing_guild_id
        self._testing = testing

    async def on_ready(self):
        print(f"Connected as: {self.user}")

    async def setup_hook(self):
        print("Running setup_hook...")
        print("Syncing command tree...")

        if self._testing:
            self.tree.copy_global_to(
                guild=discord.Object(id=self._testing_guild_id))
            await self.tree.sync(guild=discord.Object(id=self._testing_guild_id))
        else:
            await self.tree.sync()

        print("Command tree synced.")

    async def on_message(self, message):
        if message.author == self.user:
            return

        # await self.send_message_back(message, "Spam Test")

        await self.process_commands(message)

    async def send_message_back(self, message: discord.Message, content: str):
        try:
            await message.channel.send(content)
        except discord.Forbidden:
            print(
                f"Error: No permission to send messages in #{message.channel.name}")
