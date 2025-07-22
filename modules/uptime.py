"""
Uptime command module
"""
import time
from datetime import datetime, timedelta

start_time = None

async def uptime_command(ctx):
    """Show bot uptime"""
    if start_time is None:
        await ctx.send("⏰ Uptime tracking not available")
        return
    
    uptime_seconds = time.time() - start_time
    uptime_delta = timedelta(seconds=int(uptime_seconds))
    
    # Format uptime
    days = uptime_delta.days
    hours, remainder = divmod(uptime_delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        uptime_str = f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        uptime_str = f"{minutes}m {seconds}s"
    else:
        uptime_str = f"{seconds}s"
    
    await ctx.send(f"⏰ Bot uptime: {uptime_str}")
    
    if hasattr(ctx.bot, 'log_queue'):
        ctx.bot.log_queue.put(f"⏰ [UPTIME] Uptime requested by {ctx.author.name}")

def setup_command(bot, log_queue):
    """Setup function called by module manager"""
    global start_time
    start_time = time.time()
    
    @bot.command(name='uptime')
    async def uptime(ctx):
        await uptime_command(ctx)
    
    log_queue.put(f"✅ [UPTIME] Command registered")

def cleanup_command(bot):
    """Cleanup function for module reload"""
    if hasattr(bot, 'commands') and 'uptime' in bot.commands:
        bot.remove_command('uptime')