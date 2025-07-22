from .elchcoins import coinmanager

async def rank_command(ctx):
    coins = coinmanager.get_user_points(f"{ctx.author.name}")
    if coins < 100 or coins == 100:
        await ctx.send(f'{ctx.author.name} rank is "newbe". Welcome in the Chat! ❤️')
    elif coins > 100 and coins <= 500:
        await ctx.send(f'{ctx.author.name} rank is "novice". Thanks for showing up! 🥳')
    elif coins > 500 and coins <= 1000:
        await ctx.send(f'{ctx.author.name} rank is "watcher". Thanks for actually Watching! 😊')
    elif coins > 1000 and coins <= 2000:
        await ctx.send(f'{ctx.author.name} rank is "Viewer". Someone seems to actually like my Stream 📺')
    elif coins > 2000 and coins <= 5000:
        await ctx.send(f'{ctx.author.name} rank is "master". Playing Ranked now huh?')
    elif coins > 5000 and coins <= 7500:
        await ctx.send(f'{ctx.author.name} rank is "elite". Going into E-Sports now it seems like? 🏆')
    elif coins > 7500 and coins <= 10000:
        await ctx.send(f'{ctx.author.name} rank is "Legend". You are on top! but maybe it goes higher ; )')
        await ctx.send(f'{ctx.author.name} rank is "Jobless". I dont think I have to say more... you are CRAZY!')
    
    if hasattr(ctx.bot, 'log_queue'):
        ctx.bot.log_queue.put(f"[RANK] Command executed by {ctx.author.name} in {ctx.channel.name}")

async def ranks_command(ctx):
    await ctx.send('There are the following Ranks: "newbe", "novice", "watcher", "Viewer", "elite", "Legend" Good Luck!')
    if hasattr(ctx.bot, 'log_queue'):
        ctx.bot.log_queue.put(f"[RANK] Command executed by {ctx.author.name} in {ctx.channel.name}")

def setup_command(bot, log_queue):
    @bot.command(name='rank')
    async def rank(ctx):
        await rank_command(ctx)
    
    log_queue.put(f"✅ [RANK] Command registered")

    @bot.command(name='ranks')
    async def ranks(ctx):
        await ranks_command(ctx)
    
    log_queue.put(f"✅ [RANK] Command registered")

def cleanup_command(bot):
    if hasattr(bot, 'commands') and 'rank' in bot.commands:
        bot.remove_command('rank')
    if hasattr(bot, 'commands') and 'ranks' in bot.commands:
        bot.remove_command('ranks')