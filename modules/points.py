from .elchcoins import coinmanager

async def coin_command(ctx):
    username = ctx.author.name
    points = coinmanager.get_user_points(username)
    await ctx.send(f"{username}, du hast {points} Elchcoins 💰")

    if hasattr(ctx.bot, 'log_queue'):
        ctx.bot.log_queue.put(f"[POINTS] Command executed by {username} in {ctx.channel.name}")

def setup_command(bot, log_queue):
    """Setup function called by module manager"""
    @bot.command(name='coins')
    async def coins(ctx):
        await coin_command(ctx)
    
    log_queue.put(f"✅ [POINTS] Command registered")

    @bot.command(name='top')
    async def top(ctx):
        top_users = coinmanager.get_top_users(3)
        if not top_users:
            await ctx.send("Noch keine Punkte vergeben.")
            return

        msg = "🏆 Top 3 User: " + " | ".join([f"{u[0]}: {u[1]}" for u in top_users])
        await ctx.send(msg)

    log_queue.put(f"✅ [POINTS] Command registered")

def cleanup_command(bot):
    """Cleanup function for module reload"""
    if hasattr(bot, 'commands') and 'coins' in bot.commands:
        bot.remove_command('coins')
    if hasattr(bot, 'commands') and 'top' in bot.commands:
        bot.remove_command('top')