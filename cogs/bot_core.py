from discord import app_commands, DMChannel, Forbidden, Message, Interaction
from discord.ext import commands
from database_manager import DatabaseManager
import asyncio


class BotCore(commands.Cog):
    def __init__(self, bot: commands.Bot, database: DatabaseManager):
        self.bot = bot
        print("BotCore Cog loaded.")
        self.db = database

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"Pong! Latency: {round(self.bot.latency * 1000)}ms")

    async def _send_await_pm_interaction(self, interaction: Interaction, message_content: str):
        author = interaction.user

        try:
            await author.send(message_content)

            if not isinstance(interaction.channel, DMChannel):
                await interaction.followup.send("Check your DMs!", ephemeral=True)

        except Forbidden:
            await interaction.followup.send("DM could not be sent. Please check your privacy settings.")
            return

        def check(message: Message) -> bool:
            return message.author == author and isinstance(message.channel, DMChannel)
        try:
            response_message = await self.bot.wait_for('message', timeout=20.0, check=check)
            return response_message

        except asyncio.TimeoutError:
            await author.send("Your request timed out.")

    async def _send_await_pm_ctx(self, ctx: commands.Context, message_content: str):
        author = ctx.author

        try:
            await author.send(message_content)

            if not isinstance(ctx.channel, DMChannel):
                await ctx.send("Check your DMs!")

        except Forbidden:
            await ctx.send("DM could not be sent. Please check your privacy settings.")
            return

        def check(message: Message) -> bool:
            return message.author == author and isinstance(message.channel, DMChannel)
        try:
            response_message = await self.bot.wait_for('message', timeout=20.0, check=check)
            return response_message

        except asyncio.TimeoutError:
            await author.send("Your request timed out.")

    # "1- A lobby cannot be public and encrypted at the same time\n\
    # 2- A lobby can be private but not encrypted\n\
    # 3- You need to pass in a strong password for both a private and encrypted lobby\n\
    # 4- Don't forget the hash of your lobby!")
    @app_commands.command(name="create_lobby", description="Creates a new study lobby.")
    @app_commands.describe(
        name="The name of the lobby.",
        is_encrypted="Should the lobby be encrypted? (Default: False)",
        is_public="Should the lobby be public? (Default: False)"
    )
    async def create_lobby(self, interaction: Interaction, name: str, is_encrypted: bool = False, is_public: bool = False):
        user_id = str(interaction.user.id)
        author = interaction.user
        print("Test")
        await interaction.response.defer()

        password = None
        if is_encrypted or not is_public:
            password = await self._send_await_pm_interaction(interaction, "Please type your password here.")
            if password is None or password.content == "":
                await author.send("Password could not be empty!")
        else:
            await interaction.followup.send("Creating new lobby...")

        hash = ""
        try:
            hash = await self.db.create_lobby(user_id=user_id,
                                              name=name,
                                              is_encrypted=is_encrypted,
                                              is_public=is_public,
                                              password=password.content if password is not None else None
                                              )
        except Exception as e:
            print(f"DEBUG: ERROR! An exception occurred: {e}")
            await interaction.followup.send("HAHAHAHAHAH EXCEPTION!")

        await interaction.followup.send(f"Lobby '{name}' was created... Don't forget the value below!\nLeaderboard hash: {hash}")


async def setup(bot: commands.Bot):
    await bot.add_cog(BotCore(bot, bot.db))
