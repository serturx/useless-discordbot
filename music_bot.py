import discord
import youtube_dl
from threading import Thread
import asyncio
from requests.models import PreparedRequest
import requests.exceptions

class Song:
    def __init__(self, title, url):
        self.title = title
        self.url = url         

class MusicBot:

    def __init__(self):
        self.voice_client = None
        self.queue = []
        self.music_thread = None
        self.playing = None
        self.voice_channel = None
        self.text_channel = None
        self.music_paused = False
        self.skip = False
        self.is_playing = False

    async def play(self, message, playtop=False):
        if self.voice_client is None:
            try:
                await self.connect(message)
            except Exception as err:
                await message.channel.send("Couldn't connect: " + str(err))

        if self.voice_client is not None:
            await self.add_to_queue(message.content[6:], playtop=playtop)
        
        if not self.voice_client.is_playing():
            await self.play_queue()

    async def playtop(self, message):
        self.play(message, playtop=True)

    async def is_url(self, url):
        prepared_request = PreparedRequest()
        try:
            prepared_request.prepare_url(url, None)
            return True
        except Exception:
            return False

    def pause(self, message):
        self.voice_client.pause()
        self.music_paused = True

    def resume(self, message):
        self.voice_client.resume()
        self.music_paused = False

    async def connect(self, message):
        self.text_channel = message.channel

        if message.author.voice is None:
            raise(ConnectionError("You're not currently in a voice channel"))
        else:
            self.channel = message.author.voice.channel
            self.voice_client = await self.channel.connect()
            await self.text_channel.send("Connected :)")

    async def disconnect(self, message):
        await self.text_channel.send("Bye :(")
        await self.voice_client.disconnect()
        self.voice_channel = None
        self.voice_client = None
        self.music_paused = False
        self.queue = []
        self.music_thread = None
        self.playing = None
        self.is_playing = False

    def get_session_from_url(self, song):
        try:
            with youtube_dl.YoutubeDL({}) as ydl:
                info = ydl.extract_info(song.url, download=False)
                return info["formats"][0]["url"]
        except Exception as err:
            print(err)

    async def add_to_queue(self, url, playtop=False):
        try:
            with youtube_dl.YoutubeDL({}) as ydl:
                if(await self.is_url(url)):
                    info = ydl.extract_info(url, download=False)
                else:
                    await self.text_channel.send("**Searching** for: " + url)
                    info = ydl.extract_info(f"ytsearch:{url}", download=False)['entries'][0]

                if(playtop):
                    self.queue.insert(0, Song(info["title"], info["webpage_url"]))
                else:
                    self.queue.append(Song(info["title"], info["webpage_url"]))

                await self.text_channel.send("**Added:** " + self.queue[-1].title)
        except Exception as err:
            await self.text_channel.send("Error while retrieving song info (2): " + str(err))

    async def print_queue(self, message):
        if self.channel is None:
            return

        queue_str = f"**Now Playing: ** {self.playing.title} \n**Queue: \n **"
        for i in range(0, len(self.queue)):
            queue_str += f"{i}. ```{self.queue[i].title}``` \n"

        await self.text_channel.send(queue_str)

    async def print_now_playing(self, message):
        await self.text_channel.send("**Now Playing: **" + self.playing.title)
    
    async def skip_song(self, message):
        await self.text_channel.send("**Skipped** :D")
        self.skip = True
    
    async def play_queue(self):
        
        self.is_playing = True
        while(len(self.queue) != 0):
            self.playing = self.queue.pop()
            session = self.get_session_from_url(self.playing)
            source = discord.FFmpegPCMAudio(source=session, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
            self.voice_client.play(source)

            try:
                while((self.voice_client.is_playing() or self.music_paused) and not self.skip):
                    await asyncio.sleep(1)
                    #await self.text_channel.send("skip = " + str(self.skip))
            except Exception as err:
                print(err)
            
            self.voice_client.stop()
            self.skip = False
        
        await self.voice_client.disconnect()

