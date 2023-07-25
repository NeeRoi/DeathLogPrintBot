import os
import re
import sys
import codecs
import nextcord
import shutil
from nextcord.ext import tasks, commands
from datetime import datetime, timedelta
from config import TOKEN

intents = nextcord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

#Mention the role that will be notified when the bot is broken
Staff = 1132058617563070484
Tech_Admin = 1132625409800929390
CHANNEL_ID = 1132681879854796841

#Roles that are allowed to use the !checknow command
ALLOWED_ROLES = [1132625665175339008, 1129764708858200154, 1129764767628787742, 1129764624468807690]

#Log paths
BEASTS_LOG_PATH = r'G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\BeastsOfBermuda.log'
BOT_LOG_PATH = r'G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\Bots\DeathLogPrint Bot\logs\Bot.log'
BACKUP_FOLDER_PATH = r"G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\Bots\DeathLogPrint Bot\logs\backup"
LAST_BACKUP_FILE = r'G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\Bots\DeathLogPrint Bot\logs\last_backup.txt'

#Death reasons listed
DEATH_REASONS = [
    "You have fallen to your death.",
    "You have drowned.",
    "You have been slain.",
    "You have died from food poisoning.",
    "You have starved to death.",
    "You died from extreme stress.",
    "You have been sacrificed to the Power Deity.",
    "You have been sacrificed to the Survival Deity.",
    "You have been sacrificed to the Mobility Deity."
]

def timestamped_print(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

@bot.event
async def on_ready():
    #Check if the Bot.log file exists and the last line is "Finish"
    try:
        with open(BOT_LOG_PATH, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            #check if lines is not empty and the last line is not 'Finish'
            if lines and lines[-1].strip() != 'Finish':
                with open(BOT_LOG_PATH, 'a') as file:
                    file.write('Finish\n')
    except FileNotFoundError:
        #If the Bot.log file does not exist, create a new one
        open(BOT_LOG_PATH, 'a').close()
        
    check_log.start()
    backup_log.start()
    cleanup_old_backups.start()

async def check_log_process():
    await bot.change_presence(activity=nextcord.Game(name="Looking for new deaths!"), status=nextcord.Status.online)
    timestamped_print("Starting check_log_process")
    
    #Check if both files exist
    if not os.path.exists(BEASTS_LOG_PATH):
        print("BeastsOfBermuda.log file not found")
        channel = bot.get_channel(CHANNEL_ID)
        staff_role = bot.get_guild(channel.guild.id).get_role(Tech_Admin)
        staff_role2 = bot.get_guild(channel.guild.id).get_role(Staff)
        #Sending message if the BeastsOfBermuda.log file is missing
        await channel.send(f'{staff_role2.mention} Tell {staff_role.mention} the DeathLogPrint Bot is broken because the BeastsOfBermuda.log file is missing!')
        return
    #Only the bot.log is missing, create a new one
    if not os.path.exists(BOT_LOG_PATH):
        print("Bot log file not found, creating a new one")
        open(BOT_LOG_PATH, 'a').close()

    with open(BEASTS_LOG_PATH, 'r', encoding='utf-8-sig') as file:
        lines = file.readlines()

    #Temp list to store matching lines
    temp_list = []

    for i in range(len(lines)):
        #Check if the line contains "PLAYER DEATH", any of the death reasons, and a number from 1 to 999 / Checking the conditions
        if "PLAYER DEATH" in lines[i] and any(reason in lines[i] for reason in DEATH_REASONS):
            print(f"Found 'PLAYER DEATH' and a death reason in line {i}")
            match = re.search(r'\b\d{1,3}\b', lines[i])
            if match:
                num = match.group()
                print(f"Found a number in line {i}: {num}")
                with open(BOT_LOG_PATH, 'r', encoding='utf-8-sig') as bot_log:
                    bot_log_content = bot_log.read()
                #Check if the entire death event entry does not exist in the Bot.log, then copy this line and the next also the next line after it
                for reason in DEATH_REASONS:
                    if reason in lines[i]:
                        event_id = re.sub(r'LogBlueprintUserMessages: \[ServerPlayerState_C_\d+\] ', '', lines[i]).strip()
                        print(f"Checking if '{event_id}' is in the bot log")
                        if event_id not in bot_log_content:
                            print(f"Didn't find '{event_id}' in the bot log, appending lines {i} and {i+1}")
                            line = re.sub(r'LogBlueprintUserMessages: \[ServerPlayerState_C_\d+\] ', '', lines[i])
                            line = re.sub(r'(Killing Player ID)(\d{17})', r'\1 \2', line)
                            temp_list.append(line)
                            #If the death reason is "You have fallen to your death.", only copy one line
                            if "You have fallen to your death." not in lines[i]:
                                line = re.sub(r'LogBlueprintUserMessages: \[ServerPlayerState_C_\d+\] ', '', lines[i+1])
                                line = re.sub(r'(Killing Player ID)(\d{17})', r'\1 \2', line)
                                temp_list.append(line)
                        else:
                            print(f"Found '{event_id}' in the bot log, not appending lines {i} and {i+1}")

    #Writing to Bot.log file and sending a messages to the discord deathlog channel
    with open(BOT_LOG_PATH, 'a', encoding='utf-8') as bot_log:
        channel = bot.get_channel(CHANNEL_ID)
        if temp_list:  #if temp_list is not empty
            for line in temp_list:
                print(f"Writing line to bot log and sending message: {line}")
                bot_log.write(line + '\n')
                await channel.send(line)
            await bot.change_presence(activity=nextcord.Game(name="Idle /checknow to check manually"), status=nextcord.Status.idle)        
            timestamped_print("Finished check_log_process")
            return True  #new deaths were found
        else:
            await bot.change_presence(activity=nextcord.Game(name="Idle /checknow to check manually"), status=nextcord.Status.idle)        
            timestamped_print("Finished check_log_process")
            return False  #no new deaths were found

#Command to check the log file manually
@bot.slash_command(guild_ids=[1129093489670500422])
async def checknow(interaction: nextcord.Interaction):
    print(f'{interaction.user} used the /checknow command.')
    #Check if the user has any of the allowed roles
    user_roles = [role.id for role in interaction.user.roles]
    if not any(role in user_roles for role in ALLOWED_ROLES):
        await interaction.response.send_message("You don't have the required role to run this command.", ephemeral=True, delete_after=30)
        return

    await interaction.response.send_message("DeathLogPrint Bot is processing the log file, please wait.", ephemeral=True, delete_after=30)
    new_deaths_found = await check_log_process()  
    if not new_deaths_found:
        await interaction.followup.send("No new deaths were found.", ephemeral=True, delete_after=30)

#Start the Checklog Process every hour
@tasks.loop(hours=1)
async def check_log():
    await check_log_process()

#Backup the Bot.log file every 7 days
def get_time_since_last_backup():
    try:
        with open(LAST_BACKUP_FILE, 'r') as f:
            last_backup_str = f.read().strip()
            if last_backup_str:  #Check if the string is not empty
                last_backup = datetime.fromisoformat(last_backup_str)
            else:
                raise ValueError("Invalid isoformat string: ''")
    except (FileNotFoundError, ValueError):  #Catch both FileNotFoundError and ValueError
        last_backup = datetime.now()
        with open(LAST_BACKUP_FILE, 'w') as f:
            f.write(last_backup.isoformat())
    return (datetime.now() - last_backup).total_seconds()

@tasks.loop(seconds=360)  #Check every hour
async def backup_log():
    if get_time_since_last_backup() >= 168 * 3600:
        #Write "Finish" to the end of the Bot.log file
        with open(BOT_LOG_PATH, 'a', encoding='utf-8') as bot_log:
            bot_log.write('Finish\n')
        #Rename the Bot.log file to Bot_Backup_YYYY-MM-DD.log
        now = datetime.now()
        date_string = now.strftime("%Y-%m-%d")
        new_log_path = f'Bot_Backup_{date_string}.log'
        os.rename(BOT_LOG_PATH, new_log_path)

        #Move the file to the backup folder
        shutil.move(new_log_path, os.path.join(BACKUP_FOLDER_PATH, new_log_path))

        #Create a new Bot.log file after the old one is moved
        open(BOT_LOG_PATH, 'a').close()

        #Send a message to the deathlog channel
        backup_channel = bot.get_channel(CHANNEL_ID)
        await backup_channel.send(f"Bot.log has been backed up as Bot_Backup_{date_string}.log.")

        #Write a timestamp to the last_backup.txt file
        with open(LAST_BACKUP_FILE, 'w') as f:
            f.write(datetime.now().isoformat())

#Cleanup old backups every day
@tasks.loop(hours=24)
async def cleanup_old_backups():
    now = datetime.now()
    two_months_ago = now - timedelta(days=60) #backup files older than 2 months will be deleted
    for filename in os.listdir(BACKUP_FOLDER_PATH):
        #Check if the file is a backup file
        if filename.startswith('Bot_Backup_'):
            #Extract the date from the filename
            date_str = filename.replace('Bot_Backup_', '').replace('.log', '')
            file_date = datetime.strptime(date_str, '%Y-%m-%d')
            #If the file is older than 2 months, delete it
            if file_date < two_months_ago:
                file_path = os.path.join(BACKUP_FOLDER_PATH, filename)
                os.remove(file_path)
                print(f"Deleted old backup file: {filename}")


bot.run(TOKEN)
