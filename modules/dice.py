"""
Dice roll command module
"""
import random

async def dice_command(ctx, sides=6):
    """Roll a dice with specified sides"""
    try:
        sides = int(sides)
        if sides < 2 or sides > 100:
            await ctx.send("🎲 Dice must have between 2 and 100 sides!")
            return
        
        result = random.randint(1, sides)
        await ctx.send(f"🎲 {ctx.author.name} rolled a {result} (1-{sides})")
        
        if hasattr(ctx.bot, 'log_queue'):
            ctx.bot.log_queue.put(f"🎲 [DICE] {ctx.author.name} rolled {result} on d{sides}")
            
    except ValueError:
        await ctx.send("🎲 Please provide a valid number of sides!")

def setup_command(bot, log_queue):
    """Setup function called by module manager"""
    @bot.command(name='dice', aliases=['roll', 'd'])
    async def dice(ctx, *, sides: str = "6"):
        # Clean the input and handle edge cases
        sides = sides.strip()
        
        # Handle empty or whitespace-only input
        if not sides:
            sides = "6"
        
        # Remove invisible Unicode characters
        sides = ''.join(char for char in sides if char.isprintable())
        
        # If still empty after cleaning, default to 6
        if not sides:
            sides = "6"
        
        await dice_command(ctx, sides)
    
    log_queue.put(f"✅ [DICE] Command registered")

def cleanup_command(bot):
    """Cleanup function for module reload"""
    if hasattr(bot, 'commands'):
        bot.remove_command('dice')
        bot.remove_command('roll')
        bot.remove_command('d')