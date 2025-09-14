from discord import app_commands, DMChannel, Forbidden, Message, Interaction, Embed, Color, NotFound
from discord.ext import commands
from database_manager import DatabaseManager
import datetime
import asyncio
import smile


class BotCore(commands.Cog):
    def __init__(self, bot: commands.Bot, database: DatabaseManager):
        self.bot = bot
        print("BotCore Cog loaded.")
        self.db = database

    async def _send_await_pm_interaction(self, interaction: Interaction, message_content: str):
        author = interaction.user
        try:
            await author.send(message_content)
            if not isinstance(interaction.channel, DMChannel):
                await interaction.followup.send("Check your DMs!", ephemeral=True)

        except Forbidden:
            await interaction.followup.send("DM could not be sent. Please check your privacy settings.", ephemeral=True)
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
                await ctx.send("Check your DMs!", ephemeral=True)

        except Forbidden:
            await ctx.send("DM could not be sent. Please check your privacy settings.", ephemeral=True)
            return

        def check(message: Message) -> bool:
            return message.author == author and isinstance(message.channel, DMChannel)
        try:
            response_message = await self.bot.wait_for('message', timeout=20.0, check=check)
            return response_message

        except asyncio.TimeoutError:
            await author.send("Your request timed out.")

    @app_commands.command(name="create_lobby", description="Creates a new study lobby.")
    @app_commands.describe(
        name="The name of the lobby.",
        is_public="Should the lobby be public? (Default: False)"
    )
    async def create_lobby(self, interaction: Interaction, name: str,  is_public: bool = False):
        user_id = str(interaction.user.id)
        author = interaction.user
        await interaction.response.defer()

        user_has_free_slots = await self.db.user_has_free_slots(user_id)
        if not user_has_free_slots:
            await interaction.followup.send("You don't have room for a new lobby. Limit of 10 lobbies is reached.", ephemeral=True)
            return

        password = None
        if not is_public:
            password = await self._send_await_pm_interaction(interaction, "Please type your password here.")
            if password is None or password.content == "":
                await author.send("Password could not be empty!")
        else:
            await interaction.followup.send("Creating new lobby...", ephemeral=True)

        hash = ""
        hash = await self.db.create_lobby(user_id=user_id,
                                          name=name,
                                          is_public=is_public,
                                          password=password.content if password is not None else None
                                          )

        await interaction.followup.send(f"Lobby **{name}** was created.\n||Hash: **{hash}**||", ephemeral=True)

    @app_commands.command(name="start_chrono",  description="Starts the chronometer for your studies")
    @app_commands.describe(lobby_hash="Hash value of the lobby. Can be found under 'my lobbies'")
    async def start_chrono(self, interaction: Interaction, lobby_hash: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        dttm = interaction.created_at
        started_chrono = await self.db.start_chrono(lobby_hash, user_id, dttm)
        lobby_name = await self.db.get_lobby_name(lobby_hash)
        if started_chrono:
            await interaction.followup.send(f"Chronometer started for lobby: **{lobby_name}**", ephemeral=True)
        return

    @app_commands.command(name="stop_chrono",  description="Stops the chronometer for your studies")
    @app_commands.describe(lobby_hash="Hash value of the lobby. Can be found under 'my lobbies'")
    async def stop_chrono(self, interaction: Interaction, lobby_hash: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        dttm = interaction.created_at
        stopped_chrono, recorded_seconds = await self.db.stop_chrono(lobby_hash, user_id, dttm)
        lobby_name = await self.db.get_lobby_name(lobby_hash)
        if stopped_chrono:

            total_minutes, seconds = divmod(recorded_seconds, 60)
            hours, minutes = divmod(total_minutes, 60)
            await interaction.followup.send(f"Chronometer stopped for lobby: **{lobby_name}**.\n" +
                                            f"Studied for: **{hours}** Hours, **{minutes}** " +
                                            "Minutes and **{seconds}** Seconds. {smile.get_positive_comment()}", ephemeral=True)
        return

    @app_commands.command(name="my_lobbies",  description="Lists your lobbies")
    async def my_lobbies(self, interaction: Interaction):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        user_lobby_hashes = await self.db.get_user_lobbies(user_id)
        out_string = ""
        if user_lobby_hashes is None or user_lobby_hashes == []:
            await interaction.followup.send("You are not in any lobbies yet!")
            return

        for lobby_hash in user_lobby_hashes:
            print(lobby_hash)
            lobby_name = await self.db.get_lobby_name(lobby_hash)
            out_string += f":gear:Lobby Name: **{lobby_name}**\n:hammer:Lobby Hash: ||**{lobby_hash}**||\n\n"

        await interaction.followup.send(out_string, ephemeral=True)

    @app_commands.command(name="leaderboard",  description="Displays the leaderboard for the given lobby.")
    @app_commands.describe(lobby_hash="Hash value of the lobby. Can be found under 'my lobbies'")
    async def leaderboard(self, interaction: Interaction, lobby_hash: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        lobby_name = await self.db.get_lobby_name(lobby_hash)
        embed = Embed(
            title=f"🏆 {lobby_name}",
            description="Top students based on their total study time.",
            color=Color.gold()
        )

        leaderboard_text = ""
        users = await self.db.get_lobby_users(lobby_hash)
        users_list: list[tuple[str, int]] = []
        for user_dict in users:
            try:
                user_id = user_dict["user_id"]
                user = await self.bot.fetch_user(user_id)
                user_mention = user.mention
            except NotFound:
                user_mention = f"Unknown User ({user_id})"

            total_seconds = user_dict["total_seconds"]
            users_list.append((user_mention, total_seconds))

        users_list.sort(key=lambda x: x[1], reverse=True)
        for i, (mention, total_seconds) in enumerate(users_list, 1):
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)
            leaderboard_text += (
                f"**{i}.** {mention}\n"
                f"> **Hours:** {hours}, **Minutes:** {minutes}, **Seconds:** {seconds}\n\n"
            )
        if leaderboard_text:
            embed.description = leaderboard_text
        else:
            embed.description = "The leaderboard is empty!"
        await interaction.followup.send(embed=embed)

        return

    @app_commands.command(name="join",  description="Tries joining a certain lobby.")
    @app_commands.describe(lobby_hash="Hash value of the lobby")
    async def join(self, interaction: Interaction, lobby_hash: str):
        await interaction.response.defer()

        lobby_exists = await self.db.check_lobby_all(lobby_hash)
        if not lobby_exists:
            await interaction.followup.send(f"Could not join lobby with hash: **{lobby_hash}** . " +
                                            "Check if both the hash and password are correct", ephemeral=True)
            return

        # TODO: combine password check in one function
        is_public = await self.db.is_public(lobby_hash)
        password = None
        if not is_public:
            message = await self._send_await_pm_interaction(interaction, "Enter the password for the lobby you are trying to join.")
            if message is None:
                await interaction.followup.send(f"Could not join lobby with hash: **{lobby_hash}** . " +
                                                "Check if both the hash and password are correct", ephemeral=True)
                return
            password = message.content

        user_id = str(interaction.user.id)

        user_added = False
        user_added = await self.db.join_lobby(lobby_hash, user_id, password)

        lobby_name = await self.db.get_lobby_name(lobby_hash)
        if user_added:
            await interaction.followup.send(f"You have joined **{lobby_name}** !\n||Hash: {lobby_hash}||", ephemeral=True)
        else:
            await interaction.followup.send(f"Could not join lobby with hash: **{lobby_hash}** . " +
                                            "Check if both the hash and password are correct", ephemeral=True)

        return


async def setup(bot: commands.Bot):
    await bot.add_cog(BotCore(bot, bot.db))
