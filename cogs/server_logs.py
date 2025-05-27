import discord
from discord.ext import commands
import config_utils
import datetime

class ServerLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = None

    async def get_log_channel(self):
        if self.log_channel_id is None:
            config = config_utils.load_config()
            self.log_channel_id = config.get("server_logs_channel")
        return self.bot.get_channel(self.log_channel_id)

    async def send_log(self, embed: discord.Embed):
        channel = await self.get_log_channel()
        if channel:
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(
            title="🟢 Вход нового участника",
            description=f"{member.mention} ({member}) зашёл на сервер.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"ID: {member.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(
            title="🔴 Участник покинул сервер",
            description=f"{member.mention} ({member}) вышел с сервера.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"ID: {member.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        embed = discord.Embed(
            title="🗑️ Сообщение удалено",
            description=f"**Автор:** {message.author.mention} ({message.author})\n**Канал:** {message.channel.mention}",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.utcnow()
        )
        if message.content:
            embed.add_field(name="Содержимое", value=message.content[:1024], inline=False)
        embed.set_footer(text=f"ID: {message.author.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        embed = discord.Embed(
            title="✏️ Сообщение отредактировано",
            description=f"**Автор:** {before.author.mention} ({before.author})\n**Канал:** {before.channel.mention}",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="До", value=before.content[:1024] or "(пусто)", inline=False)
        embed.add_field(name="После", value=after.content[:1024] or "(пусто)", inline=False)
        embed.set_footer(text=f"ID: {before.author.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Никнейм
        if before.nick != after.nick:
            embed = discord.Embed(
                title="🔄 Смена ника",
                description=f"{after.mention} ({after}) сменил никнейм.",
                color=discord.Color.purple(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Было", value=before.nick or before.name)
            embed.add_field(name="Стало", value=after.nick or after.name)
            embed.set_footer(text=f"ID: {after.id} | 49 Battalion | Server Logs")
            await self.send_log(embed)
        # Роли
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        added = after_roles - before_roles
        removed = before_roles - after_roles
        if added or removed:
            guild = after.guild
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                if entry.target.id == after.id:
                    initiator = entry.user
                    break
            else:
                initiator = None
        if added:
            for role in added:
                embed = discord.Embed(
                    title="➕ Выдана роль",
                    description=f"{after.mention} получил роль {role.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.utcnow()
                )
                if initiator:
                    embed.add_field(name="Кто выдал", value=f"{initiator.mention} ({initiator})")
                embed.set_footer(text=f"ID: {after.id} | 49 Battalion | Server Logs")
                await self.send_log(embed)
        if removed:
            for role in removed:
                embed = discord.Embed(
                    title="➖ Снята роль",
                    description=f"{after.mention} потерял роль {role.mention}",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.utcnow()
                )
                if initiator:
                    embed.add_field(name="Кто снял", value=f"{initiator.mention} ({initiator})")
                embed.set_footer(text=f"ID: {after.id} | 49 Battalion | Server Logs")
                await self.send_log(embed)
        # Таймаут
        if before.timed_out_until != after.timed_out_until:
            guild = after.guild
            initiator = None
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id:
                    initiator = entry.user
                    break
            if after.timed_out_until:
                embed = discord.Embed(
                    title="⏳ Таймаут участника",
                    description=f"{after.mention} получил таймаут до {after.timed_out_until}",
                    color=discord.Color.orange(),
                    timestamp=datetime.datetime.utcnow()
                )
                if initiator:
                    embed.add_field(name="Кто выдал", value=f"{initiator.mention} ({initiator})")
                embed.set_footer(text=f"ID: {after.id} | 49 Battalion | Server Logs")
                await self.send_log(embed)
            else:
                embed = discord.Embed(
                    title="✅ Снят таймаут",
                    description=f"{after.mention} вышел из таймаута.",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.utcnow()
                )
                if initiator:
                    embed.add_field(name="Кто снял", value=f"{initiator.mention} ({initiator})")
                embed.set_footer(text=f"ID: {after.id} | 49 Battalion | Server Logs")
                await self.send_log(embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        initiator = None
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                initiator = entry.user
                break
        embed = discord.Embed(
            title="⛔ Бан участника",
            description=f"{user.mention} ({user}) был забанен.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        if initiator:
            embed.add_field(name="Кто забанил", value=f"{initiator.mention} ({initiator})")
        embed.set_footer(text=f"ID: {user.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        initiator = None
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                initiator = entry.user
                break
        embed = discord.Embed(
            title="✅ Разбан участника",
            description=f"{user.mention} ({user}) был разбанен.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        if initiator:
            embed.add_field(name="Кто разбанил", value=f"{initiator.mention} ({initiator})")
        embed.set_footer(text=f"ID: {user.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        guild = member.guild
        embed = None
        initiator = None
        # Перемещение другим участником
        if before.channel and after.channel and before.channel != after.channel:
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
            embed.add_field(name="Кто переместил", value=f"{initiator.mention} ({initiator})" if initiator else "Не удалось определить", inline=False)
        # Вход в голосовой
        elif not before.channel and after.channel:
            embed = discord.Embed(
                title="🔊 Вход в голосовой канал",
                description=f"{member.mention} ({member}) зашёл в {after.channel.mention}",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
        # Выход из голосового
        elif before.channel and not after.channel:
            embed = discord.Embed(
                title="🔇 Выход из голосового канала",
                description=f"{member.mention} ({member}) вышел из {before.channel.mention}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Кто вышел", value=f"{member.mention} ({member})", inline=False)
        if embed:
            embed.set_footer(text=f"ID: {member.id} | 49 Battalion | Server Logs")
            await self.send_log(embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        initiator = None
        async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_create):
            if entry.target.id == channel.id:
                initiator = entry.user
                break
        embed = discord.Embed(
            title="📁 Создан канал",
            description=f"Канал {channel.mention} ({channel.name}) был создан.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Кто создал", value=f"{initiator.mention} ({initiator})" if initiator else "Не удалось определить", inline=False)
        embed.set_footer(text=f"ID: {channel.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        initiator = None
        async for entry in channel.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
            if entry.target.id == channel.id:
                initiator = entry.user
                break
        embed = discord.Embed(
            title="🗑️ Удалён канал",
            description=f"Канал {channel.name} был удалён.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Кто удалил", value=f"{initiator.mention} ({initiator})" if initiator else "Не удалось определить", inline=False)
        embed.set_footer(text=f"ID: {channel.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.name != after.name:
            initiator = None
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_update):
                if entry.target.id == after.id:
                    initiator = entry.user
                    break
            embed = discord.Embed(
                title="✏️ Переименование канала",
                description=f"Канал {before.mention if hasattr(before, 'mention') else before.name} был переименован в {after.name}",
                color=discord.Color.blurple(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Было", value=before.name)
            embed.add_field(name="Стало", value=after.name)
            embed.add_field(name="Кто переименовал", value=f"{initiator.mention} ({initiator})" if initiator else "Не удалось определить", inline=False)
            embed.set_footer(text=f"ID: {after.id} | 49 Battalion | Server Logs")
            await self.send_log(embed)

    async def log_private_vc_action(self, action: str, user: discord.Member, channel: discord.VoiceChannel, extra: str = ""):
        embed = discord.Embed(
            title=f"🔒 Приватный канал: {action}",
            description=f"Пользователь: {user.mention} ({user})\nКанал: {channel.mention} ({channel.name})\n{extra}",
            color=discord.Color.pink(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text=f"ID: {user.id} | 49 Battalion | Server Logs")
        await self.send_log(embed)

async def setup(bot):
    await bot.add_cog(ServerLogs(bot)) 