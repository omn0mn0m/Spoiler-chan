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
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")

bot = commands.Bot(command_prefix=('s!', 'S!'))

@bot.event
async def on_ready():
    async with bot.pool.acquire() as connection:
        for guild in bot.guilds:
            await connection.execute("INSERT INTO guilds(id) VALUES($1) on conflict (id) do nothing", guild.id)

    print('We have logged in as {0.user}'.format(bot))

@bot.listen('on_message')
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    warning = "Looks like a possible {series} spoiler, {user}. Please tag it if it is, or the <@&{mod_role}> will issue a warning.\n\nTag example: `[{series} Full]||{series} spoiler||`\n\nMessage Link: {jump_link}"
    
    async with bot.pool.acquire() as connection:
        spoiler_list = await connection.fetch('SELECT phrase, exceptions, spoiler_channels, series FROM spoilers WHERE guild_id=$1', message.guild.id)

        mod_role = await connection.fetchrow('SELECT mod_role FROM guilds WHERE id=$1', message.guild.id)

    for spoiler in spoiler_list:
        if re.search(r'(?i)(?![^\|\|]*\|\|)' + spoiler['phrase'], message.content.lower()):
            if spoiler['spoiler_channels']:
                if message.channel.id in spoiler['spoiler_channels']:
                    return

            mod_role = mod_role['mod_role'] if mod_role else None
            message_text = message.content.lower()
                
            if spoiler['exceptions']:
                if any(exception in message_text for exception in spoiler['exceptions']):
                    return
                
            await message.channel.send(warning.format(user = message.author.mention,
                                                      mod_role = mod_role,
                                                      jump_link = message.jump_url,
                                                      series = spoiler['series']))

@bot.event
async def on_guild_join(guild):
    async with bot.pool.acquire() as connection:
        await connection.execute("INSERT INTO guilds(id) VALUES($1)", guild.id)

@bot.event
async def on_guild_remove(guild):
    async with bot.pool.acquire() as connection:
        await connection.execute("DELETE FROM guilds WHERE id=$1", guild.id)

@bot.group()
@commands.has_permissions(administrator=True)
async def spoiler(context):
    ''' Run s!help for subcommands '''
    if context.invoked_subcommand is None:
        pass
            

@spoiler.command()
async def add(context, spoiler, series):
    async with bot.pool.acquire() as connection:
        await connection.execute('''
        INSERT INTO spoilers(guild_id, phrase, series) 
        VALUES($1, $2, $3)
        ''', context.guild.id, spoiler, series)

    await context.send("Spoiler added: {}".format(spoiler))

@spoiler.command()
async def remove(context, spoiler):
    async with bot.pool.acquire() as connection:
        await connection.execute('''
        DELETE FROM spoilers 
        WHERE guild_id=$1 AND phrase=$2
        ''', context.guild.id, spoiler)

    await context.send("Spoiler removed: {}".format(spoiler))

@spoiler.command()
async def list(context):
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
async def tag(context, *, label=None):
    ''' Spoiler tags an image or text '''
    if context.message.attachments:
        for attachment in context.message.attachments:
            fp = io.BytesIO()
            
            bytes_written = await attachment.save(fp)
            
            if bytes_written > 0:
                await context.send(content="{} sent: [{}]".format(context.author.mention, label),
                                   file=discord.File(fp, filename="SPOILER_" + attachment.filename, spoiler=True))

    await context.message.delete()

async def main():
    credentials = {
        "user": POSTGRES_USER,
        "password": POSTGRES_PASSWORD,
        "database": POSTGRES_DATABASE,
        "host": POSTGRES_HOST,
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
            series text,
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
