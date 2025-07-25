import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_TOKEN = os.getenv('GEMINI_TOKEN')
GEMINI_PROMPT = os.getenv('GEMINI_PROMPT')
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
ROLE_CHANNEL_ID = int(os.getenv('ROLE_CHANNEL_ID'))
ROLE_ID = int(os.getenv('ROLE_ID'))

genai.configure(api_key=GEMINI_TOKEN)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')
gemini_chat = gemini_model.start_chat(history=[])

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)

role_message_id = None

@bot.event
async def on_ready():
    print(f'登入身份: {bot.user}')
    await setup_role_message()
    await bot.tree.sync()

async def setup_role_message():
    global role_message_id
    channel = bot.get_channel(ROLE_CHANNEL_ID)
    
    async for message in channel.history(limit=100):
        if message.author == bot.user and '👥' in message.content:
            role_message_id = message.id
            print(f"找到現有身分組訊息: {role_message_id}")
            return
    
    msg = await channel.send("請點擊下方 👥 表情領取成員身分組！")
    await msg.add_reaction('👥')
    role_message_id = msg.id
    print(f"已發送新身分組訊息: {role_message_id}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id != role_message_id or str(payload.emoji) != '👥':
        return
    
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    role = guild.get_role(ROLE_ID)
    
    if member.bot:
        return
    
    await member.add_roles(role)
    print(f"已給予 {member} 身分組: {role.name}")

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != role_message_id or str(payload.emoji) != '👥':
        return
    
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    role = guild.get_role(ROLE_ID)
    
    await member.remove_roles(role)
    print(f"已移除 {member} 的身分組: {role.name}")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    
    human_members = sum(not m.bot for m in member.guild.members)
    
    welcome_msg = (
        f"你好 <@{member.id}> 歡迎加入！\n"
        f"std_dllms\n"
        f"你是第【{human_members}】位加入的成員\n"
        "請你領取身分組及細閱規則！\n"
        "使用`/chat`可以跟stddllm聊天"
    )
    
    await channel.send(welcome_msg)

@bot.tree.command(name="chat", description="與stddllm聊天")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()  
    
    try:
        response = gemini_chat.send_message(
            f"{GEMINI_PROMPT}\n使用者提問: {message}",
            safety_settings={
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
            }
        )
        
        text = response.text[:1900] if len(response.text) > 1900 else response.text
        await interaction.followup.send(f"stddllms:\n{text}")
    except Exception as e:
        await interaction.followup.send(f"錯誤: {str(e)}")

if __name__ == "__main__":
    bot.run(TOKEN)
