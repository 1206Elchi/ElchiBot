from configs import get_config, get_command_config, is_command_enabled

async def ping_command(ctx):
    """Simple ping command"""
    await ctx.send("🏓 Pong!")
    # Log zur Queue senden
    if hasattr(ctx.bot, 'log_queue'):
        ctx.bot.log_queue.put(f"🎯 [PING] Command executed by {ctx.author.name} in {ctx.channel.name}")

def setup_command(bot, log_queue):
    """Setup function called by module manager"""
    @bot.command(name='ping')
    async def ping(ctx):
        await ping_command(ctx)
    
    log_queue.put(f"✅ [PING] Command registered")

def cleanup_command(bot):
    """Cleanup function for module reload"""
    if hasattr(bot, 'commands') and 'ping' in bot.commands:
        bot.remove_command('ping')