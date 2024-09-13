import disnake
from disnake.ext import commands, tasks
import requests
import random
from flask import Flask
from threading import Thread
import os

intents = disnake.Intents.all()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)

staff_status_message = None
channel_id = 1283104286271864913
role_name = "📂〢Staff"
QUESTION_CHANNEL = "❔〃question-du-jour"
GUILD_NAME = "La Taverne 🍻"

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}.")
    await bot.change_presence(
        status=disnake.Status.online,
        activity=disnake.Activity(
            type=disnake.ActivityType.streaming,
            name=".gg/lataverne & created by Mxtsouko",
            url='https://www.twitch.tv/mxtsouko'
        )
    )
    send_random_question.start()
    remind_bumping.start()
    update_staff_status.start()
    check_status.start()
    load_animes()
    
    if not anime_vote_task.is_running():
        anime_vote_task.start()

@tasks.loop(hours=2)
async def remind_bumping():
    for guild in bot.guilds:
        channel = disnake.utils.get(guild.text_channels, name='🌊〃bump')
        role = disnake.utils.get(guild.roles, name='🌊〢Ping Bumping')
        if channel and role:
            embed = disnake.Embed(
                title="Rappel de Bump",
                description="Il est temps de bump le serveur !",
                color=0xFF5733
            )
            await channel.send(content=role.mention, embed=embed)

@tasks.loop(minutes=3)
async def update_staff_status():
    global staff_status_message  
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    guild = channel.guild
    role = disnake.utils.get(guild.roles, name=role_name)
    if not role:
        return

    statuses = {"online": [], "idle": [], "dnd": [], "offline": []}

    for member in guild.members:
        if role in member.roles:
            if member.status == disnake.Status.online:
                statuses["online"].append(member.mention)
            elif member.status == disnake.Status.idle:
                statuses["idle"].append(member.mention)
            elif member.status == disnake.Status.dnd:
                statuses["dnd"].append(member.mention)
            else:
                statuses["offline"].append(member.mention)

    embed = disnake.Embed(
        title="Statut du Staff",
        color=0x00ff00,
        description="Voici les statuts actuels des membres du staff."
    )
    embed.add_field(name="`🟢` **En ligne**", value='\n'.join(statuses["online"]) or "Aucun", inline=False)
    embed.add_field(name="`🌙` **Inactif**", value='\n'.join(statuses["idle"]) or "Aucun", inline=False)
    embed.add_field(name="`⛔` **Ne pas déranger**", value='\n'.join(statuses["dnd"]) or "Aucun", inline=False)
    embed.add_field(name="`⚫` **Hors ligne**", value='\n'.join(statuses["offline"]) or "Aucun", inline=False)

    if staff_status_message is None:
        staff_status_message = await channel.send(embed=embed)
    else:
        await staff_status_message.edit(embed=embed)

@update_staff_status.before_loop
async def before_update_staff_status():
    await bot.wait_until_ready()

@tasks.loop(seconds=20)
async def check_status():
    for guild in bot.guilds:
        role = disnake.utils.get(guild.roles, name='🦾〢Soutient Bio')
        if not role:
            print(f"Rôle '🦾〢Soutient Bio' non trouvé dans {guild.name}.")
            continue

        for member in guild.members:
            if member.bot or member.status == disnake.Status.offline:
                continue

            has_custom_status = any(
                activity.type == disnake.ActivityType.custom and activity.state and '/Taverne' in activity.state
                for activity in member.activities
            )

            if has_custom_status and role not in member.roles:
                await member.add_roles(role)
                print(f'Rôle ajouté à {member.display_name} dans {guild.name}')
            elif not has_custom_status and role in member.roles:
                await member.remove_roles(role)
                print(f'Rôle retiré de {member.display_name} dans {guild.name}')

def load_questions():
    global questions
    try:
        response = requests.get('https://raw.githubusercontent.com/Mxtsouko-off/Misaki/main/Json/question.json')
        if response.status_code == 200:
            data = response.json()
            questions = [item['question'] for item in data]
            print(f"{len(questions)} questions chargées.")
        else:
            print(f"Erreur lors du chargement des questions: {response.status_code}")
    except Exception as e:
        print(f"Une erreur s'est produite lors du chargement des questions: {e}")

load_questions()

@tasks.loop(hours=5)
async def send_random_question():
    guild = disnake.utils.get(bot.guilds, name=GUILD_NAME)
    channel = disnake.utils.get(guild.text_channels, name=QUESTION_CHANNEL)
    role = disnake.utils.get(channel.guild.roles, name="❔〢Ping Question !")

    if channel and role:
        try:
            await channel.purge(limit=100) 
        except Exception as e:
            print(f"Erreur lors de la purge des messages: {e}")

        if questions:  
            question = random.choice(questions)
            embed = disnake.Embed(
                title="Question du jour",
                description=question,
                color=0x00ff00
            )
            embed.add_field(name='Répondez dans :', value='https://discord.com/channels/1251476405112537148/1269373203650973726')
            await channel.send(content=role.mention, embed=embed)

def load_animes():
    global anime_list
    try:
        response = requests.get('https://raw.githubusercontent.com/Mxtsouko-off/Misaki/main/Json/anime.json')
        if response.status_code == 200:
            anime_list = response.json()
            print(f"{len(anime_list)} animes chargés.")
        else:
            print(f"Erreur lors du chargement des animes: {response.status_code}")
    except Exception as e:
        print(f"Une erreur s'est produite lors du chargement des animes: {e}")

def get_anime_image(anime_name):
    url = f"https://api.jikan.moe/v4/anime?q={anime_name}&limit=1"
    response = requests.get(url)
    data = response.json()
    if data['data']:
        return data['data'][0]['images']['jpg']['large_image_url']
    return None

@tasks.loop(hours=4)
async def anime_vote_task():
    global global_anime_name, global_anime_link, accept_count, pass_count

    guild = disnake.utils.get(bot.guilds, name="La Taverne 🍻")
    channel = disnake.utils.get(guild.text_channels, name="💐〃anime-vote")
    if not channel:
        print("Canal non trouvé.")
        return

    total_count = accept_count + pass_count
    if total_count > 0:
        accept_percentage = (accept_count / total_count) * 100
        pass_percentage = (pass_count / total_count) * 100
        results_embed = disnake.Embed(
            title="Résultats du vote anime",
            description=f"**Accepté**: {accept_percentage:.2f}%\n**Passé**: {pass_percentage:.2f}%",
            color=0x00ff00
        )
        await channel.send(embed=results_embed)

    accept_count = 0
    pass_count = 0

    if not anime_list:
        print("La liste des animes est vide.")
        return

    anime = random.choice(anime_list)
    global_anime_name = anime["name"]
    global_anime_link = anime["link"]
    image_url = get_anime_image(global_anime_name)

    role = disnake.utils.get(channel.guild.roles, name='🚀〢Ping Anime vote')
    if image_url:
        embed = disnake.Embed(
            title="Vote pour l'anime",
            description=f"Proposition d'anime : {global_anime_name}\n{global_anime_link}"
        )
        embed.set_image(url=image_url)

        view = disnake.ui.View()
        view.add_item(disnake.ui.Button(label="Accepter", style=disnake.ButtonStyle.success, custom_id="accept"))
        view.add_item(disnake.ui.Button(label="Passer", style=disnake.ButtonStyle.danger, custom_id="pass"))

        await channel.send(content=role.mention, embed=embed, view=view)
    else:
        await channel.send(content=f"Je n'ai pas pu trouver une image pour l'anime '{global_anime_name}'.")

@anime_vote_task.before_loop
async def before_anime_vote_task():
    await bot.wait_until_ready()

@bot.event
async def on_interaction(interaction: disnake.Interaction):
    global accept_count, pass_count, global_anime_name, global_anime_link

    if interaction.type == disnake.InteractionType.component:
        custom_id = interaction.data.get("custom_id")
        if custom_id == "accept":
            accept_count += 1
            await interaction.response.send_message(f"Vous avez accepté l'anime '{global_anime_name}'. Vous pouvez le voir ici : {global_anime_link}", ephemeral=True)
        elif custom_id == "pass":
            pass_count += 1
            await interaction.response.send_message(f"Vous avez passé l'anime '{global_anime_name}'.", ephemeral=True)

app = Flask('')

@app.route('/')
def main():
    return f"Logged in as {bot.user}."

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    server = Thread(target=run)
    server.start()

keep_alive()

bot.run(os.getenv('TOKEN'))
