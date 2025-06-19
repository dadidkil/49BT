import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import datetime

# Загрузка переменных окружения
load_dotenv()

# Проверка наличия токена
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("Не найден токен Discord. Убедитесь, что файл .env содержит DISCORD_TOKEN.")

# Настройка интентов
intents = discord.Intents.default()
intents.members = True
# Проверка наличия атрибута message_content (добавлен в discord.py 2.0+)
if hasattr(intents, 'message_content'):
    intents.message_content = True
intents.voice_states = True

# Создание бота
bot = commands.Bot(command_prefix='!', intents=intents)

# ID каналов и ролей
MEMBER_COUNT_CHANNEL = 1375890394726006856
BOT_COUNT_CHANNEL = 1375890398739828797
WELCOME_CHANNEL = 1374767126912565258
VERIFICATION_CHANNEL = 1374748463337836697
VERIFIED_ROLE = 1374752253646475284
VOICE_CREATE_CHANNEL = 1375913894312415303
PRIVATE_VOICE_CREATE_CHANNEL = 1385371353867358370
VOICE_CATEGORY = 1369754090095251488
PRIVATE_VOICE_CATEGORY = 1375193403603681290

# Форматы названий каналов
MEMBER_COUNT_FORMAT = "╭👥・участников: {}"
BOT_COUNT_FORMAT = "╰🤖・ботов: {}"
VOICE_CHANNEL_FORMAT = "🔊ㆍVC {}"
PRIVATE_VOICE_CHANNEL_FORMAT = "🔊ㆍPVC {}"

# Цвета для эмбедов
MAIN_COLOR = 0x2F3136  # Темно-серый цвет Discord
SUCCESS_COLOR = 0x57F287  # Зеленый
WARNING_COLOR = 0xFEE75C  # Желтый
ERROR_COLOR = 0xED4245  # Красный

# Словарь для хранения временных голосовых каналов
temp_channels = {}
# Хранение ID сообщения с кнопкой верификации
verification_message_id = None

@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')
    try:
        update_member_count.start()
        await check_verification_message()
    except RuntimeError:
        # Если задача уже запущена
        pass

async def check_verification_message():
    """Проверка наличия сообщения с кнопкой верификации"""
    global verification_message_id
    
    try:
        verification_channel = bot.get_channel(VERIFICATION_CHANNEL)
        if not verification_channel:
            return
            
        # Проверка последних сообщений в канале
        async for message in verification_channel.history(limit=10):
            if message.author == bot.user and message.embeds and message.embeds[0].title == "Верификация на сервере":
                verification_message_id = message.id
                return
                
        # Если сообщение не найдено, отправляем новое
        await send_verification_message(verification_channel)
    except Exception as e:
        print(f"Ошибка при проверке сообщения верификации: {e}")

async def send_verification_message(channel):
    """Отправка сообщения с кнопкой верификации"""
    global verification_message_id
    
    try:
        # Создаем эмбед для верификации
        embed = discord.Embed(
            title="Верификация на сервере",
            description="Добро пожаловать на сервер **49 Battalion**!\n\n"
                        "Для получения доступа к основным каналам сервера, пожалуйста, пройдите верификацию, "
                        "нажав на кнопку ниже.",
            color=MAIN_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url="https://i.imgur.com/6YToyEF.png")  # Иконка сервера или другое изображение
        embed.add_field(name="Преимущества верификации", value="✅ Доступ ко всем каналам\n✅ Возможность общаться с участниками\n✅ Доступ к голосовым каналам", inline=False)
        embed.set_footer(text="49 Battalion • Система верификации", icon_url="https://i.imgur.com/6YToyEF.png")
        
        # Создаем кнопку верификации
        verify_button = discord.ui.Button(style=discord.ButtonStyle.green, label="Пройти верификацию", custom_id="verify_button", emoji="✅")
        view = discord.ui.View(timeout=None)
        view.add_item(verify_button)
        
        # Отправляем сообщение с кнопкой
        message = await channel.send(embed=embed, view=view)
        verification_message_id = message.id
    except Exception as e:
        print(f"Ошибка при отправке сообщения верификации: {e}")

@tasks.loop(minutes=5)
async def update_member_count():
    """Обновление количества участников и ботов в названиях каналов"""
    if not bot.guilds:
        return
    
    guild = bot.guilds[0]
    if not guild:
        return

    try:
        # Подсчет участников и ботов
        member_count = len([m for m in guild.members if not m.bot])
        bot_count = len([m for m in guild.members if m.bot])

        # Обновление названий каналов
        member_channel = guild.get_channel(MEMBER_COUNT_CHANNEL)
        bot_channel = guild.get_channel(BOT_COUNT_CHANNEL)

        if member_channel:
            await member_channel.edit(name=MEMBER_COUNT_FORMAT.format(member_count))
        if bot_channel:
            await bot_channel.edit(name=BOT_COUNT_FORMAT.format(bot_count))
    except discord.HTTPException as e:
        print(f"Ошибка при обновлении каналов: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")

@bot.event
async def on_member_join(member):
    """Приветствие новых участников"""
    try:
        welcome_channel = member.guild.get_channel(WELCOME_CHANNEL)
        if welcome_channel:
            # Создаем эмбед для приветствия
            embed = discord.Embed(
                title=f"Добро пожаловать на сервер 49 Battalion!",
                description=f"Привет, {member.mention}! Мы рады видеть тебя на нашем сервере!\n\n"
                            f"Пожалуйста, пройди верификацию в канале <#{VERIFICATION_CHANNEL}>, "
                            f"чтобы получить доступ ко всем каналам.",
                color=MAIN_COLOR,
                timestamp=datetime.datetime.now()
            )
            
            # Добавляем аватар пользователя
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Добавляем информацию о сервере
            embed.add_field(name="📜 Правила", value="Ознакомьтесь с правилами сервера, чтобы избежать недоразумений.", inline=True)
            embed.add_field(name="🎮 Развлечения", value="У нас есть множество каналов для общения и игр.", inline=True)
            embed.add_field(name="🔊 Голосовые каналы", value="Заходи в голосовые каналы, чтобы пообщаться с другими участниками.", inline=True)
            
            # Добавляем информацию о пользователе
            member_since = int(member.created_at.timestamp())
            embed.add_field(name="Аккаунт создан", value=f"<t:{member_since}:R>", inline=True)
            
            # Добавляем счетчик участников
            embed.set_footer(text=f"Участник #{len([m for m in member.guild.members if not m.bot])} • 49 Battalion", icon_url="https://i.imgur.com/6YToyEF.png")
            
            await welcome_channel.send(embed=embed)
    except Exception as e:
        print(f"Ошибка при отправке приветствия: {e}")

@bot.event
async def on_message(message):
    """Обработка сообщений для верификации"""
    try:
        if message.channel.id == VERIFICATION_CHANNEL and not message.author.bot:
            # Здесь можно добавить более сложную логику верификации
            # Сейчас просто выдаем роль при любом сообщении
            verified_role = message.guild.get_role(VERIFIED_ROLE)
            if verified_role:
                await message.author.add_roles(verified_role)
                
                # Создаем эмбед для подтверждения верификации
                embed = discord.Embed(
                    title="Верификация пройдена!",
                    description=f"{message.author.mention}, вы успешно прошли верификацию на сервере!",
                    color=SUCCESS_COLOR,
                    timestamp=datetime.datetime.now()
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                embed.set_footer(text="49 Battalion • Система верификации", icon_url="https://i.imgur.com/6YToyEF.png")
                
                await message.channel.send(embed=embed)
    except Exception as e:
        print(f"Ошибка при верификации: {e}")
    
    await bot.process_commands(message)

@bot.event
async def on_interaction(interaction):
    """Обработка взаимодействий (кнопки, меню и т.д.)"""
    try:
        if interaction.data.get("custom_id") == "verify_button":
            # Выдаем роль при нажатии на кнопку верификации
            verified_role = interaction.guild.get_role(VERIFIED_ROLE)
            if verified_role:
                await interaction.user.add_roles(verified_role)
                
                # Создаем эмбед для подтверждения верификации
                embed = discord.Embed(
                    title="Верификация пройдена!",
                    description=f"Вы успешно прошли верификацию на сервере!\nТеперь у вас есть доступ ко всем каналам.",
                    color=SUCCESS_COLOR,
                    timestamp=datetime.datetime.now()
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                embed.set_footer(text="49 Battalion • Система верификации", icon_url="https://i.imgur.com/6YToyEF.png")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        print(f"Ошибка при обработке взаимодействия: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    """Обработка голосовых каналов"""
    try:
        # Пользователь вышел из канала
        if before.channel and not after.channel:
            # Проверяем, был ли это временный канал
            if before.channel.id in temp_channels:
                # Если канал пустой, удаляем его
                if len(before.channel.members) == 0:
                    await before.channel.delete()
            
            # Проверка и удаление пустых временных каналов
            await cleanup_empty_channels(member.guild)
            await reorder_voice_channels(member.guild)
            return
        
        # Пользователь переместился между каналами
        if before.channel and after.channel and before.channel.id != after.channel.id:
            # Проверяем, был ли предыдущий канал временным
            if before.channel.id in temp_channels and len(before.channel.members) == 0:
                await before.channel.delete()
        
        # Создание обычного временного канала
        if after.channel and after.channel.id == VOICE_CREATE_CHANNEL:
            category = member.guild.get_channel(VOICE_CATEGORY)
            if category:
                channel = await create_temp_voice_channel(member.guild, category, "VC", member)
                await member.move_to(channel)

        # Создание приватного временного канала
        elif after.channel and after.channel.id == PRIVATE_VOICE_CREATE_CHANNEL:
            category = member.guild.get_channel(PRIVATE_VOICE_CATEGORY)
            if category:
                channel = await create_temp_voice_channel(member.guild, category, "PVC", member)
                await member.move_to(channel)
    except Exception as e:
        print(f"Ошибка при обработке голосовых каналов: {e}")

async def create_temp_voice_channel(guild, category, prefix, member):
    """Создание временного голосового канала"""
    try:
        # Получение следующего номера для канала
        existing_channels = [c for c in category.voice_channels 
                            if c.name.startswith(f'🔊ㆍ{prefix}')]
        next_number = 1
        used_numbers = set()
        
        for channel in existing_channels:
            try:
                num = int(channel.name.split()[-1])
                used_numbers.add(num)
            except ValueError:
                continue
        
        while next_number in used_numbers:
            next_number += 1

        # Создание нового канала
        channel_name = ""
        if prefix == "VC":
            channel_name = VOICE_CHANNEL_FORMAT.format(next_number)
        else:
            channel_name = PRIVATE_VOICE_CHANNEL_FORMAT.format(next_number)
            
        channel = await guild.create_voice_channel(
            channel_name,
            category=category
        )
        temp_channels[channel.id] = True
        return channel
    except Exception as e:
        print(f"Ошибка при создании голосового канала: {e}")
        return None

async def cleanup_empty_channels(guild):
    """Удаление пустых временных каналов"""
    try:
        for category_id in [VOICE_CATEGORY, PRIVATE_VOICE_CATEGORY]:
            category = guild.get_channel(category_id)
            if not category:
                continue

            for channel in category.voice_channels:
                if ((channel.name.startswith('🔊ㆍVC') or channel.name.startswith('🔊ㆍPVC')) and 
                   len(channel.members) == 0):
                    await channel.delete()
                    if channel.id in temp_channels:
                        del temp_channels[channel.id]
    except Exception as e:
        print(f"Ошибка при очистке пустых каналов: {e}")

async def reorder_voice_channels(guild):
    """Переименование каналов по порядку"""
    try:
        for category_id in [VOICE_CATEGORY, PRIVATE_VOICE_CATEGORY]:
            category = guild.get_channel(category_id)
            if not category:
                continue

            prefix = "PVC" if category_id == PRIVATE_VOICE_CATEGORY else "VC"
            format_str = PRIVATE_VOICE_CHANNEL_FORMAT if prefix == "PVC" else VOICE_CHANNEL_FORMAT
            
            if prefix == "VC":
                channels = [c for c in category.voice_channels 
                        if c.name.startswith('🔊ㆍVC') and len(c.members) > 0]
            else:
                channels = [c for c in category.voice_channels 
                        if c.name.startswith('🔊ㆍPVC') and len(c.members) > 0]
            
            # Сортировка каналов по текущему номеру для минимизации изменений
            def get_channel_number(channel):
                try:
                    return int(channel.name.split()[-1])
                except (ValueError, IndexError):
                    return 999
                    
            channels.sort(key=get_channel_number)
            
            for i, channel in enumerate(channels, 1):
                new_name = format_str.format(i)
                if channel.name != new_name:
                    await channel.edit(name=new_name)
    except Exception as e:
        print(f"Ошибка при перенумерации каналов: {e}")

# Запуск бота
try:
    bot.run(TOKEN)
except discord.LoginFailure:
    print("Ошибка авторизации. Проверьте токен Discord.")
except Exception as e:
    print(f"Ошибка при запуске бота: {e}") 