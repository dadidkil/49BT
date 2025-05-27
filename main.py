import discord
from discord.ext import commands
import random
import string
from discord import ui, ButtonStyle, Embed, PermissionOverwrite
import os
from dotenv import load_dotenv
from discord.ui import Button, View
import asyncio
from discord import app_commands
import config_utils
import logging
from typing import Optional, Dict, Set
import json
import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Загрузка конфигурации
config = config_utils.load_config()

# Загрузка токена из .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("Токен Discord не найден. Создайте файл .env с DISCORD_TOKEN=ваш_токен")

# Настройки для бота
intents = discord.Intents.all()
intents.members = True
intents.message_content = True

recent_welcomes: Set[int] = set()
private_vc_owners: Dict[int, int] = {}

class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.voice")
        await self.load_extension("cogs.mod_applications")
        await self.load_extension("cogs.server_logs")
        logging.info("Коги загружены и команды синхронизированы")

bot = MyBot(command_prefix='!', intents=intents)

# ID каналов и ролей (заполняются из config)
VERIFICATION_CHANNEL_ID = config.get("verification_channel", 0)
MEMBER_ROLE_ID = config.get("member_role", 0)
WELCOME_CHANNEL_ID = config.get("welcome_channel", 0)
INFO_CHANNEL_ID = config.get("info_channel", 0)
TICKET_CHANNEL_ID = config.get("ticket_channel", 0)
TICKET_CATEGORY_ID = config.get("ticket_category", 0)
TICKET_MOD_ROLE_ID = config.get("ticket_mod_role", 0)
GUILD_ID = config.get("guild_id", 0)
PRIVATE_VC_CATEGORY_ID = config.get("private_vc_category", 0)
PRIVATE_VC_LOBBY_ID = config.get("private_vc_lobby", 0)

# Баннеры и цвета
ASSETS_PATH = "assets"
WELCOME_BANNER_FILENAME = config.get("welcome_banner_filename", "welcome.gif")
LINKS_BANNER_FILENAME = config.get("links_banner_filename", "links.gif")
MODS_BANNER_FILENAME = config.get("mods_banner_filename", "mods.gif")
INVITE_BANNER_FILENAME = config.get("invite_banner_filename", "invite.gif")
BANNER_URL = config.get("banner_url_default", "")
GENTLE_PINK_COLOR = discord.Color(int(config.get("gentle_pink_color_hex", "#FFB6C1").replace("#", ""), 16))

# --- Верификация ---
class CaptchaModal(ui.Modal, title='Верификация'):
    def __init__(self, captcha_text: str):
        super().__init__()
        self.captcha_text = captcha_text
        self.captcha_input = ui.TextInput(
            label=f"Введите текст с капчи: {captcha_text}", 
            placeholder="Введите символы здесь...",
            required=True,
            max_length=10
        )
        self.add_item(self.captcha_input)
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.captcha_input.value.strip() == self.captcha_text:
                member = interaction.user
                role = interaction.guild.get_role(MEMBER_ROLE_ID)
                if role:
                    await member.add_roles(role)
                    embed = Embed(
                        title="Успешная верификация!",
                        description="Вы успешно прошли верификацию и получили роль участника.",
                        color=discord.Color.green()
                    )
                    if BANNER_URL:
                        embed.set_image(url=BANNER_URL)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    logging.info(f"Пользователь {member.name} успешно прошел верификацию")
                else:
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="❌ Ошибка",
                            description="Роль участника не найдена. Обратитесь к администратору.",
                            color=discord.Color.red()
                        ), ephemeral=True
                    )
                    logging.error(f"Роль участника не найдена для пользователя {member.name}")
            else:
                await interaction.response.send_message(
                    "Неверный код с капчи. Попробуйте еще раз.", ephemeral=True
                )
                logging.info(f"Неверная капча от пользователя {interaction.user.name}")
        except Exception as e:
            logging.error(f"Ошибка при верификации: {e}")
            await interaction.response.send_message(
                "Произошла ошибка при верификации. Попробуйте позже.", ephemeral=True
            )

class VerifyButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Пройти верификацию", style=ButtonStyle.primary, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        try:
            captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            await interaction.response.send_modal(CaptchaModal(captcha_text))
        except Exception as e:
            logging.error(f"Ошибка при создании капчи: {e}")
            await interaction.response.send_message(
                "Произошла ошибка. Попробуйте позже.", ephemeral=True
            )

@bot.event
async def on_ready():
    try:
        logging.info(f'Бот {bot.user} запущен и готов к работе!')
        bot.add_view(VerifyButton())
        if VERIFICATION_CHANNEL_ID:
            channel = bot.get_channel(VERIFICATION_CHANNEL_ID)
            if channel:
                async for message in channel.history(limit=10):
                    if message.author == bot.user and message.components:
                        break
                else:
                    embed = Embed(
                        title="Верификация",
                        description="Для доступа к серверу нажмите на кнопку ниже и пройдите проверку.",
                        color=discord.Color.purple()
                    )
                    embed.set_footer(text="Система верификации сервера")
                    if BANNER_URL:
                        embed.set_image(url=BANNER_URL)
                    await channel.send(embed=embed, view=VerifyButton())
                    logging.info("Сообщение верификации отправлено")
        await send_project_info_messages(INFO_CHANNEL_ID)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")

@bot.event
async def on_member_join(member):
    try:
        if member.id in recent_welcomes:
            return
        recent_welcomes.add(member.id)
        asyncio.create_task(remove_from_cache(member.id))
        welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel:
            embed = Embed(
                title="🎉 Добро пожаловать на сервер!",
                description=(
                    f"Привет, {member.mention}!\n\n"
                    "Пожалуйста, ознакомься с правилами и пройди верификацию, "
                    f"чтобы получить доступ к серверу.\n"
                    f"Верификация доступна в <#{VERIFICATION_CHANNEL_ID}>."
                ),
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="49 Battalion | Discord Server")
            if BANNER_URL:
                embed.set_image(url=BANNER_URL)
            await welcome_channel.send(embed=embed)
            logging.info(f"Отправлено приветствие для {member.name}")
    except Exception as e:
        logging.error(f"Ошибка при обработке нового участника: {e}")

async def remove_from_cache(user_id: int):
    await asyncio.sleep(120)
    recent_welcomes.discard(user_id)

# --- Информационные сообщения ---
async def send_project_info_messages(channel_id: int):
    channel = bot.get_channel(channel_id)
    if not channel:
        logging.error(f"Канал с ID {channel_id} не найден для отправки информационных сообщений.")
        return
    async for message in channel.history(limit=10):
        if message.author == bot.user and message.embeds:
            if message.embeds[0].title and message.embeds[0].title == "Добро пожаловать на 49 Battalion! 👋":
                logging.info("Информационные сообщения (Welcome часть) уже были отправлены.")
                return
    # --- Welcome ---
    try:
        welcome_description = (
            "Привет и теплое приветствие всем нашим новым участникам! 🌟 Мы очень рады, что вы присоединились к нашему сообществу ❤️\n\n"
            "🤝 Пожалуйста, найдите время, чтобы представиться сообществу – расскажите немного о себе, своих интересах и о том, что привело вас сюда.\n\n"
            "📜 Прежде чем приступить к работе, пожалуйста, найдите минутку, чтобы ознакомиться с правилами нашего сервера. Мы хотим, чтобы все отлично провели здесь время, и следование рекомендациям помогает создать благоприятную атмосферу для всех.\n\n"
            "Мы рады видеть вас здесь, и нам не терпится познакомиться с вами поближе.\n"
            "Приятного вам пребывания! 🎉"
        )
        welcome_embed = Embed(
            title="Добро пожаловать на 49 Battalion! 👋",
            description=welcome_description,
            color=GENTLE_PINK_COLOR 
        )
        welcome_banner_path = os.path.join(ASSETS_PATH, WELCOME_BANNER_FILENAME)
        if os.path.exists(welcome_banner_path):
            file = discord.File(welcome_banner_path, filename=WELCOME_BANNER_FILENAME)
            welcome_embed.set_image(url=f"attachment://{WELCOME_BANNER_FILENAME}")
            await channel.send(file=file, embed=welcome_embed)
        else:
            logging.warning(f"Файл баннера {WELCOME_BANNER_FILENAME} не найден в assets. Отправка эмбеда без картинки.")
            await channel.send(embed=welcome_embed)
        await asyncio.sleep(2)
    except Exception as e:
        logging.error(f"Ошибка при отправке Welcome блока: {e}")
    # --- Links ---
    try:
        links_description = (
            "По дополнительным вопросам, не стесняйтесь обращаться к нам.\n\n"
            "**Socials & Проекты:**\n"
            "YouTube Rivoas: [Перейти](https://www.youtube.com/@Rivoas) 🤩\n"
            "Twitch yadinozaur: [Перейти](https://www.twitch.tv/yadinozavr) 🥰\n"
            "Наш CS2 Паблик: [cs2-nightmare.ru](https://cs2-nightmare.ru/) 🎮\n"
            "Наш Discord: [Присоединяйся!](https://discord.gg/49BT) 💬"
        )
        links_embed = Embed(
            description=links_description,
            color=GENTLE_PINK_COLOR
        )
        links_banner_path = os.path.join(ASSETS_PATH, LINKS_BANNER_FILENAME)
        if os.path.exists(links_banner_path):
            file = discord.File(links_banner_path, filename=LINKS_BANNER_FILENAME)
            links_embed.set_image(url=f"attachment://{LINKS_BANNER_FILENAME}")
            await channel.send(file=file, embed=links_embed)
        else:
            logging.warning(f"Файл баннера {LINKS_BANNER_FILENAME} не найден в assets. Отправка эмбеда без картинки.")
            await channel.send(embed=links_embed)
        await asyncio.sleep(2)
    except Exception as e:
        logging.error(f"Ошибка при отправке Links блока: {e}")
    # --- Mods ---
    try:
        mods_description = (
            "Наша команда модераторов здесь для того, чтобы убедиться, что этот уютный маленький уголок Discord остается теплым и безопасным для всех. ✅\n\n"
            "Если вы когда-нибудь столкнетесь с какими-либо проблемами, связанными с нашим сервером, не стесняйтесь писать тикеты. ❤️\n\n"
            "Краткое предупреждение: Команда модераторов не будет решать проблемы между участниками. Если те не нарушили правила проекта.\n\n"
            "Если у вас возникнут какие-либо проблемы, лучше всего сообщить об этом напрямую в службу доверия и безопасности Discord и заблокировать пользователя."
        )
        mods_embed = Embed(
            description=mods_description,
            color=GENTLE_PINK_COLOR
        )
        mods_banner_path = os.path.join(ASSETS_PATH, MODS_BANNER_FILENAME)
        if os.path.exists(mods_banner_path):
            file = discord.File(mods_banner_path, filename=MODS_BANNER_FILENAME)
            mods_embed.set_image(url=f"attachment://{MODS_BANNER_FILENAME}")
            await channel.send(file=file, embed=mods_embed)
        else:
            logging.warning(f"Файл баннера {MODS_BANNER_FILENAME} не найден в assets. Отправка эмбеда без картинки.")
            await channel.send(embed=mods_embed)
        await asyncio.sleep(2)
    except Exception as e:
        logging.error(f"Ошибка при отправке Mods блока: {e}")
    # --- Invite ---
    try:
        invite_description = (
            "Поделитесь своей любовью, поделившись ссылкой для приглашения на наш сервер. 🤝\n\n"
            "https://discord.gg/49BT"
        )
        invite_embed = Embed(
            description=invite_description,
            color=GENTLE_PINK_COLOR
        )
        invite_banner_path = os.path.join(ASSETS_PATH, INVITE_BANNER_FILENAME)
        if os.path.exists(invite_banner_path):
            file = discord.File(invite_banner_path, filename=INVITE_BANNER_FILENAME)
            invite_embed.set_image(url=f"attachment://{INVITE_BANNER_FILENAME}")
            await channel.send(file=file, embed=invite_embed)
        else:
            logging.warning(f"Файл баннера {INVITE_BANNER_FILENAME} не найден в assets. Отправка эмбеда без картинки.")
            await channel.send(embed=invite_embed)
        logging.info("Все информационные сообщения успешно отправлены.")
    except Exception as e:
        logging.error(f"Ошибка при отправке Invite Link блока: {e}")

@bot.tree.command(name="rules", description="Показать правила сервера красиво и минималистично")
async def rules(interaction: discord.Interaction):
    rules_text = (
        "\n"
        "**1. Уважайте друг друга**\n"
        "> Не допускается токсичность, оскорбления, дискриминация.\n\n"
        "**2. NSFW и 18+**\n"
        " > Только в специально отведённых каналах.\n\n"
        "**3. Спам и реклама**\n"
        " > Запрещены без разрешения администрации.\n\n"
        "**4. Запрещённый контент**\n"
        " > Любой нелегальный, вредоносный или шокирующий контент — бан.\n\n"
        "**5. Слушайте модераторов**\n"
        " > Их слово — финальное.\n\n"
        "**6. Личные данные**\n"
        " > Не публикуйте свои и чужие личные данные.\n\n"
        "**7. Никнеймы и аватары**\n"
        " > Без провокаций, NSFW и оскорблений.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "\n:lotus:  **Соблюдайте эти простые правила — и атмосфера на сервере будет уютной для всех!**\n\n"
        "*За нарушение — предупреждение или бан без предупреждения.*"
    )
    embed = discord.Embed(
        title="📜 Правила сервера 49 Battalion",
        description=rules_text,
        color=GENTLE_PINK_COLOR
    )
    embed.set_footer(text="49 Battalion | Правила")
    if BANNER_URL:
        embed.set_image(url=BANNER_URL)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@commands.Cog.listener()
async def on_voice_state_update(self, member, before, after):
    guild = member.guild
    embed = None
    initiator = None
    # Перемещение другим участником
    if before.channel and after.channel and before.channel != after.channel:
        await asyncio.sleep(1.5)  # Дать Discord время записать audit log
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_move):
            if entry.target and entry.target.id == member.id and entry.created_at > datetime.datetime.utcnow() - datetime.timedelta(seconds=10):
                initiator = entry.user
                break
        embed = discord.Embed(
            title="🔄 Перемещение между голосовыми каналами",
            description=f"{member.mention} ({member}) перемещён из {before.channel.mention} в {after.channel.mention}",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        if initiator:
            embed.add_field(name="Кто переместил", value=f"{initiator.mention} ({initiator})", inline=False)
        else:
            embed.add_field(name="Кто переместил", value="Сам пользователь или не удалось определить", inline=False)
    # ... остальной код ...

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        logging.error(f"Критическая ошибка при запуске бота: {e}") 