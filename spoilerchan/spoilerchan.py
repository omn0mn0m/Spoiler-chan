import discord
import os

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix='!')

spoiler_list = [
    'featherine',
    'bernkastel',
]

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if any(spoiler_word in message.content.lower() for spoiler_word in spoiler_list):
        await message.channel.send('Looks like a spoiler...')
        return

    await bot.process_commands(message)

@bot.command()
async def spoiler(context, arg):
    await context.message.delete()
    await context.send("||{}||".format(arg))
    
bot.run(DISCORD_TOKEN)
