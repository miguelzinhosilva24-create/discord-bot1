import discord
from discord.ext import commands, tasks
from datetime import datetime, time, timedelta, timezone
import os
import traceback

# COLA O TEU TOKEN DO DISCORD DENTRO DAS ASPAS ABAIXO:
TOKEN = "MTUyNjI0NDQ4MDg2MzE3NDc0Nw.Gol6ZW.p6gQd9MBwQ5WXLWcFqODaUVi3cGBRPTrzeri1c"

# ==========================
# CONFIGURAÇÕES
# ==========================

# Evita erros de fuso horário em ambientes Linux sem a biblioteca tzdata
try:
    from zoneinfo import ZoneInfo
    PORTUGAL = ZoneInfo("Europe/Lisbon")
except Exception:
    # Fallback automático para UTC+1 (Portugal Continental na maioria do ano)
    PORTUGAL = timezone(timedelta(hours=1))

# Configurações de cada canal e o seu respetivo cargo (Separados por servidor)
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

# Guarda as mensagens de votação por canal -> { canal_id: [id_msg1, id_msg2, ...] }
mensagens_votacao = {}

# ==========================
# FUNÇÕES AUXILIARES
# ==========================

async def obter_canal_seguro(canal_id):
    """Procura o canal no cache do bot. Se não encontrar, força a procura via API."""
    canal = bot.get_channel(canal_id)
    if canal is None:
        try:
            canal = await bot.fetch_channel(canal_id)
        except Exception:
            return None
    return canal

async def criar_votacao_no_canal(canal):
    """Gera o painel de votação no canal pretendido e armazena os IDs das mensagens."""
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
    """Varre as reações do canal e devolve a lista de menções dos membros que não votaram."""
    msg_ids = mensagens_votacao.get(canal.id, [])
    if not msg_ids:
        return None, "❌ Não há nenhuma votação ativa registada na memória do bot para este canal. Usa `!votacao` primeiro."

    # Força a atualização da lista de membros do servidor se ainda não foi feita
    if not canal.guild.chunked:
        await canal.guild.chunk()

    cargo = discord.utils.get(canal.guild.roles, name=nome_cargo)
    if cargo is None:
        return None, f"❌ Cargo '{nome_cargo}' não foi encontrado neste servidor. Verifica se o nome está idêntico."

    votaram = set()

    for msg_id in msg_ids:
        try:
            mensagem = await canal.fetch_message(msg_id)
        except discord.Forbidden:
            return None, "❌ O bot não tem permissão para ler o histórico de mensagens neste canal."
        except discord.NotFound:
            continue
        except Exception as e:
            return None, f"❌ Erro ao ler mensagem {msg_id}: {str(e)}"

        for reaction in mensagem.reactions:
            async for user in reaction.users():
                if not user.bot:
                    votaram.add(user.id)

    # Filtra quem tem o cargo mas não votou
    faltam = []
    membros_cargo = cargo.members
    
    if not membros_cargo:
        return None, f"⚠️ O bot detetou 0 membros com o cargo `{nome_cargo}` neste servidor. Garante que os 'Intents de Membros' estão ativados no Developer Portal do Discord."

    for membro in membros_cargo:
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
    
    # Carrega todos os membros de cada servidor em cache ao iniciar
    for guild in bot.guilds:
        await guild.chunk()
        print(f"📦 Servidor carregado com sucesso: {guild.name} (Membros: {guild.member_count})")

    # Verifica o estado dos canais configurados
    for canal_id in CONFIGS.keys():
        canal = await obter_canal_seguro(canal_id)
        if canal is None:
            print(f"⚠️ Alerta: O bot não conseguiu encontrar ou aceder ao canal ID: {canal_id}")
        else:
            print(f"⭐ Canal detetado com sucesso: #{canal.name} no servidor '{canal.guild.name}'")

    if not votacao_automatica.is_running():
        votacao_automatica.start()

    if not verificar_nao_votaram.is_running():
        verificar_nao_votaram.start()

# ==========================
# COMANDO !VOTACAO
# ==========================

@bot.command()
async def votacao(ctx):
    if ctx.channel.id not in CONFIGS:
        await ctx.send("❌ Este canal não está configurado nas definições do bot.")
        return

    try:
        await ctx.send("🔄 A iniciar votação...")
        await criar_votacao_no_canal(ctx.channel)
    except Exception as e:
        await ctx.send(f"❌ Erro ao criar votação: `{str(e)}`")
        traceback.print_exc()

# ==========================
# COMANDO !NAOVOTARAM
# ==========================

@bot.command()
async def naovotaram(ctx):
    if ctx.channel.id not in CONFIGS:
        await ctx.send("❌ Este canal não está configurado para o controlo de votações.")
        return

    nome_cargo = CONFIGS[ctx.channel.id]["cargo"]
    
    async with ctx.typing():
        try:
            faltam, erro = await obter_nao_votaram(ctx.channel, nome_cargo)
        except Exception as e:
            await ctx.send(f"❌ Ocorreu um erro crítico no comando: `{str(e)}`")
            traceback.print_exc()
            return

    if erro:
        await ctx.send(erro)
        return

    data = datetime.now(PORTUGAL).strftime("%d/%m/%Y")

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
        canal = await obter_canal_seguro(canal_id)
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
                await canal.send(f"✅ Todos os membros com o cargo **{nome_cargo}** votaram!\n📅 {data}")
            else:
                texto = (
                    f"📅 **{data}**\n\n"
                    f"❌ **Membros com o cargo {nome_cargo} que ainda não votaram ({len(faltam)}):**\n\n"
                )
                texto += "\n".join(faltam)
                await canal.send(texto)
        except Exception as e:
            print(f"Erro ao verificar não votaram no canal {canal_id}: {e}")

# ==========================
# INICIAR BOT
# ==========================

bot.run(TOKEN)
