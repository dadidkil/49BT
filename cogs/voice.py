import discord
from discord.ext import commands
from discord import app_commands, ui
import config_utils
import logging

class PrivateVCConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set_private_lobby", description="Установить голосовой канал-лобби для создания приватов")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_private_lobby(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        config_utils.update_config("private_vc_lobby", channel.id)
        await interaction.response.send_message(f"Канал-лобби для приватов установлен: {channel.mention}", ephemeral=True)
        logging.info(f"Установлен канал-лобби для приватов: {channel.name} ({channel.id})")

    @app_commands.command(name="set_private_category", description="Установить категорию для приватных каналов")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_private_category(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        config_utils.update_config("private_vc_category", category.id)
        await interaction.response.send_message(f"Категория для приватов установлена: {category.name}", ephemeral=True)
        logging.info(f"Установлена категория для приватов: {category.name} ({category.id})")

class PrivatePanelView(ui.View):
    def __init__(self, owner_id: int, vc_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.vc_id = vc_id

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.secondary)
    async def close_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец может управлять каналом!", ephemeral=True)
            return
        channel = interaction.guild.get_channel(self.vc_id)
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        # Меняем эмодзи и название
        await channel.edit(name=f"🔒 | {channel.name.lstrip('🔓🔒| ')}")
        button.label = "🔓 Открыть"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Канал закрыт для всех.", ephemeral=True)

    @discord.ui.button(label="🔓 Открыть", style=discord.ButtonStyle.secondary)
    async def open_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец может управлять каналом!", ephemeral=True)
            return
        channel = interaction.guild.get_channel(self.vc_id)
        await channel.set_permissions(interaction.guild.default_role, connect=True)
        # Меняем эмодзи и название
        await channel.edit(name=f"🔓 | {channel.name.lstrip('🔓🔒| ')}")
        button.label = "🔒 Закрыть"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Канал открыт для всех.", ephemeral=True)

    @discord.ui.button(label="👥 Лимит", style=discord.ButtonStyle.secondary)
    async def set_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец может управлять каналом!", ephemeral=True)
            return
        class LimitModal(ui.Modal, title='Установка лимита пользователей'):
            def __init__(self, view):
                super().__init__()
                self.view = view
                self.limit = ui.TextInput(label='Новый лимит', placeholder='1-99', required=True, max_length=2)
                self.add_item(self.limit)
            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    limit = int(self.limit.value)
                    if not 1 <= limit <= 99:
                        await modal_interaction.response.send_message("Лимит должен быть от 1 до 99.", ephemeral=True)
                        return
                    channel = modal_interaction.guild.get_channel(self.view.vc_id)
                    await channel.edit(user_limit=limit)
                    await modal_interaction.response.send_message(f"Лимит установлен: {limit}", ephemeral=True)
                except Exception as e:
                    await modal_interaction.response.send_message(f"Ошибка: {e}", ephemeral=True)
        await interaction.response.send_modal(LimitModal(view=self))

    @discord.ui.button(label="✏️ Переименовать", style=discord.ButtonStyle.secondary)
    async def rename_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец может управлять каналом!", ephemeral=True)
            return
        class RenameModal(ui.Modal, title='Переименование канала'):
            def __init__(self, vc_id):
                super().__init__()
                self.vc_id = vc_id
                self.name = ui.TextInput(label='Новое имя', required=True, max_length=32)
                self.add_item(self.name)
            async def on_submit(self, modal_interaction: discord.Interaction):
                channel = modal_interaction.guild.get_channel(self.vc_id)
                await channel.edit(name=self.name.value)
                await modal_interaction.response.send_message(f"Канал переименован в: {self.name.value}", ephemeral=True)
        await interaction.response.send_modal(RenameModal(self.vc_id))

    @discord.ui.button(label="🚫 Удалить", style=discord.ButtonStyle.danger)
    async def delete_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец может управлять каналом!", ephemeral=True)
            return
        channel = interaction.guild.get_channel(self.vc_id)
        await channel.delete()
        await interaction.response.send_message("Канал удалён.", ephemeral=True)

class PrivateVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owners = {}  # user_id: channel_id

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        config = config_utils.load_config()
        lobby_id = config.get("private_vc_lobby")
        category_id = config.get("private_vc_category")
        if not lobby_id or not category_id:
            return
        # Заходит в лобби — создаём приват
        if after.channel and after.channel.id == lobby_id:
            if member.id in self.owners:
                # Уже есть приват — перемещаем
                channel = member.guild.get_channel(self.owners[member.id])
                if channel:
                    await member.move_to(channel)
                    return
            category = member.guild.get_channel(category_id)
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(connect=False),
                member: discord.PermissionOverwrite(connect=True, manage_channels=True)
            }
            vc = await category.create_voice_channel(name=f"🔒 | {member.display_name}", overwrites=overwrites)
            self.owners[member.id] = vc.id
            await member.move_to(vc)
        # Удаляем приват, если он пустой
        if before.channel and before.channel.category and before.channel.category.id == category_id:
            if len(before.channel.members) == 0:
                for uid, cid in list(self.owners.items()):
                    if cid == before.channel.id:
                        del self.owners[uid]
                        break
                try:
                    if before.channel.guild.get_channel(before.channel.id):
                        await before.channel.delete()
                except discord.errors.NotFound:
                    pass  # Канал уже удалён

    @app_commands.command(name="private_panel", description="Панель управления приватным каналом")
    async def private_panel(self, interaction: discord.Interaction):
        # Проверяем, есть ли у пользователя приват
        owner_vc_id = self.owners.get(interaction.user.id)
        if not owner_vc_id:
            await interaction.response.send_message("У вас нет приватного канала. Зайдите в лобби для создания.", ephemeral=True)
            return
        view = PrivatePanelView(interaction.user.id, owner_vc_id)
        await interaction.response.send_message("Панель управления приватным каналом:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PrivateVCConfig(bot))
    await bot.add_cog(PrivateVC(bot)) 