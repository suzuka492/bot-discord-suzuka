import os
import platform
import discord
import asyncio
from discord.ext import commands
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Esto es obligatorio para que lea el token
load_dotenv()

# Configura aquí la URL de la imagen por defecto para tus Webhooks
WEBHOOK_AVATAR_URL = "https://cdn.discordapp.com/attachments/1143960952065249475/1507090125169885225/image.png?ex=6a10a28e&is=6a0f510e&hm=57ec06b9c094bbdcf893dc8910e2822264e0f9ccab45a48b5155168fee1b1463&"

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="?", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(SorteoView())
        self.add_view(AnuncioView())
        self.add_view(HelpView())

bot = MyBot()

# Eliminar el comando help por defecto para usar el tuyo personalizado
bot.remove_command('help')

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

# Función auxiliar para manejar el error de permisos
async def sin_permisos(ctx):
    try: await ctx.message.delete()
    except: pass
    await ctx.send(f"❌ {ctx.author.mention}, no tienes permiso para usar este comando.", delete_after=10)

# Ejemplo de uso de webhook
async def enviar_webhook(url, embed):
    webhook = discord.SyncWebhook.from_url(url)
    webhook.send(embed=embed, username="Sistema", avatar_url=WEBHOOK_AVATAR_URL)

# ---------------------------
# VARIABLES DE PERMISOS
# ---------------------------
promo_roles = {}
anuncio_roles = {}
# ---------------------------
# SISTEMA DE BIENVENIDA
# ---------------------------
welcome_channels = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, channel: discord.TextChannel):
    webhook = await channel.create_webhook(name="Bienvenidas")
    welcome_channels[ctx.guild.id] = webhook.url
    await ctx.send(f"✅ Webhook de bienvenida creado en {channel.mention}")

# ---------------------------
# SISTEMA DE PROMOCIONES
# ---------------------------
yt_channels = {}
tiktok_channels = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def setyt(ctx, channel: discord.TextChannel):
    webhook = await channel.create_webhook(name="Promociones YouTube")
    yt_channels[ctx.guild.id] = webhook.url
    await ctx.send(f"✅ Canal de promociones YouTube asignado: {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def settiktok(ctx, channel: discord.TextChannel):
    webhook = await channel.create_webhook(name="Promociones TikTok")
    tiktok_channels[ctx.guild.id] = webhook.url
    await ctx.send(f"✅ Canal de promociones TikTok asignado: {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setpromorole(ctx, role: discord.Role):
    promo_roles[ctx.guild.id] = role.id
    await ctx.send(f"✅ El rol **{role.name}** ahora puede gestionar las promociones.")

# ---------------------------
# SISTEMA DE MODERACIÓN
# ---------------------------
mod_roles = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def setmodrole(ctx, role: discord.Role):
    mod_roles[ctx.guild.id] = role.id
    await ctx.send(f"✅ Rol autorizado para moderación: {role.name}")

def tiene_permiso_mod(ctx):
    guild_id = ctx.guild.id
    if guild_id in mod_roles:
        role_id = mod_roles[guild_id]
        role = ctx.guild.get_role(role_id)
        if role in ctx.author.roles:
            return True
    return ctx.author.guild_permissions.administrator

def tiene_permiso_promo(ctx):
    guild_id = ctx.guild.id
    if guild_id in promo_roles:
        role = ctx.guild.get_role(promo_roles[guild_id])
        if role and role in ctx.author.roles: return True
    return ctx.author.guild_permissions.administrator

@bot.command()
async def yt(ctx, link: str):
    if not tiene_permiso_promo(ctx): return await sin_permisos(ctx)
    guild_id = ctx.guild.id
    if guild_id in yt_channels:
        webhook_url = yt_channels[guild_id]
        webhook = discord.Webhook.from_url(webhook_url, client=bot)
        embed = discord.Embed(
            title="📺 ¡Nuevo video en YouTube!",
            description=f"{ctx.author.mention} ha compartido su nuevo video 🎉\n👉 {link}\n\nNo olvides dejar tu like 👍 y suscribirte 🔔",
            color=discord.Color.red()
        )
        await webhook.send(embed=embed, username="Promociones YouTube", avatar_url=WEBHOOK_AVATAR_URL)

@bot.command()
async def tiktok(ctx, link: str):
    if not tiene_permiso_promo(ctx): return await sin_permisos(ctx)
    guild_id = ctx.guild.id
    if guild_id in tiktok_channels:
        webhook_url = tiktok_channels[guild_id]
        webhook = discord.Webhook.from_url(webhook_url, client=bot)
        embed = discord.Embed(
            title="🎶 ¡Nuevo TikTok!",
            description=f"{ctx.author.mention} ha compartido su nuevo TikTok 💃\n👉 {link}\n\nNo olvides dejar tu ❤️ y seguirlo :3",
            color=discord.Color.purple()
        )
        await webhook.send(embed=embed, username="Promociones TikTok", avatar_url=WEBHOOK_AVATAR_URL)

@bot.command()
async def ban(ctx, member: discord.Member, *, reason="No se especificó razón"):
    if not tiene_permiso_mod(ctx): return await sin_permisos(ctx)
    await member.ban(reason=reason)
    await ctx.send(f"⛔ {member.mention} fue baneado. Razón: {reason}")

@bot.command()
async def kick(ctx, member: discord.Member, *, reason="No se especificó razón"):
    if not tiene_permiso_mod(ctx): return await sin_permisos(ctx)
    await member.kick(reason=reason)
    await ctx.send(f"👢 {member.mention} fue expulsado. Razón: {reason}")

@bot.command()
async def clear(ctx, cantidad: int):
    if not tiene_permiso_mod(ctx): return await sin_permisos(ctx)
    await ctx.channel.purge(limit=cantidad+1)
    await ctx.send(f"🧹 Se borraron {cantidad} mensajes.", delete_after=5)

@bot.command()
async def mute(ctx, member: discord.Member, tiempo: str = None, *, reason="No se especificó razón"):
    if not tiene_permiso_mod(ctx): return await sin_permisos(ctx)
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            if isinstance(channel, discord.TextChannel): await channel.set_permissions(mute_role, send_messages=False)
            elif isinstance(channel, discord.VoiceChannel): await channel.set_permissions(mute_role, speak=False)
    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"🤐 {member.mention} fue muteado. Razón: {reason}")
    if tiempo and tiempo.endswith('m'):
        await asyncio.sleep(int(tiempo[:-1]) * 60)
        await member.remove_roles(mute_role)

@bot.command()
async def unmute(ctx, member: discord.Member):
    if not tiene_permiso_mod(ctx): return await sin_permisos(ctx)
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 {member.mention} fue desmuteado.")

# ---------------------------
# SISTEMA DE ANUNCIOS
# ---------------------------
anuncio_channels = {}

class AnuncioModal(discord.ui.Modal, title="Crear anuncio"):
    titulo = discord.ui.TextInput(label="Título")
    descripcion = discord.ui.TextInput(label="Descripción", style=discord.TextStyle.paragraph)
    imagen = discord.ui.TextInput(label="Imagen (URL)", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        if guild_id in anuncio_channels:
            webhook_url = anuncio_channels[guild_id]
            webhook = discord.Webhook.from_url(webhook_url, client=bot)
            embed = discord.Embed(title=self.titulo.value, description=self.descripcion.value, color=discord.Color.blue())
            if self.imagen.value:
                embed.set_image(url=self.imagen.value)
            await webhook.send(embed=embed, username="📢 Anuncios", avatar_url=WEBHOOK_AVATAR_URL)
            await interaction.response.send_message("✅ Anuncio enviado correctamente", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No se ha configurado un canal de anuncios. Usa `?setanuncio`", ephemeral=True)

class AnuncioView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✍️ Escribir Anuncio", style=discord.ButtonStyle.green, custom_id="anuncio_btn")
    async def abrir_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnuncioModal())

def tiene_permiso_anuncio(ctx):
    guild_id = ctx.guild.id
    if guild_id in anuncio_roles:
        role = ctx.guild.get_role(anuncio_roles[guild_id])
        if role and role in ctx.author.roles: return True
    return ctx.author.guild_permissions.administrator

@bot.command()
@commands.has_permissions(administrator=True)
async def setanuncio(ctx, channel: discord.TextChannel):
    webhook = await channel.create_webhook(name="Anuncios")
    anuncio_channels[ctx.guild.id] = webhook.url
    await ctx.send(f"✅ Canal de anuncios asignado: {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setanunciorole(ctx, role: discord.Role):
    anuncio_roles[ctx.guild.id] = role.id
    await ctx.send(f"✅ El rol **{role.name}** ahora tiene permiso para usar comandos de anuncios.")

@bot.command()
async def anuncio(ctx):
    if not tiene_permiso_anuncio(ctx): return await sin_permisos(ctx)
    view = AnuncioView()
    await ctx.send("Haz clic en el botón de abajo para redactar tu anuncio:", view=view)

# ---------------------------
# SISTEMA DE AUTOROLE
# ---------------------------
autoroles = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def autorole(ctx, role: discord.Role):
    autoroles[ctx.guild.id] = role.id
    await ctx.send(f"✅ Autorole configurado: {role.name}")

# ---------------------------
# EVENTO UNIFICADO: BIENVENIDA + AUTOROLE
# ---------------------------
@bot.event
async def on_member_join(member):
    guild_id = member.guild.id
    if guild_id in welcome_channels:
        webhook_url = welcome_channels[guild_id]
        webhook = discord.Webhook.from_url(webhook_url, client=bot)
        embed = discord.Embed(
            title="🌟 ¡Bienvenido!",
            description=f"Hola {member.mention}, bienvenido o bienvenida a mi humilde comunidad espero que te guste 💕",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await webhook.send(embed=embed, username="Sistema de Bienvenidas", avatar_url=WEBHOOK_AVATAR_URL)
    if guild_id in autoroles:
        role_id = autoroles[guild_id]
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role, reason="Autorole automático")
            except Exception as e:
                print(f"No se pudo asignar autorole a {member}: {e}")

# --- BLOQUE PARA UPTIMEROBOT ---
app = Flask(__name__)

@app.route('/')
def home():
    return "El bot está activo 24/7"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()
# ---------------------------
# SISTEMA DE BOOSTS
# ---------------------------
boost_channels = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def setboost(ctx, channel: discord.TextChannel):
    boost_channels[ctx.guild.id] = channel.id
    await ctx.send(f"✅ Canal de boosts configurado en {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def testboost(ctx):
    guild_id = ctx.guild.id
    if guild_id not in boost_channels:
        return await ctx.send("❌ Primero configura un canal con `?setboost #canal`")
    channel = bot.get_channel(boost_channels[guild_id])
    if not channel:
        return await ctx.send("❌ No encontré el canal de boosts.")
    boost_count = ctx.guild.premium_subscription_count
    embed = discord.Embed(
        title="🚀 ¡NUEVO BOOST!",
        description=(f"💜 Gracias {ctx.author.mention} por boostear el servidor.\n\n✨ ¡Ya somos **{boost_count} boosts**!"),
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_image(url="https://media.tenor.com/oLA9bXhyPvmAAAAC/nanally-nte.gif")
    embed.set_footer(text=f"{ctx.guild.name} • Gracias por apoyar la comunidad 💕")
    await channel.send(embed=embed)
    await ctx.send("✅ Mensaje de boost enviado para prueba.")

@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        guild_id = after.guild.id
        if guild_id not in boost_channels: return
        channel = bot.get_channel(boost_channels[guild_id])
        if not channel: return
        boost_count = after.guild.premium_subscription_count
        embed = discord.Embed(
            title="🚀 ¡NUEVO BOOST!",
            description=(f"💜 Gracias {after.mention} por boostear el servidor.\n\n✨ ¡Ya somos **{boost_count} boosts**!"),
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=after.display_avatar.url)
        embed.set_image(url="https://media.tenor.com/oLA9bXhyPvmAAAAC/nanally-nte.gif")
        embed.set_footer(text=f"{after.guild.name} • Gracias por apoyar la comunidad 💕")
        await channel.send(embed=embed)

# =========================================================
# 💎 HELP SYSTEM (EDITADO CON DESCRIPCIONES)
# =========================================================

def promo_embed():
    return discord.Embed(title="📺 SISTEMA DE PROMOCIONES", description="Permite publicar contenido en canales específicos.", color=discord.Color.red()).add_field(name="🚀 Comandos", value="`?yt [link]` : Comparte tu video de YouTube.\n`?tiktok [link]` : Comparte tu TikTok.", inline=False)

def mod_embed():
    return discord.Embed(title="🛡️ SISTEMA DE MODERACIÓN", description="Herramientas para la seguridad del servidor.", color=discord.Color.green()).add_field(name="🔨 Sanciones", value="`?ban` : Expulsar permanentemente.\n`?kick` : Expulsar del servidor.\n`?mute` : Silenciar usuario.\n`?unmute` : Quitar silencio.", inline=False).add_field(name="🧹 Gestión", value="`?clear` : Borra mensajes masivamente.\n`?setmodrole` : Define rol de moderador.", inline=False)

def anuncio_embed():
    return discord.Embed(title="📢 SISTEMA DE ANUNCIOS", description="Panel para crear comunicados oficiales.", color=discord.Color.blurple()).add_field(name="📝 Uso", value="`?anuncio` : Abre el panel interactivo.\n`?setanuncio` : Configura el canal de anuncios.", inline=False)

def welcome_embed():
    return discord.Embed(title="🎉 SISTEMA DE BIENVENIDAS", description="Mensajes automáticos para nuevos miembros.", color=discord.Color.gold()).add_field(name="⚙️ Configuración", value="`?setwelcome` : Define el canal de bienvenidas.", inline=False)

def autorole_embed():
    return discord.Embed(title="🎭 SISTEMA AUTOROLE", description="Asignación automática de roles al entrar.", color=discord.Color.purple()).add_field(name="⚙️ Configuración", value="`?autorole` : Define el rol que se otorga.", inline=False)

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Promociones", emoji="📺", description="Gestión de videos", value="promo"),
            discord.SelectOption(label="Moderación", emoji="🛡️", description="Sanciones y limpieza", value="mod"),
            discord.SelectOption(label="Anuncios", emoji="📢", description="Panel de comunicados", value="anuncio"),
            discord.SelectOption(label="Bienvenidas", emoji="🎉", description="Mensajes de bienvenida", value="welcome"),
            discord.SelectOption(label="Autorole", emoji="🎭", description="Asignación de roles", value="autorole"),
        ]
        super().__init__(placeholder="Selecciona una categoría...", options=options, custom_id="help_menu_select")
    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        embeds = {"promo": promo_embed(), "mod": mod_embed(), "anuncio": anuncio_embed(), "welcome": welcome_embed(), "autorole": autorole_embed()}
        await interaction.response.edit_message(embed=embeds[val], view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelpSelect())

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="✨ PANEL DE AYUDA", description="Selecciona una categoría en el menú de abajo.", color=discord.Color.purple())
    await ctx.send(embed=embed, view=HelpView())

# =========================================================
# 🛡️ SISTEMA DE LOGS
# =========================================================
log_channels = {}

@bot.command()
@commands.has_permissions(administrator=True)
async def setlogs(ctx, channel: discord.TextChannel):
    log_channels[ctx.guild.id] = channel.id
    await ctx.message.delete()
    await ctx.send(f"✅ Canal de logs configurado.", delete_after=5)

async def send_log(guild, embed):
    if guild.id in log_channels:
        channel = guild.get_channel(log_channels[guild.id])
        if channel: await channel.send(embed=embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    embed = discord.Embed(title="🗑️ Mensaje eliminado", color=discord.Color.red())
    embed.add_field(name="Autor", value=message.author.mention)
    embed.add_field(name="Canal", value=message.channel.mention)
    await send_log(message.guild, embed)

# =========================================================
# 🎁 SISTEMA DE SORTEOS
# =========================================================
class SorteoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.participantes = []
    @discord.ui.button(label="🎉 ¡Participar!", style=discord.ButtonStyle.green, custom_id="participar_sorteo")
    async def participar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.participantes: return await interaction.response.send_message("❌ Ya participas.", ephemeral=True)
        self.participantes.append(interaction.user.id)
        await interaction.response.send_message("✅ ¡Te has unido!", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def sorteo(ctx, tiempo: int, *, premio: str):
    view = SorteoView()
    embed = discord.Embed(title="🎁 SORTEO", description=f"Premio: **{premio}**\nHaz clic en el botón.", color=discord.Color.gold())
    mensaje = await ctx.send(embed=embed, view=view)
    await asyncio.sleep(tiempo * 60)
    if not view.participantes: await ctx.send("😔 Nadie participó.")
    else:
        import random
        ganador = ctx.guild.get_member(random.choice(view.participantes))
        await ctx.send(f"🏆 ¡El ganador de **{premio}** es {ganador.mention if ganador else 'alguien'}!")

keep_alive()
bot.run(os.getenv("TOKEN"))