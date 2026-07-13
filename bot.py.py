import discord
from discord.ext import commands
from datetime import datetime

import os

TOKEN = os.getenv("MTUyNjI0NDQ4MDg2MzE3NDc0Nw.Gol6ZW.p6gQd9MBwQ5WXLWcFqODaUVi3cGBRPTrzeri1c")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

mensagens_votacao = []

@bot.event
async def on_ready():
    print(f"✅ Bot ligado como {bot.user}")

@bot.command()
async def votacao(ctx):
    global mensagens_votacao
    mensagens_votacao.clear()

    data = datetime.now().strftime("%d/%m/%Y")

    embed = discord.Embed(
        title="📅 Votação de Disponibilidade",
        description=f"**Data:** {data}\n\nReage em cada horário:\n\n✅ = Sim\n❌ = Não\n❓ = Talvez",
        color=0x2ecc71
    )

    await ctx.send(embed=embed)

    horas = list(range(13,24)) + [0]

    for hora in horas:
        msg = await ctx.send(f"**{hora:02d}:00**")
        mensagens_votacao.append(msg.id)

        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await msg.add_reaction("❓")

@bot.command()
async def naovotaram(ctx):

    if not mensagens_votacao:
        await ctx.send("❌ Ainda não existe nenhuma votação.")
        return

    cargo = discord.utils.find(
        lambda r: "Contratado" in r.name,
        ctx.guild.roles
    )

    if cargo is None:
        await ctx.send("❌ Cargo 'Contratado' não encontrado.")
        return

    votaram = set()

    for msg_id in mensagens_votacao:
        mensagem = await ctx.channel.fetch_message(msg_id)

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
        texto = f"📅 **{data}**\n\n❌ **Contratados que ainda não votaram ({len(faltam)}):**\n\n"
        texto += "\n".join(faltam)

        await ctx.send(texto)

bot.run(TOKEN)