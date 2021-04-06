import discord
import io
import os
import re

from discord.ext import commands
from dotenv import load_dotenv

import psycopg2

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix='!')

spoiler_list = [
    {
        'phrase': re.compile(r'featherine'),
        'exceptions': [],
    },
    {
        'phrase': re.compile(r'amakusa'),
        'exceptions': [],
    },
    {
        'phrase': re.compile(r'lambda'),
        'exceptions': [],
    },
    {
        'phrase': re.compile(r'furudo'),
        'exceptions': [],
    },
    {
        'phrase': re.compile(r'\bange\b'),
        'exceptions': [],
    },
    {
        'phrase': re.compile(r'hanyuu'),
        'exceptions': [],
    },
    {
        'phrase': re.compile(r'\bl5\b'),
        'exceptions': [],
    },
    {
        'phrase': re.compile(r'\beua\b'),
        'exceptions': [],
    },
    {
        'phrase': re.compile(r'\bbern\b'),
        'exceptions': [
            'wine',
            'gif',
            'frederica',
            'frederika',
        ],
    },
    {
        'phrase': re.compile(r'\bbernkastel\b'),
        'exceptions': [
            'wine',
            'gif',
            'frederica',
            'frederika',
        ],
    },
]

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.listen('on_message')
async def on_message(message):
    if message.author == bot.user:
        return

    for spoiler in spoiler_list:
        if spoiler['phrase'].match(message.content.lower()):
            if not any(exception in message.content.lower() for exception in spoiler['exceptions']):
                warning = "Looks like a possible spoiler, {}. Please tag it if it is, or the <@&{}> will issue a warning.\n\nTag example: `[Higu Full]||Higurashi spoiler||`\n\nMessage Link: {}"
                await message.channel.send(warning.format(message.author.mention,
                                                          690986342385057884,
                                                          message.jump_url))

@bot.command()
async def spoiler(context, *, arg=None):
    if context.message.attachments:
        for attachment in context.message.attachments:
            fp = io.BytesIO()
            
            bytes_written = await attachment.save(fp)
            
            if bytes_written > 0:
                await context.send(content=context.author.mention + " sent: ",
                                   file=discord.File(fp, filename="SPOILER_" + attachment.filename, spoiler=True))
    else:
        if arg:
            await context.send("{} wrote: ||{}||".format(context.author.mention, arg))

    await context.message.delete()
    
bot.run(DISCORD_TOKEN)
