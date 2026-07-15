import discord
from discord.ext import commands, tasks
from datetime import datetime, time
from zoneinfo import ZoneInfo
import os
import traceback

# =====================================================
# TOKEN
# =====================================================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("A variável DISCORD_TOKEN não foi encontrada.")

# =====================================================
# FUSO HORÁRIO
# =====================================================

PORTUGAL = ZoneInfo("Europe/Lisbon")

# =====================================================
# CONFIGURAÇÃO DOS SERVIDORES
# =====================================================

CONFIGS = {
    1519822701936771244: {
        "cargo": "[🧢] Contratado"
    },

    1478143333351162150: {
        "cargo": "[🧢] Caixa Baixa"
    }
}

# =====================================================
# INTENTS
# =====================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# Guarda as mensagens da votação de cada canal
mensagens_votacao = {}
# =====================================================
# FUNÇÕES AUXILIARES
# =====================================================

async def obter_canal(canal_id):
    canal = bot.get_channel(canal_id)

    if canal is None:
        try:
            canal = await bot.fetch_channel(canal_id)
        except Exception:
            return None

    return canal


async def criar_votacao(canal):

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


async def quem_nao_votou(canal, nome_cargo):

    if canal.id not in mensagens_votacao:
        return None, "❌ Ainda não existe nenhuma votação neste canal."

    cargo = discord.utils.get(
        canal.guild.roles,
        name=nome_cargo
    )

    if cargo is None:
        return None, f"❌ Cargo '{nome_cargo}' não encontrado."

    votaram = set()

    for msg_id in mensagens_votacao[canal.id]:

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
    # =====================================================
# EVENTOS
# =====================================================

@bot.event
async def on_ready():

    print("=" * 50)
    print(f"✅ Bot ligado como {bot.user}")
    print("=" * 50)

    for guild in bot.guilds:
        try:
            await guild.chunk()
        except Exception:
            pass

    if not votacao_automatica.is_running():
        votacao_automatica.start()

    if not verificar_nao_votaram.is_running():
        verificar_nao_votaram.start()

    print(f"📅 Próxima votação: {votacao_automatica.next_iteration}")
    print(f"📋 Próxima verificação: {verificar_nao_votaram.next_iteration}")


# =====================================================
# COMANDO !VOTACAO
# =====================================================

@bot.command()
async def votacao(ctx):

    if ctx.channel.id not in CONFIGS:
        await ctx.send("❌ Este canal não está configurado.")
        return

    await criar_votacao(ctx.channel)

    await ctx.send("✅ Votação criada com sucesso.")


# =====================================================
# COMANDO !NAOVOTARAM
# =====================================================

@bot.command()
async def naovotaram(ctx):

    if ctx.channel.id not in CONFIGS:
        await ctx.send("❌ Este canal não está configurado.")
        return

    cargo = CONFIGS[ctx.channel.id]["cargo"]

    async with ctx.typing():

        faltam, erro = await quem_nao_votou(
            ctx.channel,
            cargo
        )

    if erro:
        await ctx.send(erro)
        return

    data = datetime.now(PORTUGAL).strftime("%d/%m/%Y")

    if not faltam:

        embed = discord.Embed(
            title="✅ Todos votaram",
            description=(
                f"Todos os membros com o cargo **{cargo}** votaram.\n\n"
                f"📅 {data}"
            ),
            color=0x2ecc71
        )

        await ctx.send(embed=embed)

    else:

        embed = discord.Embed(
            title="❌ Ainda não votaram",
            description="\n".join(faltam),
            color=0xe74c3c
        )

        embed.set_footer(
            text=f"{len(faltam)} membro(s) • {data}"
        )

        await ctx.send(embed=embed)
        # =====================================================
# VOTAÇÃO AUTOMÁTICA (00:01)
# =====================================================

@tasks.loop(time=time(hour=0, minute=1, tzinfo=PORTUGAL))
async def votacao_automatica():

    print("📅 A criar votação automática...")

    for canal_id in CONFIGS:

        canal = await obter_canal(canal_id)

        if canal is None:
            print(f"❌ Canal {canal_id} não encontrado.")
            continue

        try:

            await criar_votacao(canal)

            print(f"✅ Votação criada em #{canal.name}")

        except Exception:

            print(f"❌ Erro ao criar votação no canal {canal_id}")
            traceback.print_exc()


@votacao_automatica.before_loop
async def before_votacao():

    await bot.wait_until_ready()
    # =====================================================
# VERIFICAR QUEM NÃO VOTOU (14:00)
# =====================================================

@tasks.loop(time=time(hour=14, minute=0, tzinfo=PORTUGAL))
async def verificar_nao_votaram():

    print("🔍 A verificar quem não votou...")

    for canal_id, info in CONFIGS.items():

        canal = await obter_canal(canal_id)

        if canal is None:
            print(f"❌ Canal {canal_id} não encontrado.")
            continue

        try:

            faltam, erro = await quem_nao_votou(
                canal,
                info["cargo"]
            )

            if erro:
                print(erro)
                continue

            data = datetime.now(PORTUGAL).strftime("%d/%m/%Y")

            if not faltam:

                embed = discord.Embed(
                    title="✅ Todos votaram",
                    description=(
                        f"Todos os membros com o cargo **{info['cargo']}** votaram.\n\n"
                        f"📅 {data}"
                    ),
                    color=0x2ecc71
                )

                await canal.send(embed=embed)

            else:

                embed = discord.Embed(
                    title="❌ Ainda não votaram",
                    description="\n".join(faltam),
                    color=0xe74c3c
                )

                embed.add_field(
                    name="Cargo",
                    value=info["cargo"],
                    inline=False
                )

                embed.add_field(
                    name="Total",
                    value=str(len(faltam)),
                    inline=True
                )

                embed.set_footer(text=data)

                await canal.send(embed=embed)

        except Exception:
            print(f"❌ Erro ao verificar o canal {canal_id}")
            traceback.print_exc()


@verificar_nao_votaram.before_loop
async def before_verificar():

    await bot.wait_until_ready()
    # =====================================================
# INICIAR BOT
# =====================================================

if __name__ == "__main__":

    print("=" * 50)
    print("🚀 A iniciar o bot...")
    print("=" * 50)

    try:
        bot.run(TOKEN)

    except discord.LoginFailure:
        print("❌ Token inválido.")
        traceback.print_exc()

    except Exception:
        print("❌ Erro ao iniciar o bot.")
        traceback.print_exc()
