import discord
import youtube_dl
import asyncio
from requests.models import PreparedRequest
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import os
import random
from enum import Enum


class Emojis(Enum):
    OKAYCHAMP = "<:okayChamp:836005875936133121>"
    LULW = "<:LULW:822269834728439818>"
    PAINCHAMP = "<:painChamp:822271360804847657>"
    LEOSKATZE = "<:LeosKatze:830104066678980688>"
    MONKAHMM = "<:monkaHmm:821505358128349215>"
    WEIRDCHAMP = "<:weirdChamp:822269328279207946>"


class Song:
    def __init__(self, title: str, url: str, length: int):
        self.title = title
        self.url = url
        self.length = length

    def get_session(self):
        with youtube_dl.YoutubeDL({}) as ydl:
            info = ydl.extract_info(self.url, download=False)
            return info["formats"][0]["url"]

    def __str__(self):
        return f"[`{self.title}`]({self.url})"

    def get_length(self):
        return f"{int(self.length) // 60}:{int(self.length) % 60:02d}"


class PlayingTrack:
    def __init__(self, song: Song):
        self.song = song
        self.current_pos = 0

    def get_playing_info(self):
        return f"{int(self.current_pos) // 60}:{int(self.current_pos) % 60:02d}/{self.song.get_length()}"


class URL:
    def __init__(self, url: str):
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

    def is_playlist(self):
        return "playlist" in self.url or "album" in self.url

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
        self.disconnecting = False
        self.queue_looping = False
        self.song_looping = False

        self.set_discord()

    def set_discord(self):
        load_dotenv()

        auth = SpotifyClientCredentials(os.getenv("SPOTIFY_CLIENT_ID"),
                                        os.getenv("SPOTIFY_CLIENT_SECRET"))

        self.spotify = spotipy.Spotify(auth_manager=auth)

    async def play(self, message, playtop=False):
        if self.voice_client is None:
            try:
                await self.connect(message)
            except Exception as err:
                await message.channel.send(":x: Couldn't connect: " + str(err))

        if self.voice_client is not None:
            if message.author.voice.channel.id != self.voice_channel.id:
                await self.text_channel.send(f"{Emojis.LULW} You must be in the same channel to send commands")
                return

            await self.add_to_queue(message.content[6:], playtop=playtop)

            if not self.voice_client.is_playing():
                await self.play_queue()

    async def playtop(self, message):
        await self.play(message, playtop=True)

    async def search_yt(self, query):
        try:
            with youtube_dl.YoutubeDL({}) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}",
                                        download=False)["entries"][0]
                return Song(info["title"], info["webpage_url"], info["duration"])

        except Exception:
            return None

    async def convert_to_yt_song(self, url: URL):
        if "track" in url.url:
            for i in range(0, 2):
                try:
                    track = self.spotify.track(url.get_spotify_id())
                    result = await self.search_yt(track["name"] + " " + track["album"]["artists"][0]["name"])
                    return result
                except AttributeError as err:
                    print(f"Retrying {i}: {str(err)}")
                    self.set_discord()
        else:
            raise ValueError(":x: Spotify Link is not a track")

    async def pause(self, message):
        self.voice_client.pause()
        self.music_paused = True

    async def resume(self, message):
        self.voice_client.resume()
        self.music_paused = False

    async def shuffle_list(self, message):
        random.shuffle(self.queue)
        await self.text_channel.send(":twisted_rightwards_arrows: **Shuffled** the queue")

    async def remove_index(self, message):

        try:
            index = int(message.content.split(" ")[-1])
            song = self.queue.pop(index - 1)
            await self.text_channel.send(":white_check_mark: **Removed** " + song.title)
        except Exception as err:
            await self.text_channel.send(":x: Error while removing song: " + str(err))

        return

    async def connect(self, message):
        self.text_channel = message.channel

        if message.author.voice is None:
            raise(ConnectionError(":x: You're not currently in a voice channel"))
        else:
            self.voice_channel = message.author.voice.channel
            self.voice_client = await self.voice_channel.connect()
            await self.text_channel.send(f"{Emojis.OKAYCHAMP.value} **Connected** :)")

    async def set_disconnect_flag(self, message):
        self.disconnecting = True

    async def disconnect(self, message):
        await self.text_channel.send(Emojis.PAINCHAMP.value)
        await self.voice_client.disconnect()
        self.voice_client = None
        self.queue = []
        self.playing = None
        self.voice_channel = None
        self.text_channel = None
        self.music_paused = False
        self.skip = False
        self.is_playing = False
        self.disconnecting = False
        self.queue_looping = False

    def get_song_from_yt(self, url: URL):
        with youtube_dl.YoutubeDL({}) as ydl:
            info = ydl.extract_info(url.url, download=False)
            return Song(info["title"], info["webpage_url"], info["duration"])

    async def add_playlist_to_queue(self, url: URL, playtop=False):
        playlist = []
        playlist_title = ""

        await self.text_channel.send(":hourglass_flowing_sand: Gathering Playlist information...")

        if url.is_spotify():
            for i in range(0, 2):
                try:
                    if "playlist" in url.url:
                        playlist_items = self.spotify.playlist_items(url.get_spotify_id(), limit=21)

                        tracks = playlist_items["tracks"]["items"][:20]

                        for entry in tracks:

                            try:
                                artist = entry["track"]["album"]["artists"][0]["name"]

                                song = await self.search_yt(entry["track"]["name"] + " " + artist)
                                if song is not None:
                                    playlist.append(song)
                                else:
                                    await self.text_channel.send(":x: Couldn't add " + entry["track"]["name"])
                            except IndexError:
                                await self.text_channel.send(":x: Couldn't add " + entry["track"]["name"])

                        playlist_title = playlist_items["name"]

                    elif "album" in url.url:
                        album_items = self.spotify.album_tracks(url.get_spotify_id(), limit=21)

                        tracks = album_items["tracks"]["items"][:20]

                        for entry in tracks:
                            try:
                                artist = entry["artists"][0]["name"]
                                song = await self.search_yt(entry["name"] + " " + artist)
                                playlist.append(song)
                            except IndexError:
                                pass

                        playlist_title = album_items["name"]

                    else:
                        raise ValueError(":x: invalid spotify link")
                except AttributeError as err:
                    print(f"Retrying {i}: {str(err)}")
                    self.set_discord()

        elif url.is_yt():

            with youtube_dl.YoutubeDL({}) as ydl:
                info = ydl.extract_info(url.url, download=False)

                for entry in info["entries"]:
                    playlist.append(Song(entry["title"], entry["webpage_url"], entry["duration"]))

                playlist_title = info["title"]

        if len(playlist) > 0:
            if playtop:
                self.queue = playlist + self.queue

            else:
                self.queue += playlist

            await self.text_channel.send(":white_check_mark: Added Playlist: " + playlist_title)

    async def add_to_queue(self, link: str, playtop=False, verbose=True):
        try:
            url = URL(link)
            song = None

            if url.is_valid_url():

                if url.is_playlist():
                    await self.add_playlist_to_queue(url)
                    return

                if url.is_yt():
                    song = self.get_song_from_yt(url)
                elif url.is_spotify():
                    song = await self.convert_to_yt_song(url)
                else:
                    await self.text_channel.send(":x: Unsupported Platform :(")

            else:
                song = await self.search_yt(link)

            if song is not None:
                if playtop:
                    self.queue.insert(0, song)
                else:
                    self.queue.append(song)

                if verbose:
                    embed = discord.Embed(title=f"Added:\n {song.title}", url=song.url, colour=discord.Color.purple())
                    embed.add_field(name="\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_", value=f"Position in Queue: {1 if playtop else len(self.queue)}\nLength: {song.get_length()}")
                    await self.text_channel.send(embed=embed)

        except Exception as err:
            await self.text_channel.send(":x: Error while retrieving" +
                                         " song info : " + str(err))

    async def print_queue(self, message):
        if self.voice_channel is None:
            return

        embed = discord.Embed(title=f"Now Playing:\n `{self.playing.song.title}`",
                              url=self.playing.song.url,
                              colour=discord.Color.purple())

        embed.add_field(name="\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_", value="**Queue:**", inline=False)

        total_length = self.playing.song.length

        for i in range(0, len(self.queue)):
            embed.add_field(name="\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_",
                            value=f"{i + 1}. {str(self.queue[i])}\n`{self.queue[i].get_length()}`", inline=False)
            total_length += self.queue[i].length

        if len(self.queue) == 0:
            embed.add_field(name=f"**Wow {Emojis.LEOSKATZE.value}**", value=f"it's _empty_ {Emojis.WEIRDCHAMP.value}")

        loop_emoji = ":white_check_mark:" if self.song_looping else ":x:"
        qloop_emoji = ":white_check_mark:" if self.queue_looping else ":x:"

        embed.add_field(name="\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_", value=f"**Loop: **{loop_emoji}  **Queue Loop: **{qloop_emoji}", inline=False)
        embed.set_footer(text=f"Total Length: {total_length // 60}:{int(total_length) % 60:02d}")

        await self.text_channel.send(embed=embed)

    async def print_now_playing(self, message):
        embed = discord.Embed(title="**Now Playing:**", colour=discord.Color.purple())
        embed.add_field(name="\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_", value=str(self.playing.song) + "\n" + self.playing.get_playing_info(), inline=False)

        await self.text_channel.send(embed=embed)

    async def clear_queue(self, message):
        self.queue = []
        await self.text_channel.send(f"{Emojis.MONKAHMM.value} **Queue cleared**")

    async def skip_song(self, message):
        await self.text_channel.send(":white_check_mark: **Skipped** :D")
        self.skip = True

    async def move_song(self, message):
        split = message.content.split(" ")

        try:
            song = self.queue.pop(int(split[2]) - 1)
            self.queue.insert(int(split[3]) - 1, song)
            await self.text_channel.send(f":white_check_mark: **Moved** `{song.title}` **from** Pos. `{split[2]}` **to** Pos. `{split[3]}`")
        except Exception as err:
            await self.text_channel.send(":x: Error while moving song: " + str(err))

    async def fast_forward(self, message):
        await self.pause(None)

        try:
            skip = int(message.content.split(" ")[-1])
            skip_steps = (skip * 1000) // 20

            for i in range(0, skip_steps):
                self.source.read()

            self.playing.current_pos += skip
            await self.text_channel.send(f":white_check_mark: Skipped {skip} seconds")

        except Exception as err:
            await self.text_channel.send(":x: Error while skipping: " + str(err))

        await self.resume(None)

    async def skipto(self, message):
        try:
            skip_pos = int(message.content.split(" ")[-1])
            self.queue = self.queue[skip_pos - 1:]
            await self.text_channel.send(f"**Skipped** to pos. `{skip_pos}`")
        except Exception as err:
            await self.text_channel.send(":x: Couldn't skipto: " + str(err))

    async def queue_loop(self, message):
        self.queue_looping = not self.queue_looping
        await self.text_channel.send(("Enabled" if self.queue_looping else "Disabled") + " queue loop :arrows_clockwise:")

    async def song_loop(self, message):
        self.song_looping = not self.song_looping
        await self.text_channel.send(("Enabled" if self.song_looping else "Disabled") + " song loop :arrows_clockwise:")

    async def play_queue(self):
        self.is_playing = True

        while(len(self.queue) > 0):
            self.playing = PlayingTrack(self.queue.pop(0))
            session = self.playing.song.get_session()
            self.source = discord.FFmpegPCMAudio(source=session,
                                                 before_options="-reconnect 1 " +
                                                 "-reconnect_streamed 1 " +
                                                 "-reconnect_delay_max 5")
            self.voice_client.play(self.source)

            try:
                while((self.voice_client.is_playing() or self.music_paused) and
                      not self.skip and not self.disconnecting):
                    await asyncio.sleep(1)
                    if not self.music_paused:
                        self.playing.current_pos += 1
            except Exception as err:
                await self.text_channel.send(":x: Error while playing: " +
                                             str(err))
                await self.disconnect(None)

            if self.disconnecting:
                await self.disconnect(None)
                return

            self.voice_client.stop()
            self.skip = False
            if self.queue_looping:
                self.queue.append(self.playing.song)
            if self.song_looping:
                self.queue.insert(0, self.playing.song)
