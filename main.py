import asyncio
import datetime
from zoneinfo import ZoneInfo
import discord
from discord.ext import commands, tasks
import logging
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

ROLE_IDS = [1372405122566459433, 1372455418319732926, 1372405444928213093, 745153619313033266]
         # [Engineering, Usability, Leads, Testing/Owner]

ESCALATION_IDS = [622934594609610752]
               # [Rohit]

CHANNEL_IDS = [1372406245251747941, 1379920251374014524, 677045772394561548]
            # [#builds, #main, Testing/#general]

TZ = ZoneInfo("America/Los_Angeles")
REMINDER_DAY = 1     # Tuesday (Mon=0, Tue=1, etc)
REMINDER_HOUR = 16   # 0-23
REMINDER_MINUTE = 30 # 0-59

# reminder on saturdays at 2:50 pm
REMINDER2_DAY = 5     # Saturday
REMINDER2_HOUR = 14
REMINDER2_MINUTE = 50
WAIT_TIME = 10

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@tasks.loop(time=datetime.time(hour=REMINDER_HOUR, minute=REMINDER_MINUTE, tzinfo=TZ))
async def build_reminder(): ### Tuesday Engineering reminder
    now = datetime.datetime.now(TZ)
    if now.weekday() != REMINDER_DAY:
        return

    print(f"[{datetime.datetime.now()}] Starting reminder")

    channel = bot.get_channel(CHANNEL_IDS[0])
    if not channel:
        print("Channel not found")
        return

    reminder_message = await channel.send(f'<@&{ROLE_IDS[1]}> - Can you confirm "✅ Build is in" by 5:00 PM PT?\n<@&{ROLE_IDS[0]}> reminder: upload by 5:00 PM PT.')
    await reminder_message.add_reaction("✅")

    print(f"[{datetime.datetime.now()}] Reminder sent in #{channel.name} (ID: {CHANNEL_IDS[0]})")

    def check(reaction, user):
        if user.bot:
            return False
        if reaction.message.id != reminder_message.id:
            return False
        if str(reaction.emoji) != "✅":
            return False

        member = reaction.message.guild.get_member(user.id)
        return any(role.id in ROLE_IDS for role in member.roles)

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=35*60.0, check=check) # 35 minutes
        await channel.send(f'✅ Confirmed by {user.name} at {datetime.datetime.now().strftime("%H:%M %p")}!')
        print(f"[{datetime.datetime.now()}] Confirmation received from {user} in #{channel.name}")

    except asyncio.TimeoutError:
        await channel.send(f' <@{ESCALATION_IDS[0]}> <@&{ROLE_IDS[0]}> <@&{ROLE_IDS[1]}> ⏰ No confirmation by 5:00 PM PT. Rohit: please verify with Engineering & Usability.')
        print(f"[{datetime.datetime.now()}] No confirmation, escalation triggered in #{channel.name}")

@tasks.loop(time=datetime.time(hour=REMINDER2_HOUR, minute=REMINDER2_MINUTE, tzinfo=TZ))
async def lab_reminder(): ### Saturday Leads reminder
    now = datetime.datetime.now(TZ)
    if now.weekday() != REMINDER2_DAY:
        return

    print(f"[{datetime.datetime.now()}] Starting reminder")

    channel_id = CHANNEL_IDS[1]
    channel = bot.get_channel(channel_id)
    if not channel:
        print("Lab reminder channel not found")
        return

    role_mention = "<@&" + str(ROLE_IDS[2]) + ">"
    msg_to_send = f"{role_mention} - It's the end of lab, so please post your standups before leaving!\n1. What did you this past week,\n2. What you are currently doing,\n3. What you will do next sprint (next week),\n4. Any blockers?"
    print("Message sent.")
    send_msg = await channel.send(msg_to_send)

    print(f"[{datetime.datetime.now()}] Reminder sent in #{channel.name} (ID: {channel_id})")

    guild = channel.guild
    role = guild.get_role(ROLE_IDS[2])
    responders = set()

    def check(message):
        if message.channel.id != channel_id:
            return False
        if message.author.bot:
            return False
        if role not in message.author.roles:
            return False
        return True

    try:
        end_time = datetime.datetime.now() + datetime.timedelta(minutes=10)
        print(f"[{datetime.datetime.now()}] Waiting for responses until {end_time}")
        while datetime.datetime.now() < end_time:
            msg = await bot.wait_for("message", timeout=WAIT_TIME*60.0, check=check)
            responders.add(msg.author.id)
            print(f"[{datetime.datetime.now()}] {msg.author.name} responded")
    except asyncio.TimeoutError:
        pass

    missing_responders = [member for member in role.members if member.id not in responders]
    if missing_responders:
        mentions = " ".join(m.mention for m in missing_responders)
        await channel.send(f"{mentions} - Another reminder to post your standups!")
        print(f"[{datetime.datetime.now()}] Missing responses: {mentions}")
    else:
        await channel.send("Everyone responded!")
        print(f"[{datetime.datetime.now()}] All responders responded")



@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    if not build_reminder.is_running():
        build_reminder.start()
        print("Build reminder started")
    if not lab_reminder.is_running():
        lab_reminder.start()
        print("Lab reminder started")

bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)
