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

# Dicionário com as configurações de cada canal/servidor
CONFIGS = {
    1519822701936771244: {
        "cargo": "[🧢] Contratado"
    },
    1526617431022370868: {
        "cargo": "[🧢] Caixa Baixa"
    }
}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True  # Garante acesso correto às informações dos servidores

bot = commands.Bot(command_prefix="!", intents=intents)

# Agora guardamos as mensagens por Canal ID -> ex: { 1519822701936...: [id1, id2, ...] }
mensagens_votacao = {}

# ==========================
# FUNÇÕES AUXILIARES
# ==========================

async def criar_votacao_no_canal(canal):
    """Cria a votação num canal específico e guarda os IDs das mensagens."""
    mensagens_votacao[canal.id] = []
    
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
        mensagens_votacao[canal.id].append(msg.id)

        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await msg.add_reaction("❓")

async def obter_nao_votaram(canal, nome_cargo):
    """Calcula quem ainda não votou num determinado canal com base no cargo."""
    msg_ids = mensagens_votacao.get(canal.id, [])
    if not msg_ids:
        return None, "❌ Ainda não existe nenhuma votação ativa neste canal."

    cargo = discord.utils.get(canal.guild.roles, name=nome_cargo)
    if cargo is None:
        return None, f"❌ Cargo '{nome_cargo}' não encontrado neste servidor."

    votaram = set()

    for msg_id in msg_ids:
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

    return faltam, None

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
    # Verifica se o canal atual está configurado
    if ctx.channel.id not in CONFIGS:
        await ctx.send("❌ Este canal não está configurado para votações automáticas.")
        return

    await ctx.send("🔄 A iniciar votação manualmente...")
    await criar_votacao_no_canal(ctx.channel)

# ==========================
# COMANDO !NAOVOTARAM
# ==========================

@bot.command()
async def naovotaram(ctx):
    if ctx.channel.id not in CONFIGS:
        await ctx.send("❌ Este canal não está configurado para o controlo de votações.")
        return

    nome_cargo = CONFIGS[ctx.channel.id]["cargo"]
    
    # Mostra um aviso rápido de "a carregar" pois ler reações pode demorar alguns segundos
    async with ctx.typing():
        faltam, erro = await obter_nao_votaram(ctx.channel, nome_cargo)

    if erro:
        await ctx.send(erro)
        return

    data = datetime.now().strftime("%d/%m/%Y")

    if not faltam:
        await ctx.send(f"✅ Todos os membros com o cargo **{nome_cargo}** votaram!\n📅 {data}")
    else:
        texto = (
            f"📅 **{data}**\n\n"
            f"❌ **Membros com o cargo {nome_cargo} que ainda não votaram ({len(faltam)}):**\n\n"
        )
        texto += "\n".join(faltam)
        await ctx.send(texto)

# ==========================
# VOTAÇÃO AUTOMÁTICA (00:01)
# ==========================

@tasks.loop(time=time(hour=0, minute=1, tzinfo=PORTUGAL))
async def votacao_automatica():
    for canal_id in CONFIGS.keys():
        canal = bot.get_channel(canal_id)
        if canal is None:
            continue
        try:
            await criar_votacao_no_canal(canal)
        except Exception as e:
            print(f"Erro ao criar votação automática no canal {canal_id}: {e}")

# ==========================
# VERIFICAR QUEM NÃO VOTOU (14:00)
# ==========================

@tasks.loop(time=time(hour=14, minute=0, tzinfo=PORTUGAL))
async def verificar_nao_votaram():
    for canal_id, info in CONFIGS.items():
        canal = bot.get_channel(canal_id)
        if canal is None:
            continue

        nome_cargo = info["cargo"]
        faltam, erro = await obter_nao_votaram(canal, nome_cargo)

        if erro:
            continue  # Se houver erro (ex: votação não iniciada), ignora este canal

        data = datetime.now().strftime("%d/%m/%Y")

        if not faltam:
            await canal.send(f"✅ Todos os membros com o cargo **{nome_cargo}** votaram!\n📅 {data}")
        else:
            texto = (
                f"📅 **{data}**\n\n"
                f"❌ **Membros com o cargo {nome_cargo} que ainda não votaram ({len(faltam)}):**\n\n"
            )
            texto += "\n".join(faltam)
            await canal.send(texto)

# ==========================
# INICIAR BOT
# ==========================

bot.run(TOKEN)
