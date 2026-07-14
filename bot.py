import discord
from discord.ext import commands, tasks
from datetime import datetime, time
from zoneinfo import ZoneInfo
import os

TOKEN = os.getenv("MTUyNjI0NDQ4MDg2MzE3NDc0Nw.Gol6ZW.p6gQd9MBwQ5WXLWcFqODaUVi3cGBRPTrzeri1c")
# ==========================
# CONFIGURAÇÕES
# ==========================

PORTUGAL = ZoneInfo("Europe/Lisbon")
CANAL_ID = 1519822701936771244
CARGO_CONTRATADO = "[🧢] Contratado"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

mensagens_votacao = []

# ==========================
# BOT LIGADO
# ==========================

@bot.event
async def on_ready():
    print(f"✅ Bot ligado como {bot.user}")

    if not votacao_automatica.is_running():
        votacao_automatica.start()

    if not verificar_nao_votaram.is_running():
        verificar_nao_votaram.start()

# ==========================
# COMANDO !VOTACAO
# ==========================

@bot.command()
async def votacao(ctx):
    global mensagens_votacao
    mensagens_votacao.clear()

    data = datetime.now().strftime("%d/%m/%Y")

    embed = discord.Embed(
        title="📅 Votação de Disponibilidade",
        description=(
            f"**Data:** {data}\n\n"
            "Reage em cada horário:\n\n"
            "✅ = Sim\n"
            "❌ = Não\n"
            "❓ = Talvez"
        ),
        color=0x2ecc71
    )

    await ctx.send(embed=embed)

    horas = list(range(13, 24)) + [0]

    for hora in horas:
        msg = await ctx.send(f"**{hora:02d}:00**")
        mensagens_votacao.append(msg.id)

        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await msg.add_reaction("❓")

# ==========================
# COMANDO !NAOVOTARAM
# ==========================

@bot.command()
async def naovotaram(ctx):

    if not mensagens_votacao:
        await ctx.send("❌ Ainda não existe nenhuma votação.")
        return

    cargo = discord.utils.get(
        ctx.guild.roles,
        name=CARGO_CONTRATADO
    )

    if cargo is None:
        await ctx.send(f"❌ Cargo '{CARGO_CONTRATADO}' não encontrado.")
        return

    votaram = set()

    for msg_id in mensagens_votacao:
        try:
            mensagem = await ctx.channel.fetch_message(msg_id)
        except:
            continue

        for reaction in mensagem.reactions:
            async for user in reaction.users():
                if not user.bot:
                    votaram.add(user.id)

    faltam = []

    for membro in cargo.members:
        if membro.bot:
            continue

        if membro.id not in votaram:
            faltam.append(membro.mention)

    data = datetime.now().strftime("%d/%m/%Y")

    if not faltam:
        await ctx.send(f"✅ Todos os contratados votaram!\n📅 {data}")
    else:
        texto = (
            f"📅 **{data}**\n\n"
            f"❌ **Contratados que ainda não votaram ({len(faltam)}):**\n\n"
        )

        texto += "\n".join(faltam)

        await ctx.send(texto)

# ==========================
# VOTAÇÃO AUTOMÁTICA
# ==========================

@tasks.loop(time=time(hour=0, minute=1, tzinfo=PORTUGAL))
async def votacao_automatica():
    global mensagens_votacao
    mensagens_votacao.clear()

    canal = bot.get_channel(CANAL_ID)

    if canal is None:
        return

    data = datetime.now().strftime("%d/%m/%Y")

    embed = discord.Embed(
        title="📅 Votação de Disponibilidade",
        description=(
            f"**Data:** {data}\n\n"
            "Reage em cada horário:\n\n"
            "✅ = Sim\n"
            "❌ = Não\n"
            "❓ = Talvez"
        ),
        color=0x2ecc71
    )

    await canal.send(embed=embed)

    horas = list(range(13, 24)) + [0]

    for hora in horas:
        msg = await canal.send(f"**{hora:02d}:00**")

        mensagens_votacao.append(msg.id)

        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await msg.add_reaction("❓")

# ==========================
# VERIFICAR QUEM NÃO VOTOU
# ==========================

@tasks.loop(time=time(hour=12, minute=30, tzinfo=PORTUGAL))
async def verificar_nao_votaram():

    if not mensagens_votacao:
        return

    canal = bot.get_channel(CANAL_ID)

    if canal is None:
        return

    guild = canal.guild

    cargo = discord.utils.get(
        guild.roles,
        name=CARGO_CONTRATADO
    )

    if cargo is None:
        return

    votaram = set()

    for msg_id in mensagens_votacao:
        try:
            mensagem = await canal.fetch_message(msg_id)
        except:
            continue

        for reaction in mensagem.reactions:
            async for user in reaction.users():
                if not user.bot:
                    votaram.add(user.id)

    faltam = []

    for membro in cargo.members:
        if membro.bot:
            continue

        if membro.id not in votaram:
            faltam.append(membro.mention)

    data = datetime.now().strftime("%d/%m/%Y")

    if not faltam:
        await canal.send(f"✅ Todos os membros com o cargo {CARGO_CONTRATADO} votaram!\n📅 {data}")
    else:
        texto = (
            f"📅 **{data}**\n\n"
            f"❌ **Membros com o cargo {CARGO_CONTRATADO} que ainda não votaram ({len(faltam)}):**\n\n"
        )

        texto += "\n".join(faltam)

        await canal.send(texto)

# ==========================
# INICIAR BOT
# ==========================

bot.run(os.getenv("DISCORD_TOKEN"))
