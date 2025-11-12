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
USER_IDS = [593182696046329879] 
            # Ramsey
IGNORE_USER_IDS = [622934594609610752,692108700705620100] 
            # Ignore Kristine, ROHIT  for standups
COLEAD_IDS = [558457237924741130,305785831313113099] 
            # CJ, Juan only need 1 response for standup - Later can make a dictionary for groups only needing one check instead, but will require more checks/time
ESCALATION_IDS = [622934594609610752]
            # [Rohit]
CHANNEL_IDS = [1372406245251747941, 1379920251374014524, 677045772394561548]
            # [#builds, #main, Testing/#general]

TZ = ZoneInfo("America/Los_Angeles")
REMINDER_DAY = 5     # Saturday (Mon=0, Tue=1, Wed=2, Thur=3, Fri=4, Sat=5, Sun=6)
REMINDER_HOUR = 15   # 0-23
REMINDER_MINUTE = 00 # 0-59

# reminder on saturdays at 2:50 pm
REMINDER2_DAY = 5     # Saturday
REMINDER2_HOUR = 14
REMINDER2_MINUTE = 50
FIRST_WAIT = 10*60.00         # 2:50pm - 3pm = 10min
FINAL_WAIT = 5*60*60+10*60.00 # 2:50pm-8pm = 5h 10min 


handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@tasks.loop(time=datetime.time(hour=REMINDER_HOUR, minute=REMINDER_MINUTE, tzinfo=TZ))
async def build_reminder(): ### Saturday (Previously Tuesday) Engineering reminder
    now = datetime.datetime.now(TZ)
    if now.weekday() != REMINDER_DAY:
        return

    print(f"[{datetime.datetime.now()}] Starting reminder")

    channel = bot.get_channel(CHANNEL_IDS[0])
    if not channel:
        print("Channel not found")
        return

    reminder_message = await channel.send(f'<@&{ROLE_IDS[1]}> - Can you confirm "✅ Build is in" by 8:00 PM PT?\n<@&{ROLE_IDS[0]}> reminder: upload by 8:00 PM PT.')
    await reminder_message.add_reaction("✅")
    producer_reminder_message = await channel.send(f"Did <@{USER_IDS[0]}> check if the README was updated for today's build?")
    await producer_reminder_message.add_reaction("✅")
    print(f"[{datetime.datetime.now()}] Reminder sent in #{channel.name} (ID: {CHANNEL_IDS[0]})")

    monitor = {}
    monitor[reminder_message.id] = {"role_id": ROLE_IDS, "emoji": "✅", "done": False}
    monitor[producer_reminder_message.id] = {"user_id": USER_IDS[0], "emoji": "✅", "done": False}

    @bot.event
    async def on_reaction_add(reaction, user):
        if user.bot:
            return False
        if reaction.message.id not in [reminder_message.id, producer_reminder_message.id]:
            return False
        if str(reaction.emoji) != "✅":
            return False

        message_id = reaction.message.id
        member = reaction.message.guild.get_member(user.id)
        return any(role.id in ROLE_IDS for role in member.roles)

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=300*60.0, check=check) # 300 minutes -> 5 hrs (Previously 35 minutes)
        await channel.send(f'✅ Confirmed by {user.name} at {datetime.datetime.now().strftime("%H:%M %p")}!')
        print(f"[{datetime.datetime.now()}] Confirmation received from {user} in #{channel.name}")

    except asyncio.TimeoutError:
        await channel.send(f' <@{ESCALATION_IDS[0]}> <@&{ROLE_IDS[0]}> <@&{ROLE_IDS[1]}> ⏰ No confirmation by 8:00 PM PT. Rohit: please verify with Engineering & Usability.')
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
    responders = set(IGNORE_USER_IDS) # ignore Rohit, Kristine

    def check(message):
        if message.channel.id != channel_id:
            return False
        if message.author.bot:
            return False
        if role not in message.author.roles:
            return False
        return True
    
    async def responseReminder():
        missing_responders = [member for member in role.members if member.id not in responders]
        if missing_responders:
            mentions = " ".join(m.mention for m in missing_responders)
            await channel.send(f"{mentions} - Another reminder to post your standups!")
            print(f"[{datetime.datetime.now()}] Missing responses: {mentions}")
        else:
            await channel.send("Everyone responded!")
            print(f"[{datetime.datetime.now()}] All responders responded")
    loop = asyncio.get_running_loop()
    end_time = loop.time() + FIRST_WAIT # first ping
    end_time_final = loop.time() + FINAL_WAIT (hours=5, minutes=10) #final ping
    async def firstPing():
        firstPing = False
        while loop.time() < end_time_final:
            await asyncio.sleep(10) # to change to 10 minutes
            if not(firstPing) and (loop.time() > end_time):
                firstPing = True
                await responseReminder()
                break
    firstPingReport = asyncio.create_task(firstPing())
    print(f"[{datetime.datetime.now()}] Waiting for responses until {datetime.datetime.now() + datetime.timedelta(FIRST_WAIT)}, {datetime.datetime.now() + datetime.timedelta(FINAL_WAIT)}")
    while loop.time() < end_time_final:
        WAIT_TIME = end_time_final - loop.time()
        try:
            msg = await bot.wait_for("message", timeout=WAIT_TIME, check=check) 
            author_string = f'{msg.author.name}'
            if msg.author.id in COLEAD_IDS:
                responders.update(COLEAD_IDS)
                author_string += " Coleads" 
            else:
                responders.add(msg.author.id)
            print(f"[{datetime.datetime.now()}] {author_string} responded")
        except asyncio.TimeoutError:
            pass
    await responseReminder()

def parse_time(timestr: str) -> int:
        units = {"s": 1, "m": 60, "min":60, "h": 3600, "d": 3600*24, "w": 60*60*24*7}
        try:
            total_time = 0
            time_list = timestr.split() 
            for time in time_list:
                total_time += int(units[time[-1]]) * int(time[:-1])
            return total_time
        except (KeyError, ValueError):
            raise commands.BadArgument("Time must end with s, m, min, h, d, w (e.g. 10s, 5m, 1h)")
        
@bot.command()
async def remind(ctx, message_id: int, *, time: str):  #!remind [message_id] 12h 30m
    print(f"[{datetime.datetime.now()}] Starting reminder for message: {message_id}")
    delay = parse_time(time)
    try: 
        msg = await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx("Can't find a message with that ID in this channel.")
        return
    
    remind_date = datetime.datetime.now(TZ) + datetime.timedelta(seconds = delay)
    await ctx.send(f'⏳ Confirmed. Will send a copy of that message at {remind_date.strftime("%H:%M %p")}')

    files = [await attachment.to_file() for attachment in msg.attachments]
    mentions = msg.mentions #list of users mentioned in original message
    allowed_mentions = discord.AllowedMentions(users=mentions)

    # Wait
    await asyncio.sleep(delay)
    # Resend message content
    await ctx.send(f"📋 Reminder of message from {msg.author.mention}:\n{msg.content}", files=files, allowed_mentions=allowed_mentions)
    # Embeds if any
    for embed in msg.embeds:
        await ctx.send(embed=embed)

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
