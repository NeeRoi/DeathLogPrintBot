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
Staff = 1132058617563070484 #Staff role for error notifications
Tech_Admin = 1132625409800929390 #Tech Admin role for error notifications
CHANNEL_ID = 1132681879854796841 #deathlog channel
CHANNEL_ID2 = 1133441575242961066 #localreceivedmessages channel

#Roles that are allowed to use the !checknow command
ALLOWED_ROLES = [1132625665175339008, 1129764708858200154, 1129764767628787742, 1129764624468807690] 

#Log paths
BEASTS_LOG_PATH = r'G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\BeastsOfBermuda.log' #Path to the BeastsOfBermuda.log file
BOT_LOG_PATH = r'G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\Bots\DeathLogPrint Bot\logs\Bot.log' #Path to the Bot.log file
BACKUP_FOLDER_PATH = r"G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\Bots\DeathLogPrint Bot\logs\backup" #Path to the backup folder
LAST_BACKUP_FILE = r'G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\Bots\DeathLogPrint Bot\logs\last_backup.txt' #Path to the last_backup.txt file
CHAT_LOG_PATH = r'G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\Bots\DeathLogPrint Bot\logs\Chat.log' #Path to the Chat.log file
LAST_CHAT_BACKUP_FILE = r'G:\Programme (x86)\Videotheke\Beastsofbermuda\Tech\Bots\DeathLogPrint Bot\logs\last_chat_backup.txt' #Path to the last_chat_backup.txt file

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

#Function to print a timestamp before and after every message
def timestamped_print(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

#Defines what is started when the bot is ready
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
       
    backup_logs.start()  #Start the task to backup the logs
    cleanup_old_backups.start()
    #Start the tasks to check the logs
    bot.loop.create_task(check_log_process())
    bot.loop.create_task(check_chat_process())

#Function to send large messages
async def send_large_message(channel, message):
    #add a zero-width space at the end to create an extra line in Discord
    message += '\u200B'
    while message:
        if len(message) <= 2000:
            if message.strip():  #check if the message is not empty or only contains whitespaces
                await channel.send(message)
            break
        else:
            idx = message.rfind('\n', 0, 1990)
            if idx == -1:
                idx = message.rfind(' ', 0, 1990)
            if idx == -1:
                idx = 1990
            await channel.send(message[:idx])
            message = message[idx:]

#Check the log file for new deaths
@tasks.loop(hours=1)
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
        #Temp list to store matching lines
        temp_list = []

        for i, line in enumerate(file):
            #Check if the line contains "PLAYER DEATH", any of the death reasons, and a number from 1 to 999 / Checking the conditions
            if "PLAYER DEATH" in line and any(reason in line for reason in DEATH_REASONS):
                print(f"Found 'PLAYER DEATH' and a death reason in line {i}")
                match = re.search(r'\b\d{1,3}\b', line)
                if match:
                    num = match.group()
                    print(f"Found a number in line {i}: {num}")
                    with open(BOT_LOG_PATH, 'r', encoding='utf-8-sig') as bot_log:
                        bot_log_content = bot_log.read()
                    #Check if the entire death event entry does not exist in the Bot.log, then copy this line and the next also the next line after it
                    for reason in DEATH_REASONS:
                        if reason in line:
                            event_id = re.sub(r'LogBlueprintUserMessages: \[ServerPlayerState_C_\d+\] ', '', line).strip()
                            print(f"Checking if '{event_id}' is in the bot log")
                            if event_id not in bot_log_content:
                                print(f"Didn't find '{event_id}' in the bot log, appending lines {i} and {i+1}")
                                line = re.sub(r'LogBlueprintUserMessages: \[ServerPlayerState_C_\d+\] ', '', line)
                                line = re.sub(r'(Killing Player ID)(\d{17})', r'\1 \2', line)
                                temp_list.append(line)
                                #If the death reason is "You have fallen to your death.", only copy one line
                                if "You have fallen to your death." not in line:
                                    line = re.sub(r'LogBlueprintUserMessages: \[ServerPlayerState_C_\d+\] ', '', line)
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
                await send_large_message(channel, line + '\n')  #Adding an extra line in the discord message
            await bot.change_presence(activity=nextcord.Game(name="Idle /checknow to check manually"), status=nextcord.Status.idle)        
            timestamped_print("Finished check_log_process")
            return True  #new deaths were found
        else:
            await bot.change_presence(activity=nextcord.Game(name="Idle /checknow to check manually"), status=nextcord.Status.idle)        
            timestamped_print("Finished check_log_process")
            return False  #no new deaths were found

#check the chat log file for new local messages and who received them
@tasks.loop(hours=1)      
async def check_chat_process():
    await bot.change_presence(activity=nextcord.Game(name="Looking for new local messages!"), status=nextcord.Status.online)
    timestamped_print("Starting check_chat_process")
    
    #Check if both files exist
    if not os.path.exists(BEASTS_LOG_PATH):
        print("BeastsOfBermuda.log file not found")
        channel = bot.get_channel(CHANNEL_ID2)
        staff_role = bot.get_guild(channel.guild.id).get_role(Tech_Admin)
        staff_role2 = bot.get_guild(channel.guild.id).get_role(Staff)
        #Sending message if the BeastsOfBermuda.log file is missing
        await channel.send(f'{staff_role2.mention} Tell {staff_role.mention} the DeathLogPrint Bot is broken because the BeastsOfBermuda.log file is missing!')
        return
    #Only the chat.log is missing, create a new one
    if not os.path.exists(CHAT_LOG_PATH):
        print("Chat log file not found, creating a new one")
        open(CHAT_LOG_PATH, 'a').close()

    with open(BEASTS_LOG_PATH, 'r', encoding='utf-8-sig') as file:
        lines = file.readlines()  #Convert the file into a list of lines
        #Temp list to store matching lines
        temp_list = []

        for i, line in enumerate(lines):
            #Check if the line contains "LogChat: Display: Received Local Dispatched Msg"
            if "LogChat: Display: Received Local Dispatched Msg" in line:
                print(f"Found 'LogChat: Display: Received Local Dispatched Msg' in line {i}")
                with open(CHAT_LOG_PATH, 'r', encoding='utf-8-sig') as chat_log:
                    chat_log_content = chat_log.read()
                #Check if the entire chat entry does not exist in the Chat.log, then copy this line and the next lines until an empty line
                chat_entry = line.strip()
                j = i + 1
                while j < len(lines) and lines[j].strip() != '':
                    chat_entry += '\n' + lines[j].strip()
                    j += 1
                #Append backticks to the sender and the message
                chat_entry = re.sub(r'- From: (.+?) \|', r'- From: `\1` |', chat_entry)
                chat_entry = re.sub(r'Msg: (.+)', r'Msg: `\1`', chat_entry)
                print(f"Checking if '{chat_entry}' is in the chat log")
                if chat_entry not in chat_log_content:
                    print(f"Didn't find '{chat_entry}' in the chat log, appending lines {i} to {j}")
                    temp_list.append(chat_entry)
                else:
                    print(f"Found '{chat_entry}' in the chat log, not appending lines {i} to {j}")

    #Writing to Chat.log file and sending messages to the discord chatlog channel
    with open(CHAT_LOG_PATH, 'a', encoding='utf-8') as chat_log:
        channel = bot.get_channel(CHANNEL_ID2)
        if temp_list:  #if temp_list is not empty
            for chat_entry in temp_list:
                print(f"Writing entry to chat log and sending message: {chat_entry}")
                chat_log.write(chat_entry + '\n\n')  #Add an extra line
                await send_large_message(channel, chat_entry + '\n\n')  #Add an extra line
            await bot.change_presence(activity=nextcord.Game(name="Idle /checknow to check manually"), status=nextcord.Status.idle)
            timestamped_print("Finished check_chat_process")
            return True  #new chat entries were found
        else:
            await bot.change_presence(activity=nextcord.Game(name="Idle /checknow to check manually"), status=nextcord.Status.idle)
            timestamped_print("Finished check_chat_process")
            return False  #no new chat entries were found

#Command to check the death log file manually
@bot.slash_command(guild_ids=[1129093489670500422])
async def checkdeathsnow(interaction: nextcord.Interaction):
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

#Command to check the chat log file manually
@bot.slash_command(guild_ids=[1129093489670500422])
async def checklocalnow(interaction: nextcord.Interaction):
    print(f'{interaction.user} used the /checknow command.')
    #Check if the user has any of the allowed roles
    user_roles = [role.id for role in interaction.user.roles]
    if not any(role in user_roles for role in ALLOWED_ROLES):
        await interaction.response.send_message("You don't have the required role to run this command.", ephemeral=True, delete_after=30)
        return

    await interaction.response.send_message("DeathLogPrint Bot is processing the log file, please wait.", ephemeral=True, delete_after=30)
    new_deaths_found = await check_chat_process()  
    if not new_deaths_found:
        await interaction.followup.send("No new local messages were found.", ephemeral=True, delete_after=30)

#Start the Checklog Process every hour
@tasks.loop(hours=1)
async def check_log():
    await check_log_process()
    await check_chat_process()

#Backup the Bot.log file every 7 days
def get_time_since_last_backup(backup_file):
    try:
        with open(backup_file, 'r') as f:
            last_backup = datetime.fromisoformat(f.read().strip())
    except FileNotFoundError:
        last_backup = datetime.now()
        with open(backup_file, 'w') as f:
            f.write(last_backup.isoformat())
    return (datetime.now() - last_backup).total_seconds()

async def backup_log(log_path, last_backup_file):
    if get_time_since_last_backup(last_backup_file) >= 168 * 3600:
        #Write "Finish" to the end of the log file
        with open(log_path, 'a', encoding='utf-8') as log:
            log.write('Finish\n')
        #Rename the log file to Log_Backup_YYYY-MM-DD.log
        now = datetime.now()
        date_string = now.strftime("%Y-%m-%d")
        file_name = os.path.basename(log_path)
        base_name, _ = os.path.splitext(file_name)
        new_log_path = f'{base_name}_Backup_{date_string}.log'
        os.rename(log_path, new_log_path)

        #Move the file to the backup folder
        shutil.move(new_log_path, os.path.join(BACKUP_FOLDER_PATH, new_log_path))

        #Create a new log file after the old one is moved
        open(log_path, 'a').close()

        #Send a message to the deathlog channel
        backup_channel = bot.get_channel(CHANNEL_ID)
        await backup_channel.send(f"{file_name} has been backed up as {new_log_path}.")

        #Write a timestamp to the last_backup.txt file
        with open(last_backup_file, 'w') as f:
            f.write(datetime.now().isoformat())

@tasks.loop(seconds=360)  #Check every hour
async def backup_logs():
    await backup_log(BOT_LOG_PATH, LAST_BACKUP_FILE)
    await backup_log(CHAT_LOG_PATH, LAST_CHAT_BACKUP_FILE)


#Cleanup old backups every day
@tasks.loop(hours=24)
async def cleanup_old_backups():
    now = datetime.now()
    two_months_ago = now - timedelta(days=60) #backup files older than 2 months will be deleted
    for filename in os.listdir(BACKUP_FOLDER_PATH):
        #Check if the file is a backup file
        if filename.startswith('Bot_Backup_') or filename.startswith('Chat_Backup_'):  #This will consider both Bot_Backup and Chat_Backup files
            #Extract the date from the filename
            date_str = filename.split('_')[-1].split(' ')[0].replace('.log', '')  #Split on space and pick the first part
            file_date = datetime.strptime(date_str, '%Y-%m-%d')
            #If the file is older than 2 months, delete it
            if file_date < two_months_ago:
                file_path = os.path.join(BACKUP_FOLDER_PATH, filename)
                os.remove(file_path)
                print(f"Deleted old backup file: {filename}")


bot.run(TOKEN)
