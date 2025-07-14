import discord
from discord.ext import commands
from discord.ui import Button, View

class Study(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='study')
    async def study(self, ctx):
        """Starts a study session with a button to join."""
        button = Button(label="Join Study Session", style=discord.ButtonStyle.green)
        
        async def button_callback(interaction):
            await interaction.response.send_message(f"{interaction.user.mention} has joined the study session!", ephemeral=True)

        button.callback = button_callback
        view = View()
        view.add_item(button)
        
        await ctx.send("Click the button below to join the study session!", view=view)

async def setup(bot):
    await bot.add_cog(Study(bot))
    print("Study cog loaded successfully.")