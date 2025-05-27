import discord
from discord.ext import commands
from discord import app_commands
import config_utils
import logging

BANNER_URL = "https://media.discordapp.net/ephemeral-attachments/1374748463337836697/1375810057996079245/standard_2.gif?ex=68330a77&is=6831b8f7&hm=fa0adbc905994051bbae2c9b65ef89058edd4a5fb0d264922cc8e34fdbddae53&="

class AdminConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_verification_channel", description="Установить канал для верификации")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_verification_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            config_utils.update_config("verification_channel", channel.id)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Успех",
                    description=f"Канал верификации установлен: {channel.mention}",
                    color=discord.Color.green()
                ).set_footer(text="49 Battalion | Администрирование").set_image(url=BANNER_URL),
                ephemeral=True
            )
            logging.info(f"Канал верификации установлен: {channel.name} (ID: {channel.id})")
        except Exception as e:
            logging.error(f"Ошибка при установке канала верификации: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Ошибка",
                    description="Произошла ошибка при установке канала верификации.",
                    color=discord.Color.red()
                ).set_footer(text="49 Battalion | Администрирование"),
                ephemeral=True
            )

    @app_commands.command(name="set_member_role", description="Установить роль участника")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_member_role(self, interaction: discord.Interaction, role: discord.Role):
        try:
            config_utils.update_config("member_role", role.id)
            await interaction.response.send_message(
                f"Роль участника установлена: {role.mention}",
                ephemeral=True
            )
            logging.info(f"Роль участника установлена: {role.name} (ID: {role.id})")
        except Exception as e:
            logging.error(f"Ошибка при установке роли участника: {e}")
            await interaction.response.send_message(
                "Произошла ошибка при установке роли участника.",
                ephemeral=True
            )

    @app_commands.command(name="set_welcome_channel", description="Установить канал приветствий")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            config_utils.update_config("welcome_channel", channel.id)
            await interaction.response.send_message(
                f"Канал приветствий установлен: {channel.mention}",
                ephemeral=True
            )
            logging.info(f"Канал приветствий установлен: {channel.name} (ID: {channel.id})")
        except Exception as e:
            logging.error(f"Ошибка при установке канала приветствий: {e}")
            await interaction.response.send_message(
                "Произошла ошибка при установке канала приветствий.",
                ephemeral=True
            )

    @app_commands.command(name="ping", description="Проверка работы бота")
    async def ping(self, interaction: discord.Interaction):
        try:
            latency = round(self.bot.latency * 1000)
            await interaction.response.send_message(
                f"🏓 Понг! Задержка: {latency}мс",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Ошибка при проверке пинга: {e}")
            await interaction.response.send_message(
                "Произошла ошибка при проверке пинга.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(AdminConfig(bot)) 