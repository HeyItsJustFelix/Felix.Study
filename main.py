import discord
from discord.ext import commands
import os
from key import key

class aclient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.synced = False

    async def on_ready(self):
        print(f"We are ready for study services! Logged in as {self.user}")

    async def setup_hook(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")

        if not self.synced:
            await self.tree.sync()
            self.synced = True
            print("Synced the commands with Discord.")

bot = aclient()

bot.run(key)  # Use the key from key.py to run the bot