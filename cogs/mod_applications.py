import discord
from discord.ext import commands
from discord import app_commands, ui, Embed
import config_utils
import logging

PERSONNEL_ROLE_ID = 1375501488813772941  # роль для упоминания при рассмотрении
PINK_COLOR = discord.Color(0xFFB6C1)

class ModAppStartView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Подать заявку",
        style=discord.ButtonStyle.primary,
        custom_id="mod_applications_start_button"  # persistent custom_id
    )
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ModApplicationModal())

class ModApplicationModal(ui.Modal, title="Заявка в персонал Discord"):
    age = ui.TextInput(label="Возраст (от 16)", placeholder="Введите ваш возраст", required=True, max_length=2)
    activity = ui.TextInput(label="Ваша активность в сутки", placeholder="Например: 2-4 часа", required=True, max_length=32)
    experience = ui.TextInput(label="Опыт в модерации Discord (кратко)", placeholder="Если есть, кратко", required=False, max_length=32)
    why_you = ui.TextInput(label="Почему именно вы? (кратко)", placeholder="Кратко опишите", required=True, max_length=32)
    what_add = ui.TextInput(label="Что бы вы добавили на сервер? (кратко)", placeholder="Кратко опишите", required=True, max_length=32)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            try:
                age_int = int(self.age.value)
            except ValueError:
                embed = Embed(title="Ошибка!", description="Возраст должен быть числом!", color=PINK_COLOR)
                try:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.errors.NotFound:
                    logging.error("Interaction expired or already responded (response.send_message)")
                except Exception as e:
                    logging.error(f"Ошибка при отправке embed: {e}")
                return
            if age_int < 16:
                embed = Embed(title="Отказ в заявке", description="Извините, заявки принимаются только от 16 лет.", color=PINK_COLOR)
                try:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.errors.NotFound:
                    logging.error("Interaction expired or already responded (response.send_message)")
                except Exception as e:
                    logging.error(f"Ошибка при отправке embed: {e}")
                return
            # Embed уведомление пользователю
            user_embed = Embed(
                title="Ваша заявка отправлена!",
                description="Ваша заявка на вступление в персонал отправлена на рассмотрение. Ожидайте ответа в личные сообщения.",
                color=PINK_COLOR
            )
            user_embed.set_footer(text="49 Battalion | Набор персонала | Модерация")
            try:
                await interaction.user.send(embed=user_embed)
            except:
                pass
            config = config_utils.load_config()
            review_channel_id = config.get("mod_applications_review_channel")
            review_channel = interaction.client.get_channel(review_channel_id) if review_channel_id else None
            if not review_channel:
                embed = Embed(title="Ошибка!", description="Канал для рассмотрения заявок не найден. Обратитесь к администрации.", color=PINK_COLOR)
                try:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.errors.NotFound:
                    logging.error("Interaction expired or already responded (response.send_message)")
                except Exception as e:
                    logging.error(f"Ошибка при отправке embed: {e}")
                return
            # Embed для рассмотрения (столбцами)
            role_mention = f'<@&{PERSONNEL_ROLE_ID}>'
            embed = Embed(
                title="📝 Новая заявка в персонал Discord",
                color=PINK_COLOR,
                description=f"**Пользователь:** {interaction.user.mention} ({interaction.user})"
            )
            embed.add_field(name="Возраст", value=self.age.value, inline=True)
            embed.add_field(name="Активность", value=self.activity.value, inline=True)
            embed.add_field(name="Опыт", value=self.experience.value or "Нет", inline=True)
            embed.add_field(name="Почему вы?", value=self.why_you.value, inline=True)
            embed.add_field(name="Что добавите?", value=self.what_add.value, inline=True)
            embed.set_footer(text=f"ID: {interaction.user.id} | 49 Battalion | Набор персонала | Модерация")
            view = ModAppReviewView(applicant=interaction.user)
            await review_channel.send(content=role_mention, embed=embed, view=view)
            embed = Embed(title="Успешно!", description="Ваша заявка отправлена на рассмотрение! Ожидайте ответа в личные сообщения.", color=PINK_COLOR)
            embed.set_footer(text="49 Battalion | Набор персонала | Модерация")
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.errors.NotFound:
                logging.error("Interaction expired or already responded (response.send_message)")
            except Exception as e:
                logging.error(f"Ошибка при отправке embed: {e}")
        except Exception as e:
            logging.error(f"Ошибка при отправке заявки: {e}")
            embed = Embed(title="Ошибка!", description="Произошла ошибка при отправке заявки. Попробуйте позже.", color=PINK_COLOR)
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.errors.NotFound:
                logging.error("Interaction expired or already responded (response.send_message)")
            except Exception as e:
                logging.error(f"Ошибка при отправке embed: {e}")

class ModAppReviewView(ui.View):
    def __init__(self, applicant: discord.User):
        super().__init__(timeout=None)
        self.applicant = applicant

    @discord.ui.button(label="📞 Вызвать на обзвон", style=discord.ButtonStyle.primary)
    async def call_interview(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0].copy()
        embed.color = PINK_COLOR
        embed.title = "🕑 Ожидает обзвона"
        embed.add_field(name="Статус", value="Пользователь вызван на обзвон!", inline=False)
        self.clear_items()
        self.add_item(ModAppAcceptButton(self.applicant))
        self.add_item(ModAppDeclineButton(self.applicant))
        await interaction.message.edit(embed=embed, view=self)
        embed_dm = Embed(title="Вас вызвали на обзвон!", description="Вас вызвали на обзвон по заявке в персонал. Ожидайте дальнейших инструкций от администрации.", color=PINK_COLOR)
        embed_dm.set_footer(text="49 Battalion | Набор персонала | Модерация")
        try:
            await self.applicant.send(embed=embed_dm)
        except:
            pass
        await interaction.response.send_message(embed=Embed(description=f"Пользователь {self.applicant.mention} вызван на обзвон.", color=PINK_COLOR), ephemeral=True)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        class DeclineReasonModal(ui.Modal, title="Причина отказа"):
            reason = ui.TextInput(label="Причина отказа", placeholder="Укажите причину отказа", required=True, max_length=200)
            async def on_submit(self, modal_interaction: discord.Interaction):
                embed = interaction.message.embeds[0].copy()
                embed.color = PINK_COLOR
                embed.title = "❌ Заявка отклонена"
                embed.add_field(name="Статус", value="Заявка отклонена администрацией.", inline=False)
                embed.add_field(name="Причина отказа", value=self.reason.value, inline=False)
                await interaction.message.edit(embed=embed, view=None)
                embed_dm = Embed(title="Ваша заявка отклонена", description=f"Ваша заявка в персонал была отклонена.\n**Причина:** {self.reason.value}\nСпасибо за интерес к проекту!", color=PINK_COLOR)
                embed_dm.set_footer(text="49 Battalion | Набор персонала | Модерация")
                try:
                    await self.applicant.send(embed=embed_dm)
                except:
                    pass
                await modal_interaction.response.send_message(embed=Embed(description=f"Заявка {self.applicant.mention} отклонена. Причина: {self.reason.value}", color=PINK_COLOR), ephemeral=True)
        await interaction.response.send_modal(DeclineReasonModal())

class ModAppAcceptButton(ui.Button):
    def __init__(self, applicant):
        super().__init__(label="✅ Принять", style=discord.ButtonStyle.success)
        self.applicant = applicant
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0].copy()
        embed.color = PINK_COLOR
        embed.title = "✅ Заявка одобрена"
        embed.add_field(name="Статус", value="Заявка одобрена! Роль выдана.", inline=False)
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(embed=embed, view=None)
        config = config_utils.load_config()
        mod_role_id = config.get("mod_role_id")
        guild = interaction.guild or (interaction.client.get_guild(interaction.guild_id) if interaction.guild_id else None)
        if mod_role_id and guild:
            member = guild.get_member(self.applicant.id)
            if member:
                try:
                    role = guild.get_role(mod_role_id)
                    if role:
                        await member.add_roles(role, reason="Заявка в персонал одобрена")
                except Exception as e:
                    logging.error(f"Ошибка при выдаче роли: {e}")
        embed_dm = Embed(title="Ваша заявка одобрена!", description="Ваша заявка в персонал одобрена! Добро пожаловать в команду.", color=PINK_COLOR)
        embed_dm.set_footer(text="49 Battalion | Набор персонала | Модерация")
        try:
            await self.applicant.send(embed=embed_dm)
        except:
            pass
        await interaction.response.send_message(embed=Embed(description=f"Заявка {self.applicant.mention} одобрена!", color=PINK_COLOR), ephemeral=True)

class ModAppDeclineButton(ui.Button):
    def __init__(self, applicant):
        super().__init__(label="❌ Отклонить", style=discord.ButtonStyle.danger)
        self.applicant = applicant
    async def callback(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0].copy()
        embed.color = PINK_COLOR
        embed.title = "❌ Заявка отклонена"
        embed.add_field(name="Статус", value="Заявка отклонена после обзвона.", inline=False)
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(embed=embed, view=self.view)
        embed_dm = Embed(title="Ваша заявка отклонена", description="Ваша заявка в персонал была отклонена после обзвона. Спасибо за интерес к проекту!", color=PINK_COLOR)
        embed_dm.set_footer(text="49 Battalion | Набор персонала | Модерация")
        try:
            await self.applicant.send(embed=embed_dm)
        except:
            pass
        await interaction.response.send_message(embed=Embed(description=f"Заявка {self.applicant.mention} отклонена после обзвона.", color=PINK_COLOR), ephemeral=True)

class ModApplications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._ready = False

    async def send_form_message_if_needed(self):
        config = config_utils.load_config()
        form_channel_id = config.get("mod_applications_form_channel")
        if not form_channel_id:
            return
        channel = self.bot.get_channel(form_channel_id)
        if not channel:
            return
        async for message in channel.history(limit=20):
            if message.author == self.bot.user and message.components:
                return
        embed = Embed(
            title="Набор персонала Discord!",
            description=(
                "Добро пожаловать в систему набора персонала 49 Battalion!\n\n"
                "**Кого мы ищем:**\n"
                "— Модераторов (и другие роли в будущем)\n\n"
                "**Что требуется:**\n"
                "• Возраст от 16 лет\n"
                "• Активность и желание помогать\n"
                "• Ответственность и коммуникабельность\n\n"
                "Нажмите на кнопку ниже, чтобы подать заявку!"
            ),
            color=PINK_COLOR
        )
        embed.set_footer(text="49 Battalion | Набор персонала | Модерация")
        await channel.send(embed=embed, view=ModAppStartView())

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._ready:
            self.bot.add_view(ModAppStartView())
            await self.send_form_message_if_needed()
            self._ready = True

async def setup(bot):
    await bot.add_cog(ModApplications(bot)) 