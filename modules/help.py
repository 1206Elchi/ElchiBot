async def help_command(ctx):
    await ctx.send("❓| Use \"%\" as Präfix before one of my Custom Commands like %song, %coins or %rank! Have Fun Chatting! There also will be Chat Interactive Things/Games sometimes : )")

    if hasattr(ctx.bot, 'log_queue'):
        ctx.bot.log_queue.put(f"[HELP] Command executed by {ctx.author.name} in {ctx.channel.name}")

def setup_command(bot, log_queue):
    @bot.command(name='help')
    async def help(ctx):
        await help_command(ctx)
    
    log_queue.put(f"✅ [HELP] Command registered")

def cleanup_command(bot):
    if hasattr(bot, 'commands') and 'help' in bot.commands:
        bot.remove_command('help')