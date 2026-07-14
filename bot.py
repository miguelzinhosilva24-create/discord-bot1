import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta, timezone
import os
import traceback

# Puxa o token de forma segura a partir do painel de alojamento (sem expor no GitHub)
TOKEN = os.getenv("MTUyNjI0NDQ4MDg2MzE3NDc0Nw.GILBzY.jKebRMEW6vnNyMs4DV_wHRe1qtigY8jBHTsDUM")

# ==========================
# CONFIGURAÇÕES
# ==========================

try:
    from zoneinfo import ZoneInfo
    PORTUGAL = ZoneInfo("Europe/Lisbon")
except Exception:
    PORTUGAL = timezone(timedelta(hours=1))

CONFIGS = {
    1519822701936771244: {
        "cargo": "[🧢] Contratado"
    },
    1478143333351162150: {
        "cargo": "[🧢] Caixa Baixa"
    }
}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
mensagens_votacao = {}

# ==========================
# FUNÇÕES AUXILIARES
# ==========================

async def obter_canal_seguro(canal_id):
    canal = bot.get_channel(canal_id)
    if canal is None:
        try:
            canal = await bot.fetch_channel(canal_id)
        except Exception:
            return None
    return canal

async def criar_votacao_no_canal(canal):
    mensagens_votacao[canal.id] = []
    data = datetime.now(PORTUGAL).strftime("%d/%m/%Y")

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
        mensagens_votacao[canal.id].append(msg.id)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await msg.add_reaction("❓")

async def obter_nao_votaram(canal, nome_cargo):
    msg_ids = mensagens_votacao.get(canal.id, [])
    if not msg_ids:
        return None, "❌ Não há nenhuma votação ativa registada na memória do bot para este canal. Usa `!votacao` primeiro."

    if not canal.guild.chunked:
        await canal.guild.chunk()

    cargo = discord.utils.get(canal.guild.roles, name=nome_cargo)
    if cargo is None:
        return None, f"❌ Cargo '{nome_cargo}' não foi encontrado neste servidor."

    votaram = set()
    for msg_id in msg_ids:
        try:
            mensagem = await canal.fetch_message(msg_id)
        except Exception:
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

    return faltam, None

# ==========================
# EVENTOS E COMANDOS
# ==========================

@bot.event
async def on_ready():
    print(f"✅ Bot ligado como {bot.user}")
    for guild in bot.guilds:
        await guild.chunk()
    
    if not votacao_automatica.is_running():
        votacao_automatica.start()
    if not verificar_nao_votaram.is_running():
        verificar_nao_votaram.start()

@bot.command()
async def votacao(ctx):
    if ctx.channel.id not in CONFIGS:
        await ctx.send("❌ Este canal não está configurado.")
        return
    try:
        await ctx.send("🔄 A iniciar votação...")
        await criar_votacao_no_canal(ctx.channel)
    except Exception as e:
        await ctx.send(f"❌ Erro: `{str(e)}`")

@bot.command()
async def naovotaram(ctx):
    if ctx.channel.id not in CONFIGS:
        await ctx.send("❌ Este canal não está configurado.")
        return

    nome_cargo = CONFIGS[ctx.channel.id]["cargo"]
    async with ctx.typing():
        faltam, erro = await obter_nao_votaram(ctx.channel, nome_cargo)

    if erro:
        await ctx.send(erro)
        return

    data = datetime.now(PORTUGAL).strftime("%d/%m/%Y")
    if not faltam:
        await ctx.send(f"✅ Todos os membros com o cargo **{nome_cargo}** votaram!\n📅 {data}")
    else:
        texto = f"📅 **{data}**\n\n❌ **Membros com o cargo {nome_cargo} que ainda não votaram ({len(faltam)}):**\n\n"
        texto += "\n".join(faltam)
        await ctx.send(texto)

# ==========================
# TAREFAS AUTOMÁTICAS
# ==========================

@tasks.loop(time=time(hour=0, minute=1, tzinfo=PORTUGAL))
async def votacao_automatica():
    for canal_id in CONFIGS.keys():
        canal = await obter_canal_seguro(canal_id)
        if canal is not None:
            try:
                await criar_votacao_no_canal(canal)
            except Exception as e:
                print(f"Erro na votação diária: {e}")

@tasks.loop(time=time(hour=14, minute=0, tzinfo=PORTUGAL))
async def verificar_nao_votaram():
    for canal_id, info in CONFIGS.items():
        canal = await obter_canal_seguro(canal_id)
        if canal is None:
            continue

        nome_cargo = info["cargo"]
        try:
            faltam, erro = await obter_nao_votaram(canal, nome_cargo)
            if erro:
                continue

            data = datetime.now(PORTUGAL).strftime("%d/%m/%Y")
            if not faltam:
                await canal.send(f"✅ Todos com o cargo **{nome_cargo}** votaram!\n📅 {data}")
            else:
                texto = f"📅 **{data}**\n\n❌ **Membros com o cargo {nome_cargo} que ainda não votaram ({len(faltam)}):**\n\n"
                texto += "\n".join(faltam)
                await canal.send(texto)
        except Exception as e:
            print(f"Erro ao verificar votações: {e}")

bot.run(TOKEN)
