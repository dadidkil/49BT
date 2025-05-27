import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle, Embed, Interaction
from .. import config_utils
import logging

# Цвета для embed
APPLIED_COLOR = discord.Color.blue() # Синий для новой заявки
ACCEPTED_FOR_INTERVIEW_COLOR = discord.Color.green() # Зеленый для принятых на обзвон
REJECTED_COLOR = discord.Color.red() # Красный для отклоненных

class ApplicationModal(ui.Modal, title='Заявка на пост модератора'):
    real_age = ui.TextInput(
        label='Ваш реальный возраст:',
        placeholder='Например: 18',
        required=True,
        min_length=2, max_length=3
    )

    experience = ui.TextInput(
        label='Опыт модерирования (если есть, опишите):',
        placeholder='Пример: Модерировал сервер X 1 год, знаю команды /ban, /kick...',
        style=discord.TextStyle.long,
        required=False, max_length=1000
    )

    motivation = ui.TextInput(
        label='Почему вы хотите стать модератором?',
        placeholder='Расскажите о вашей мотивации и целях',
        style=discord.TextStyle.long,
        required=True, min_length=50, max_length=1500
    )

    time_commitment = ui.TextInput(
        label='Сколько времени готовы уделять модерированию?',
        placeholder='Пример: 2-3 часа в день / 15 часов в неделю',
        required=True, min_length=5, max_length=100
    )

    ready_for_interview = ui.TextInput(
        label='Готовы ли вы пройти собеседование (обзвон)?',
        placeholder='Да / Нет',
        required=True, min_length=2, max_length=3
    )

    additional_info = ui.TextInput(
        label='Дополнительная информация (необязательно):',
        placeholder='Любая другая информация, которую считаете важной',
        style=discord.TextStyle.long,
        required=False, max_length=1000
    )

    async def on_submit(self, interaction: Interaction):
        try:
            config = config_utils.load_config()
            app_channel_id = config.get("moderation_application_channel")
            if not app_channel_id:
                await interaction.response.send_message(
                    "Канал для заявок не настроен. Обратитесь к администрации.", ephemeral=True
                )
                logging.error("Moderation applications: Канал для заявок (moderation_application_channel) не настроен.")
                return

            app_channel = interaction.guild.get_channel(app_channel_id)
            if not app_channel:
                await interaction.response.send_message(
                    "Канал для заявок не найден. Обратитесь к администрации.", ephemeral=True
                )
                logging.error(f"Moderation applications: Канал для заявок с ID {app_channel_id} не найден.")
                return

            embed = Embed(title="📝 Новая заявка на модератора", color=APPLIED_COLOR)
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.add_field(name="Отправитель:", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
            embed.add_field(name="Возраст:", value=self.real_age.value, inline=False)
            embed.add_field(name="Опыт модерирования:", value=self.experience.value or "Не указан", inline=False)
            embed.add_field(name="Мотивация:", value=self.motivation.value, inline=False)
            embed.add_field(name="Готовность уделять время:", value=self.time_commitment.value, inline=False)
            embed.add_field(name="Готовность к обзвону:", value=self.ready_for_interview.value, inline=False)
            if self.additional_info.value:
                embed.add_field(name="Дополнительная информация:", value=self.additional_info.value, inline=False)
            embed.set_footer(text=f"Заявка от: {interaction.user.name}")
            embed.timestamp = discord.utils.utcnow()

            view = ApplicationReviewView(original_applicant=interaction.user)
            await app_channel.send(embed=embed, view=view)
            await interaction.response.send_message("✅ Ваша заявка успешно отправлена! Ожидайте рассмотрения.", ephemeral=True)
            logging.info(f"Пользователь {interaction.user.name} ({interaction.user.id}) подал заявку на модератора.")

        except Exception as e:
            logging.error(f"Ошибка при обработке заявки на модератора: {e}")
            await interaction.response.send_message("Произошла ошибка при отправке заявки. Попробуйте позже.", ephemeral=True)

    async def on_error(self, interaction: Interaction, error: Exception):
        logging.error(f"Ошибка в модальном окне заявки: {error}")
        await interaction.response.send_message("Что-то пошло не так. Пожалуйста, попробуйте снова.", ephemeral=True)

class ApplicationReviewView(ui.View):
    def __init__(self, original_applicant: discord.Member):
        super().__init__(timeout=None) # Кнопки должны быть постоянными
        self.original_applicant = original_applicant

    async def interaction_check(self, interaction: Interaction) -> bool:
        config = config_utils.load_config()
        recruiter_role_id = config.get("moderation_recruiter_role")
        if not recruiter_role_id:
            await interaction.response.send_message("Роль рекрутера не настроена.", ephemeral=True)
            logging.warning("Moderation applications: Роль рекрутера (moderation_recruiter_role) не настроена.")
            return False
        
        recruiter_role = interaction.guild.get_role(recruiter_role_id)
        if not recruiter_role:
            await interaction.response.send_message("Роль рекрутера не найдена на сервере.", ephemeral=True)
            logging.warning(f"Moderation applications: Роль рекрутера с ID {recruiter_role_id} не найдена.")
            return False

        if recruiter_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("У вас нет прав для этого действия.", ephemeral=True)
            return False
        return True

    @ui.button(label="✅ Принять на обзвон", style=ButtonStyle.success, custom_id="mod_app_accept_interview")
    async def accept_interview(self, interaction: Interaction, button: ui.Button):
        original_message = interaction.message
        original_embed = original_message.embeds[0]
        
        new_embed = original_embed.copy()
        new_embed.color = ACCEPTED_FOR_INTERVIEW_COLOR
        new_embed.add_field(name="Статус:", value=f"✅ Принят на обзвон пользователем {interaction.user.mention}", inline=False)
        new_embed.timestamp = discord.utils.utcnow()

        # Отключаем все кнопки в View
        for item in self.children:
            item.disabled = True
        
        await original_message.edit(embed=new_embed, view=self)
        await interaction.response.send_message(f"Заявка от {self.original_applicant.mention} принята на обзвон.", ephemeral=True)
        try:
            await self.original_applicant.send(
                f"Здравствуйте, {self.original_applicant.mention}! 🎉\n\n"
                f"Ваша заявка на пост модератора на сервере **{interaction.guild.name}** была рассмотрена и **принята к обзвону**!\n"
                f"В ближайшее время с вами свяжется один из администраторов для назначения времени собеседования.\n\n"
                f"Спасибо за ваш интерес к проекту!"
            )
            logging.info(f"Заявка {self.original_applicant.name} принята на обзвон. Рекрутер: {interaction.user.name}")
        except discord.Forbidden:
            logging.warning(f"Не удалось отправить ЛС пользователю {self.original_applicant.name} (закрыты ЛС?).")
            await interaction.followup.send(f"Не удалось уведомить {self.original_applicant.mention} в ЛС (возможно, закрыты).", ephemeral=True)
        except Exception as e:
            logging.error(f"Ошибка при отправке ЛС о принятии на обзвон: {e}")

    @ui.button(label="❌ Отклонить", style=ButtonStyle.danger, custom_id="mod_app_reject")
    async def reject_application(self, interaction: Interaction, button: ui.Button):
        original_message = interaction.message
        original_embed = original_message.embeds[0]

        # Можно добавить модальное окно для указания причины отклонения
        # Для простоты пока без него

        new_embed = original_embed.copy()
        new_embed.color = REJECTED_COLOR
        new_embed.add_field(name="Статус:", value=f"❌ Отклонено пользователем {interaction.user.mention}", inline=False)
        new_embed.timestamp = discord.utils.utcnow()

        for item in self.children:
            item.disabled = True

        await original_message.edit(embed=new_embed, view=self)
        await interaction.response.send_message(f"Заявка от {self.original_applicant.mention} отклонена.", ephemeral=True)
        try:
            await self.original_applicant.send(
                f"Здравствуйте, {self.original_applicant.mention}.\n\n"
                f"К сожалению, ваша заявка на пост модератора на сервере **{interaction.guild.name}** была **отклонена**.\n"
                f"Не расстраивайтесь, вы можете попробовать снова позже.\n\n"
                f"Спасибо за ваш интерес к проекту!"
            )
            logging.info(f"Заявка {self.original_applicant.name} отклонена. Рекрутер: {interaction.user.name}")
        except discord.Forbidden:
            logging.warning(f"Не удалось отправить ЛС пользователю {self.original_applicant.name} (закрыты ЛС?).")
            await interaction.followup.send(f"Не удалось уведомить {self.original_applicant.mention} в ЛС (возможно, закрыты).", ephemeral=True)
        except Exception as e:
            logging.error(f"Ошибка при отправке ЛС об отклонении: {e}")

class ModerationApplications(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="apply_moderator", description="Подать заявку на пост модератора")
    async def apply_moderator_command(self, interaction: Interaction):
        """Открывает модальное окно для подачи заявки на модератора."""
        config = config_utils.load_config()
        app_channel_id = config.get("moderation_application_channel")
        recruiter_role_id = config.get("moderation_recruiter_role")

        if not app_channel_id or not recruiter_role_id:
            await interaction.response.send_message(
                "Система подачи заявок не настроена. Пожалуйста, сообщите администрации.", ephemeral=True
            )
            logging.warning("Команда /apply_moderator: moderation_application_channel или moderation_recruiter_role не настроены.")
            return
            
        await interaction.response.send_modal(ApplicationModal())

    @commands.Cog.listener()
    async def on_ready(self):
        # Регистрируем View для обработки кнопок после перезапуска бота, если они были в канале
        # Нам нужно передать 'original_applicant', но мы не можем знать его заранее для всех старых сообщений.
        # Поэтому, при нажатии кнопки, мы будем пытаться получить пользователя из embed.
        # Для этого View должен быть немного умнее.
        # Пока что, для простоты, сделаем так, чтобы View создавался при отправке, а не регистрировался глобально.
        # Если кнопки должны работать после перезапуска, это потребует более сложной логики хранения состояния 
        # или извлечения original_applicant из сообщения.
        # В текущей реализации кнопки будут работать только в текущей сессии бота.
        # Чтобы кнопки работали после перезапуска, нужен persistent view и другой подход к original_applicant.
        pass 

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationApplications(bot))
    # Если кнопки должны быть постоянными и работать после перезапуска бота,
    # то нужно добавить view здесь, но это потребует доработки ApplicationReviewView
    # для извлечения applicant_id из embed-а или другой логики.
    # bot.add_view(ApplicationReviewView(None)) # Не сработает так просто с original_applicant
    logging.info("Cog ModerationApplications загружен.") 