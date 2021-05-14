import discord
import os
import json
import random
from dotenv import load_dotenv
import asyncio
import googletrans
import enchant
from music_bot import MusicBot

'''
PREREQUISITES:
de hunspell dictionary for enchant
googletrans version 4.0.0
FFMPEG binary
'''

# DATA PATHS
copypastas_file = "data/copypastas.json"
settings_file = "data/settings.json"
urls_file = "data/urls.json"
xd_variations_file = "data/xd_variations.txt"
role_emoji_file = "data/role-emoji.json"
magic_muschel_file = "data/magic_muschel_answers.json"

johncena1 = "audio/johncena.mp3"
johncena2 = "audio/johncena2.mp3"

# INITIALIZE BOT
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN_DEV")
FFMPEG_PATH = os.getenv("FFMPEG_PATH")

intents = discord.Intents.all()
bot = discord.Client(intents=intents)


class Command:
    def __init__(self, function, name: str, description: str, isEnabled: bool = True, isDeamon: bool = False, needPermission: bool = False):
        self.fun = function
        self.isEnabled = isEnabled
        self.isDeamon = isDeamon
        self.needPermission = needPermission
        self.description = description


# SETTINGS FUNCTIONS
def dump_settings():
    settings = {}
    settings["commands"] = {}

    for key, val in commands.items():
        settings["commands"][key] = val["enabled"]

    settings["restricted-channel"] = restricted_channel
    settings["role-channel"] = role_channel
    settings["role-message"] = role_message
    settings["role-remove-message"] = role_remove_message

    with open(settings_file, "w") as fp:
        json.dump(settings, fp)


def load_settings():
    global restricted_channel
    global role_channel
    global role_message
    global role_remove_message

    settings = {}

    with open(settings_file, "r") as fp:
        settings = json.load(fp)

    print(str(settings.items()))

    for keyD, valD in settings["commands"].items():
        commands[keyD]["enabled"] = valD

    restricted_channel = settings["restricted-channel"]
    role_channel = settings["role-channel"]
    role_message = settings["role-message"]
    role_remove_message = settings["role-remove-message"]


# COMMAND FUNCTIONS
async def command_selector(message):
    command = message.content.split(" ")
    if command[1] == "enable" or command[1] == "disable":
        if not message.author.guild_permissions.administrator:
            await message.channel.send("No permission Sadge")
            return

        if command[2] not in commands:
            await message.channel.send(f"unknown feature {command[2]}")
        else:
            if command[1] == "enable":
                commands[command[2]]["enabled"] = True
            else:
                commands[command[2]]["enabled"] = False

            await message.channel.send(f"{command[1]}d feature:" +
                                       " **{command[2]}**")

            dump_settings()

    elif command[1] in commands:
        if commands[command[1]]["fun"] is None:
            await message.channel.send("Can't execute this command directly")
            return

        if commands[command[1]]["needPermission"] and message.author.guild_permissions.administrator:
            await commands[command[1]]["fun"](message)

        elif not commands[command[1]]["needPermission"]:
            await commands[command[1]]["fun"](message)

        else:
            await message.channel.send("No permission PepeHands")
    else:
        await message.channel.send(f"unknown command or feature **{command[1]}**")


async def post_copypasta(message): # gets a random entry from the copypasta file
    if not commands["kopiernudel"]["enabled"]: return 
    randIndex = random.randint(0, len(copypastas) - 1)
    await message.channel.send(copypastas[str(randIndex)])


async def check_xd(message):  # checks for "xd", including all formats in the xd_variations file and replies with random xd string (5% chance)
    if not commands["xd"]["enabled"]:
        return

    if random.randint(0, 100) < 95:
        return

    for v in xd_variations:
        if v in message.content:
            await message.channel.send("".join([c.upper() if random.randint(0, 1) == 0 else c.lower()
                                       for c in "x" + random.randint(1, 10) * "d"]))
            return


async def stupidedia_random(message): #TODO fix, some api changed, should get a random page from stupidedia and display its content
    """url = urls["stupidedia_random"]
    scraper = cloudscraper.create_scraper()
    
    html_unparsed = scraper.get(url).text

    html = BeautifulSoup(html_unparsed, "html.parser")
    print(html)
    div = html.find(id="mw-content-text")
    print(div)
    out = html.find(id="firstHeading").get_text() +
    print(out)
    out += div.find("p").get_text()
    out = html"""

    await message.channel.send("lul")

async def help_message(message): #prints a help message including all commands
    embed = discord.Embed(title="Commands", description="Usage: -mr command", color=0x34aae5)

    for key in commands.keys():
        if not commands[key]["needPermission"] and not commands[key]["isDeamon"] and commands[key]["enabled"]: #only print commands for which no permissions are needed and aren't deamons
            embed.add_field(name=f"\t**{key}**", value=commands[key]["desc"])

    if message.author.guild_permissions.administrator:
        for key in commands.keys():
            if commands[key]["needPermission"] or not commands[key]["enabled"] or commands[key]["isDeamon"]:
                name = f"**{key} (Admin only)**"

                if not commands[key]["enabled"]:
                    name += " [disabled]"

                if commands[key]["isDeamon"]:
                    name += " [feature]"

                embed.add_field(name=name, value=commands[key]["desc"])
        
        embed.add_field(name="Note", value="To enable/disable any command type: \"-mr enable/disable \{command\}\"")

    await message.channel.send(embed=embed)

async def john_cena(channel): #joins channel (0.5% chance), and plays john cena
    rnd = random.randint(1, 200)
    print(rnd)

    if rnd == 1:
        client = await channel.connect()

        source = johncena1
        source2 = johncena2

        audio_source = discord.FFmpegPCMAudio(executable=FFMPEG_PATH, source= source2 if random.randint(1, 10) == 1 else source)
        client.play(audio_source)

        while client.is_playing():
            await asyncio.sleep(1)

        await client.disconnect()

async def magic_muschel(message):
    rnd = random.randint(0, len(muschel_answers))
    await message.channel.send(list(muschel_answers.values()[rnd]))

async def random_list(message):
    message_text = message.content[16:]
    message_arr = message_text.split(",")
    random.shuffle(message_arr)

    out = "---\n"

    for i in range(len(message_arr)):
        out += f"{i}. {message_arr[i]}\n"
    
    await message.channel.send(out)

async def restricted_channel_update(message): #sets the channel from which to accept commands
    global restricted_channel
    channel_id = message.content.split(" ")[-1]
    
    if channel_id == "None":
        role_channel = None
        out = "**Cleared** Role Channel"
        await message.channel.send(out)
        return
        
    channel_id = channel_id[2:-1]
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        out = "bruh couldn't find the channel"
    else:
        out = f"Set Role Channel to: {channel.name}"
        restricted_channel = channel.id
        dump_settings()
    
    await message.channel.send(out)

async def role_channel_update(message): #sets the channel to send the role messages to
    global role_channel
    channel_id = message.content.split(" ")[-1]
    
    if channel_id == "None":
        role_channel = None
        out = "**Cleared** Role Channel"
        await message.channel.send(out)
        return

    channel_id = channel_id[2:-1]
    channel = bot.get_channel(int(channel_id))
    if channel is None:
        out = "bruh couldn't find the channel"
    else:
        out = f"Set Role Channel to: {channel.name}"
        role_channel = channel.id
        dump_settings()
    
    await message.channel.send(out)

async def role_channel_send_message(message, is_remove=False):
    global role_message
    global role_remove_message

    add_or_rem = "get" if not is_remove else "remove"
    out = f"**React with these emojis to {add_or_rem} these roles**\n"

    if not is_remove:
        for key in role_emojis.keys():
            out += f"{key} - {role_emojis[key]}\n"

    role_message_obj = await bot.get_channel(role_channel).send(out)
    if is_remove:
       role_remove_message = role_message_obj.id
    else:
        role_message = role_message_obj.id

    await message.channel.send(f":+1: Sent {add_or_rem} role to: {bot.get_channel(role_channel).name}")
    
    for emoji in role_emojis.keys():
        await role_message_obj.add_reaction(emoji)

    dump_settings()

async def role_channel_rem_send_message(message):
    await role_channel_send_message(message, is_remove=True)

async def role_channel_rem_add_send_message(message):
    await role_channel_send_message(message, is_remove=False)
    await role_channel_send_message(message, is_remove=True)

async def check_german(message): #checks whether german is in the message and replies (1% chance)
    message_text = message.content
    if message_text.count(" ") > 20 or len(message_text) > 150 or message_text.startswith("https://"): return

    out = ""
    words = message_text.split(" ")

    if translator.detect(message_text).lang == "en" and random.randint(1, 100) == 1:
        if random.randint(1, 100) <= 50:
            out = "Sprich Deutsch du Hurensohn"

        elif random.randint(1, 100) <= 50:
            any_exchanged = False

            for word in words:
                if dict_en.check(word) and not dict_de.check(word):
                    to_en = translator.translate(word, dest="en").text
                    to_de = translator.translate(to_en, dest="de").text
                    message_text = message_text.replace(word, f"**{to_de}**", 1)
                    any_exchanged = True

            if any_exchanged:
                out = "Meintest du: " + message_text + "?"

    if len(out) != 0: await message.channel.send(out)

#EVENT HANDLER
@bot.event
async def on_voice_state_update(member, before, after):
    if not member.bot and ((before.channel is None and after.channel is not None) or (before.channel is not None and after.channel is not None and before.channel != after.channel)):
        await john_cena(after.channel)


@bot.event
async def on_ready():
    server_count = len(bot.guilds)
    for guild in bot.guilds:
        print(f"Connected to: {guild.name}")
    print(f"Server Count: {server_count}")

@bot.event
async def on_message(message): #either runs command or runs all Deamons on the message
    if not message.author.bot and message.content is not None and len(message.content) != 0:
        if message.content.startswith("-mr ") and (message.channel.id == restricted_channel or restricted_channel is None):
            await command_selector(message)
        else:
            for feature in commands.values():
                if feature["fun"] is not None and feature["isDeamon"]: await feature["fun"](message)

@bot.event
async def on_raw_reaction_add(payload): #adds role depending on with which emoji the user reacted to the message
    if payload.message_id == role_message or payload.message_id == role_remove_message:
        if str(payload.emoji) in role_emojis.keys():
            role = discord.utils.get(payload.member.guild.roles, name=role_emojis[str(payload.emoji)])
            if role is not None:
                if payload.message_id == role_message:
                    await payload.member.add_roles(role)
                else:
                    await payload.member.remove_roles(role)
        else:
            message = await bot.get_channel(role_channel).fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)

@bot.event
async def on_member_join(member):
    role1 = discord.utils.get(member.guild.roles, name="────────────────────")
    role2 = discord.utils.get(member.guild.roles, name="Avikratischer Besucher")

    await member.add_roles(role1)
    await member.add_roles(role2)

# LOAD DATA
with open(copypastas_file, "r", encoding="utf-16") as fp:
    copypastas = json.load(fp)

with open(role_emoji_file, "r", encoding="utf-16") as fp:
    role_emojis = json.load(fp)

with open(xd_variations_file, "r") as fp:
    xd_variations = fp.read().split(",")

with open(urls_file, "r") as fp:
    urls = json.load(fp)

with open(magic_muschel_file, "r") as fp:
    muschel_answers = json.load(fp)

#german checker stuff
translator = googletrans.Translator()
dict_en = enchant.Dict("en_US")
dict_de = enchant.Dict("de_DE")

#music bot stuff
music_bot = MusicBot()

#ALL COMMANDS
commands = {
    "kopiernudel": {"fun": post_copypasta, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "sends a random german copypasta"},
    "xd": {"fun": check_xd, "enabled": True, "isDeamon": True, "needPermission": False, "desc": "checks for 'xd' and replies sometimes"},
    "help": {"fun": help_message, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "Sends a message with all available commands (depending on the users role)"},
    "wissen": {"fun": stupidedia_random, "enabled": False, "isDeamon": False, "needPermission": False, "desc": "Fetches a random page from Stupidedia (doesn't work rn cuz the bot cant scrape their website cuz they have fucking cloudflare protection wtf *why*)"},
    "deutschdurchsetzer": {"fun": check_german, "enabled": True, "isDeamon": True, "needPermission": False, "desc": "When an english message appears, the bot will sometimes reply"},
    "accidental-cena": {"fun": None, "enabled": True, "isDeamon": True, "needPermission": False, "desc": "John Cena randomly joins a channel (only enable/disable)"},
    "change-restricted-channel": {"fun": restricted_channel_update, "enabled": True, "isDeamon": False, "needPermission": True, "desc": "specifies the channel from which to accept commands, **None** to accept from all channels"},
    "change-role-channel": {"fun": role_channel_update, "enabled": True, "isDeamon": False, "needPermission": True, "desc": "specifies the role channel (link with '#')"},
    "send-reaction-message": {"fun": role_channel_send_message, "enabled": True, "isDeamon": False, "needPermission": True, "desc": "sends the role add message to the specified role channel"},
    "send-reaction-rem-message": {"fun": role_channel_rem_send_message, "enabled": True, "isDeamon": False, "needPermission": True, "desc": "sends the role remove message to the specified role channel"},
    "send-reaction-rem-add-message": {"fun": role_channel_rem_add_send_message, "enabled": True, "isDeamon": False, "needPermission": True, "desc": "sends the role add and remove message to the specified role channel"},
    "random-list": {"fun": random_list, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "randomize a set of elements, seperated by \",\""},
    "p": {"fun": music_bot.play, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "adds a song to the queue, also lets the bot join the channel if it hasn't already"},
    "join": {"fun": music_bot.connect, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "connects the bot to the channel you're currently in"},
    "pause": {"fun": music_bot.pause, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "pauses the music"},
    "resume": {"fun": music_bot.resume, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "resumes the music"},
    "q": {"fun": music_bot.print_queue, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "prints the queue"},
    "bye": {"fun": music_bot.disconnect, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "the bot leaves :("},
    "s": {"fun": music_bot.skip_song, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "skips the current song"},
    "np": {"fun": music_bot.print_now_playing, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "prints the currently playing song"},
    "pt": {"fun": music_bot.playtop, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "prints the currently playing song"},
    "clear": {"fun": music_bot.clear_queue, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "clears the queue"},
    "muschel": {"fun": magic_muschel, "enabled": True, "isDeamon": False, "needPermission": False, "desc": "Die magische Miesmuschel gibt weise Antworten"}
}

#with open("commands.json", "w") as fp:
#    json.dump(commands, fp)

restricted_channel = None
role_channel = None
role_message = None
role_remove_message = None



load_settings()

bot.run(DISCORD_TOKEN)
