import discord
import io
import os
import re

import asyncio
import asyncpg

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.listen('on_message')
async def on_message(message):
    if message.author == bot.user:
        return

    warning = "Looks like a possible spoiler, {}. Please tag it if it is, or the <@&{}> will issue a warning.\n\nTag example: `[Higu Full]||Higurashi spoiler||`\n\nMessage Link: {}"

    async with bot.pool.acquire() as connection:
        spoiler_list = await connection.fetch('SELECT phrase, exceptions, spoiler_channels FROM spoilers WHERE guild_id=$1', message.guild.id)

        mod_role = await connection.fetchrow('SELECT mod_role FROM guilds WHERE id=$1', message.guild.id)

    for spoiler in spoiler_list:
        if re.match(spoiler['phrase'], message.content.lower()):
            if spoiler['exceptions']:
                if not any(exception in message.content.lower() for exception in spoiler['exceptions']):
                    await message.channel.send(warning.format(message.author.mention,
                                                              mod_role,
                                                              message.jump_url))
            else:
                await message.channel.send(warning.format(message.author.mention,
                                                              mod_role['mod_role'],
                                                              message.jump_url))

@bot.event
async def on_guild_join(guild):
    async with bot.pool.acquire() as connection:
        await connection.execute("INSERT INTO guilds(id) VALUES($1)", guild.id)

@bot.event
async def on_guild_remove(guild):
    async with bot.pool.acquire() as connection:
        await connection.execute("DELETE FROM guilds WHERE id=$1", guild.id)

@bot.command()
async def addspoiler(context, spoiler_phrase):
    ''' !addspoiler spoiler_phrase '''
    if spoiler_phrase:
        async with bot.pool.acquire() as connection:
            await connection.execute('''
                 INSERT INTO spoilers(guild_id, phrase) VALUES($1, $2)
            ''', context.guild.id, spoiler_phrase)

@bot.command()
async def removespoiler(context, spoiler_phrase):
    if spoiler_phrase:
        async with bot.pool.acquire() as connection:
            await connection.execute("DELETE FROM spoilers WHERE guild_id=$1 AND phrase=$2", context.guild.id, spoiler_phrase)

@bot.command()
async def listspoilers(context):
    async with bot.pool.acquire() as connection:
        spoilers = await connection.fetch('SELECT phrase FROM spoilers WHERE guild_id=$1', context.guild.id)

        spoilers_string = ''
        
        for record in spoilers:
            spoilers_string += record['phrase'] + ', '
        
        await context.send("Spoilers: {}".format(spoilers_string))

@bot.command()
async def addspoilerexception(context, *args):
    ''' !addspoilerexception exception1 exception2 '''
    pass

@bot.command()
async def addspoilerchannel(context, *args):
    ''' !addspoilerchannel channel1 channel2 '''
    pass

@bot.command()
async def setmodrole(context, mod_role):
    async with bot.pool.acquire() as connection:
        await connection.execute("UPDATE guilds SET mod_role=$1 WHERE id=$2", int(mod_role), context.guild.id)

@bot.command()
async def servers(context):
    async with bot.pool.acquire() as connection:
        guild_ids = await connection.fetch("SELECT * from guilds")

    if guild_ids:
        await context.send("Servers: {}".format(guild_ids))
    else:
        await context.send("Servers: None")

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

async def main():
    credentials = {
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "database": os.getenv("POSTGRES_DATABASE", "postgres"),
        "host": os.getenv("POSTGRES_HOST", "db")
    }
    
    bot.pool = await asyncpg.create_pool(**credentials)

    await bot.pool.execute('''
        CREATE TABLE IF NOT EXISTS guilds(
            id bigint PRIMARY KEY,
            mod_role bigint
        )
    ''')
    await bot.pool.execute('''
        CREATE TABLE IF NOT EXISTS spoilers(
            id SERIAL PRIMARY KEY,
            guild_id bigint,
            phrase text,
            exceptions text[],
            spoiler_channels bigint
        )
    ''')
    
    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        await bot.pool.close()
        await bot.logout()

if __name__ == "__main__":
    bot.loop.run_until_complete(main())
