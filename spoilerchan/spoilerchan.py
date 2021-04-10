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

bot = commands.Bot(command_prefix='s!')

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

@bot.listen('on_message')
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    warning = "Looks like a possible spoiler, {}. Please tag it if it is, or the <@&{}> will issue a warning.\n\nTag example: `[Higu Full]||Higurashi spoiler||`\n\nMessage Link: {}"
    
    async with bot.pool.acquire() as connection:
        spoiler_list = await connection.fetch('SELECT phrase, exceptions, spoiler_channels FROM spoilers WHERE guild_id=$1', message.guild.id)

        mod_role = await connection.fetchrow('SELECT mod_role FROM guilds WHERE id=$1', message.guild.id)

    for spoiler in spoiler_list:
        if re.match(spoiler['phrase'], message.content.lower()):
            if spoiler['spoiler_channels']:
                if message.channel.id in spoiler['spoiler_channels']:
                    return

            mod_role = mod_role['mod_role'] if mod_role else None
            message_text = message.content.lower()
                
            if spoiler['exceptions']:
                if any(exception in message_text for exception in spoiler['exceptions']):
                    return
                
            await message.channel.send(warning.format(message.author.mention,
                                                      mod_role,
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
@commands.has_permissions(administrator=True)
async def spoiler(context, action, *args):
    ''' Run this command for help '''
    if action:
        if action == 'add':
            if args:
                spoiler_phrase = args[0]
            
                async with bot.pool.acquire() as connection:
                    await connection.execute('''
                        INSERT INTO spoilers(guild_id, phrase) 
                        VALUES($1, $2)
                    ''', context.guild.id, spoiler_phrase)
        elif action == 'remove':
            if args:
                spoiler_phrase = args[0]
                
                async with bot.pool.acquire() as connection:
                    await connection.execute('''
                        DELETE FROM spoilers 
                        WHERE guild_id=$1 AND phrase=$2
                    ''', context.guild.id, spoiler_phrase)
        elif action == 'list':
            async with bot.pool.acquire() as connection:
                spoilers = await connection.fetch('''
                    SELECT phrase FROM spoilers 
                    WHERE guild_id=$1
                ''', context.guild.id)
                
                spoilers_list = [record['phrase'] for record in spoilers]
                
                await context.send("Spoilers: {}".format(spoilers_list))

@bot.command()
@commands.has_permissions(administrator=True)
async def addspoilerexceptions(context, spoiler_phrase, *args):
    ''' Adds a list of phrases that makes the bot disregard a specific spoiler phrase '''
    if spoiler_phrase:
        async with bot.pool.acquire() as connection:
            await connection.execute('''
                UPDATE spoilers
                SET exceptions=$3
                WHERE guild_id=$1 AND phrase=$2
            ''', context.guild.id, spoiler_phrase, args)

        await context.send("Added spoiler exceptions: {}.".format(args))

@bot.command()
@commands.has_permissions(administrator=True)
async def clearspoilerexceptions(context, spoiler_phrase):
    ''' Clears all exceptions from a specific phrase '''
    if spoiler_phrase:
        async with bot.pool.acquire() as connection:
            await connection.execute('''
                UPDATE spoilers
                SET exceptions=null
                WHERE guild_id=$1 AND phrase=$2
            ''', context.guild.id, spoiler_phrase)

        await context.send("Cleared all exceptions from {}.".format(spoiler_phrase))

@bot.command()
@commands.has_permissions(administrator=True)
async def addspoilerchannels(context, spoiler_phrase, *args):
    ''' Adds a list of spoiler channels to ignore a specific phrase in '''
    if spoiler_phrase:
        spoiler_channels = [int(channel_id) for channel_id in args]
        
        async with bot.pool.acquire() as connection:
            await connection.execute('''
                UPDATE spoilers
                SET spoiler_channels=$3
                WHERE guild_id=$1 AND phrase=$2
            ''', context.guild.id, spoiler_phrase, spoiler_channels)

        await context.send("Added spoiler channels: {}.".format(spoiler_channels))

@bot.command()
@commands.has_permissions(administrator=True)
async def clearspoilerchannels(context, spoiler_phrase):
    ''' Clears all spoiler channels to ignore a specific phrase '''
    if spoiler_phrase:
        async with bot.pool.acquire() as connection:
            await connection.execute('''
                UPDATE spoilers
                SET spoiler_channels=null
                WHERE guild_id=$1 AND phrase=$2
            ''', context.guild.id, spoiler_phrase)

        await context.send("Cleared all channels from {}.".format(spoiler_phrase))

@bot.command()
@commands.has_permissions(administrator=True)
async def setmodrole(context, mod_role):
    ''' Sets the server's moderator role (for pinging) '''
    async with bot.pool.acquire() as connection:
        await connection.execute("UPDATE guilds SET mod_role=$1 WHERE id=$2", int(mod_role), context.guild.id)

@bot.command()
async def info(context):
    ''' Displays bot info '''
    async with bot.pool.acquire() as connection:
        guild_ids = await connection.fetch("SELECT * from guilds")

    await context.send("Servers: {}".format(len(guild_ids)))

@bot.command()
async def tag(context, *, arg=None):
    ''' Spoiler tags an image or text '''
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
            spoiler_channels bigint[]
        )
    ''')
    
    try:
        await bot.start(DISCORD_TOKEN)
    except KeyboardInterrupt:
        await bot.pool.close()
        await bot.logout()

if __name__ == "__main__":
    bot.loop.run_until_complete(main())
