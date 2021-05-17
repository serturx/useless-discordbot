import discord
import youtube_dl
import asyncio
from requests.models import PreparedRequest
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import os


class Song:
    def __init__(self, title, url):
        self.title = title
        self.url = url

    def get_session(self):
        with youtube_dl.YoutubeDL({}) as ydl:
            info = ydl.extract_info(self.url, download=False)
            return info["formats"][0]["url"]


class URL:
    def __init__(self, url):
        self.url = url

    def is_valid_url(self):
        prepared_request = PreparedRequest()
        try:
            prepared_request.prepare_url(self.url, None)
            return True
        except Exception:
            return False

    def is_spotify(self):
        return "spotify.com" in self.url

    def is_yt(self):
        return "youtube.com" in self.url

    def get_spotify_id(self):
        return self.url.split("/")[-1]


class MusicBot:

    def __init__(self):
        self.voice_client = None
        self.queue = []
        self.playing = None
        self.voice_channel = None
        self.text_channel = None
        self.music_paused = False
        self.skip = False
        self.is_playing = False

        load_dotenv()

        credentials = SpotifyClientCredentials(
                                                os.getenv("SPOTIFY_CLIENT_ID"),
                                                os.getenv("SPOTIFY_CLIENT_SECRET"))

        self.spotify = spotipy.Spotify(auth=credentials.get_access_token())

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

    async def search_yt(self, query):
        try:
            with youtube_dl.YoutubeDL({}) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}",
                                        download=False)["entries"][0]
                return Song(info["title"], info["webpage_url"])

        except Exception as err:
            self.text_channel.send("Error while searching YouTube: " + str(err))

    async def convert_to_yt_song(self, url: URL):
                #if "playlist" in url:
                #    print(self.spotify.playlist_items(ressource_id)["tracks"][0]["track"]["name"])
                #    return
        if "track" in url.url:
            track = self.spotify.track(url.get_spotify_id())
            return await self.search_yt(track["name"] + " " + track["album"]["artists"][0]["name"])
        else:
            raise ValueError("Spotify Link is not a track")

    def get_playlist_tracks(self):
        return

    def pause(self, message):
        self.voice_client.pause()
        self.music_paused = True

    def resume(self, message):
        self.voice_client.resume()
        self.music_paused = False

    async def remove_index(self, message):

        try:
            index = int(message.content[7:])
            song = self.queue.pop(index + 1)
            await self.text_channel.send("Removed " + song.title)
        except Exception as err:
            await self.text_channel.send("Error while removing song: " +
                                         str(err))

        return

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
        self.playing = None
        self.is_playing = False

    def get_song_from_yt(self, url):
        with youtube_dl.YoutubeDL({}) as ydl:
            info = ydl.extract_info(url, download=False)
            return Song(info["title"], info["webpage_url"])

    async def add_to_queue(self, link: str, playtop=False, verbose=True):
        try:
            url = URL(link)
            song = None

            if(url.is_valid_url()):
                if url.is_yt():
                    song = self.get_song_from_yt(url)
                elif url.is_spotify():
                    song = await self.convert_to_yt_song(url)
                else:
                    await self.text_channel.send("Unsupported Platform :(")

                if song is not None:
                    if playtop:
                        self.queue.append(song)
                    else:
                        self.queue.insert(0, song)

                    if verbose:
                        await self.text_channel.send("Added: " + song.title)

        except Exception as err:
            await self.text_channel.send(
                                        "Error while retrieving" +
                                        " song info : " + str(err))

    async def print_queue(self, message):
        if self.channel is None:
            return

        queue_str = f"**Now Playing: ** {self.playing.title} \n**Queue: \n **"
        for i in range(0, len(self.queue)):
            queue_str += f"{i + 1}. ```{self.queue[i].title}``` \n"

        await self.text_channel.send(queue_str)

    async def print_now_playing(self, message): # TODO add current song length/position
        await self.text_channel.send("**Now Playing: **" + self.playing.title)

    async def clear_queue(self, message):
        self.queue = []
        await self.text_channel.send("**Queue cleared**")

    async def skip_song(self, message):
        await self.text_channel.send("**Skipped** :D")
        self.skip = True

    async def play_queue(self):

        self.is_playing = True
        while(len(self.queue) != 0):
            self.playing = self.queue.pop(0)
            session = self.playing.get_session()
            source = discord.FFmpegPCMAudio(
                            source=session,
                            before_options="-reconnect 1 " +
                                           "-reconnect_streamed 1 " +
                                           "-reconnect_delay_max 5")
            self.voice_client.play(source)

            try:
                while((self.voice_client.is_playing() or self.music_paused)
                        and not self.skip):
                    await asyncio.sleep(1)
            except Exception as err:
                await self.text_channel.send("Error while playing: "
                                             + str(err))
                self.disconnect(None)

            self.voice_client.stop()
            self.skip = False
