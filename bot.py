import discord
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

song_queue = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="play", description="Search and play a song from YouTube")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    try:
        ydl_opts = {
            'format': 'bestaudio',
            'quiet': True,
            'extract_flat': 'in_playlist', 
            'noplaylist': 'True',
            'default_search': 'ytsearch',  
            'source_address': '0.0.0.0',  
        }
        with YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(query, download=False)
            if 'entries' in results:
                video = results['entries'][0]  
            else:
                video = results

        title = video.get('title')
        url = video.get('url')

        if interaction.guild.id not in song_queue:
            song_queue[interaction.guild.id] = []

        song_queue[interaction.guild.id].append((title, url))

        if len(song_queue[interaction.guild.id]) == 1:  
            await play_song(interaction.guild.id, interaction)

        embed = discord.Embed(title="Added to Queue", description=f"[{title}]({url})", color=discord.Color.blue())
        await interaction.followup.send(embed=embed)
    except Exception as e:
        print(f"Error during YouTube search: {e}")
        await interaction.followup.send(f"Error occurred while searching for the song: {e}")

async def play_song(guild_id, interaction):
    guild = interaction.guild
    vc = discord.utils.get(bot.voice_clients, guild=guild)
    if not vc:
        vc = await guild.voice_channels[0].connect()

    try:
        if song_queue[guild_id]:
            title, url = song_queue[guild_id][0]
            YDL_OPTIONS = {'format': 'bestaudio'}
            FFMPEG_OPTIONS = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn',
            }

            with YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['url']
                source = await discord.FFmpegOpusAudio.from_probe(url2, **FFMPEG_OPTIONS)
                vc.play(source, after=lambda e: next_song(guild_id, interaction))
                embed = discord.Embed(title="Now Playing", description=f"[{title}]({url})", color=discord.Color.green())
                await interaction.channel.send(embed=embed)
    except Exception as e:
        print(f"Error playing the song: {e}")

def next_song(guild_id, interaction):
    if song_queue[guild_id]:
        song_queue[guild_id].pop(0)
        if song_queue[guild_id]:
            bot.loop.create_task(play_song(guild_id, interaction))

@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    await interaction.response.defer()
    guild_id = interaction.guild.id
    if guild_id in song_queue and song_queue[guild_id]:
        guild = interaction.guild
        vc = discord.utils.get(bot.voice_clients, guild=guild)
        if vc and vc.is_playing():
            vc.stop()
        await interaction.followup.send("Skipped to the next song.")
    else:
        await interaction.followup.send("No song is currently playing.")

@bot.tree.command(name="queue", description="View the current song queue")
async def queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id in song_queue and song_queue[guild_id]:
        queue_list = [f"{i + 1}. {title} - {url}" for i, (title, url) in enumerate(song_queue[guild_id])]
        queue_message = "\n".join(queue_list)
        embed = discord.Embed(title="Current Song Queue", description=queue_message, color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("The queue is currently empty.")

@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("Paused the current song.")
    else:
        await interaction.response.send_message("No song is currently playing or the song is already paused.")

@bot.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("Resumed the song.")
    else:
        await interaction.response.send_message("No song is currently paused or already playing.")

@bot.tree.command(name="clearqueue", description="Clear the current song queue")
async def clearqueue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id in song_queue:
        song_queue[guild_id] = []
        await interaction.response.send_message("The song queue has been cleared.")
    else:
        await interaction.response.send_message("The queue is already empty.")

@bot.tree.command(name="help", description="Display all available commands and their descriptions")
async def help_command(interaction: discord.Interaction):
    commands_list = [
        "/play <query> - Search and play a song from YouTube",
        "/skip - Skip the current song",
        "/queue - View the current song queue",
        "/pause - Pause the current song",
        "/resume - Resume the paused song",
        "/clearqueue - Clear the current song queue"
    ]
    help_message = "\n".join(commands_list)
    embed = discord.Embed(title="Help - Available Commands", description=help_message, color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_disconnect():
    for vc in bot.voice_clients:
        await vc.disconnect()

bot.run("MTMxNjU4MTI5MjcwNzU0NTE3OA.GAC8Id.zKuomzkfmyBg2iqYJtlr9NtTSiUL8uZRuuZnUI")
