import asyncio
import traceback
from .elchcoins import coinmanager

# Globale Variablen
auto_reward_task = None
active_users = set()

async def auto_reward_loop(bot, log_queue):
    """Gibt alle 10 Minuten allen aktiven Usern 10 Punkte"""
    while True:
        try:
            await asyncio.sleep(600)  # 10 Minuten = 600 Sekunden
            
            if active_users:
                reward_count = 0
                for username in active_users.copy():
                    try:
                        coinmanager.give_user_points(username, 10)
                        reward_count += 1
                    except Exception as e:
                        log_queue.put(f"[AUTO-REWARD] Error giving points to {username}: {str(e)}")
                
                log_queue.put(f"[AUTO-REWARD] Gave 10 points to {reward_count} active users")
                
                # Optional: Nachricht in den Chat senden
                # try:
                #     for channel in bot.connected_channels:
                #         await channel.send(f"🎁 Auto-Reward: {reward_count} active users received 10 Coins!")
                # except Exception as e:
                #     log_queue.put(f"[AUTO-REWARD] Error sending chat message: {str(e)}")
                
                # Reset active users für nächste Runde (optional)
                active_users.clear()
            else:
                log_queue.put("[AUTO-REWARD] No active users found")
                
        except Exception as e:
            log_queue.put(f"[AUTO-REWARD] Error in auto_reward_loop: {str(e)}")
            log_queue.put(f"[AUTO-REWARD] Full traceback: {traceback.format_exc()}")
            await asyncio.sleep(60)  # Warte 1 Minute bei Fehler

def add_active_user(username, log_queue):
    """Fügt User zur aktiven User-Liste hinzu"""
    if username not in active_users:
        active_users.add(username)
        log_queue.put(f"[AUTO-REWARD] Added {username} to active users")

async def handle_follow(follower, bot, log_queue):
    """Gibt neuen Followern 100 Punkte"""
    try:
        username = follower.name
        log_queue.put(f"[DEBUG] Processing follow from: {username}")
        
        # Prüfe aktuelle Punkte vor der Belohnung
        try:
            current_points = coinmanager.get_user_points(username)
            log_queue.put(f"[DEBUG] {username} had {current_points} points before follow reward")
        except Exception as e:
            log_queue.put(f"[DEBUG] Could not get current points for {username}: {str(e)}")
            current_points = 0
        
        # Gebe 100 Punkte
        coinmanager.give_user_points(username, 100)
        
        # Verifiziere dass Punkte hinzugefügt wurden
        try:
            new_points = coinmanager.get_user_points(username)
            log_queue.put(f"[DEBUG] {username} now has {new_points} points after follow reward")
        except Exception as e:
            log_queue.put(f"[DEBUG] Could not verify new points for {username}: {str(e)}")
        
        log_queue.put(f"[AUTO-REWARD] ✅ Gave 100 points to new follower: {username}")
        
        # Optional: Dankesnachricht im Chat
        try:
            for channel in bot.connected_channels:
                await channel.send(f"🎉 Thanks for the follow, {username}! You received 100 Coins!")
        except Exception as e:
            log_queue.put(f"[AUTO-REWARD] Error sending follow message: {str(e)}")
            
    except Exception as e:
        log_queue.put(f"[AUTO-REWARD] Follow reward error: {str(e)}")
        log_queue.put(f"[AUTO-REWARD] Full traceback: {traceback.format_exc()}")

async def status_command(ctx):
    """Zeigt Status des Auto-Reward Systems"""
    try:
        active_count = len(active_users)
        active_list = list(active_users)[:10]  # Zeige nur erste 10 User
        
        status_msg = f"🎁 Auto-Reward Status: {active_count} active users tracked"
        if active_list:
            status_msg += f"\nRecent active users: {', '.join(active_list)}"
            if active_count > 10:
                status_msg += f" (and {active_count - 10} more...)"
        
        await ctx.send(status_msg)
        
        if hasattr(ctx.bot, 'log_queue'):
            ctx.bot.log_queue.put(f"[AUTO-REWARD] Status command executed by {ctx.author.name}")
    except Exception as e:
        await ctx.send(f"❌ Error getting status: {str(e)}")
        if hasattr(ctx.bot, 'log_queue'):
            ctx.bot.log_queue.put(f"[AUTO-REWARD] Status command error: {str(e)}")

def setup_command(bot, log_queue):
    """Initialisiert das Auto-Reward System"""
    global auto_reward_task
    
    try:
        # Starte Auto-Reward Loop
        auto_reward_task = asyncio.create_task(auto_reward_loop(bot, log_queue))
        log_queue.put("[AUTO-REWARD] Auto-reward loop started")
        
        # Follow Event Handler - Mehrere Methoden für verschiedene Libraries
        log_queue.put("[AUTO-REWARD] Registering follow event handler...")
        
        # Methode 1: Direkte Event-Handler Zuweisung
        async def on_follow(follower):
            log_queue.put(f"[AUTO-REWARD] Follow event triggered for: {follower.name}")
            await handle_follow(follower, bot, log_queue)
        
        # Versuche verschiedene Event-Registration Methoden
        if hasattr(bot, 'event'):
            # Twitchio Style
            @bot.event()
            async def event_follow(follower):
                await on_follow(follower)
            log_queue.put("[AUTO-REWARD] Registered follow handler via @bot.event()")
            
        elif hasattr(bot, 'add_event_handler'):
            # Alternative Event Handler Registration
            bot.add_event_handler('event_follow', on_follow)
            log_queue.put("[AUTO-REWARD] Registered follow handler via add_event_handler")
            
        else:
            # Direkte Zuweisung
            bot.event_follow = on_follow
            log_queue.put("[AUTO-REWARD] Registered follow handler via direct assignment")
        
        # Registriere Status Command
        @bot.command(name='autoreward')
        async def autoreward(ctx):
            await status_command(ctx)
        
        log_queue.put("✅ [AUTO-REWARD] Module loaded successfully")
        
        # Test-Follow für Debugging (optional)
        # log_queue.put("[AUTO-REWARD] Module ready. Test follow events to verify functionality.")
        
    except Exception as e:
        log_queue.put(f"❌ [AUTO-REWARD] Setup error: {str(e)}")
        log_queue.put(f"[AUTO-REWARD] Full traceback: {traceback.format_exc()}")

def cleanup_command(bot, log_queue=None):
    """Beendet das Auto-Reward System sauber"""
    global auto_reward_task
    
    try:
        # Stoppe Auto-Reward Loop
        if auto_reward_task:
            auto_reward_task.cancel()
            auto_reward_task = None
            if log_queue:
                log_queue.put("[AUTO-REWARD] Auto-reward loop stopped")
        
        # Entferne Commands
        if hasattr(bot, 'commands') and 'autoreward' in bot.commands:
            bot.remove_command('autoreward')
            if log_queue:
                log_queue.put("[AUTO-REWARD] Removed autoreward command")
        
        # Leere aktive User-Liste
        active_users.clear()
        if log_queue:
            log_queue.put("[AUTO-REWARD] Cleared active users list")
            log_queue.put("✅ [AUTO-REWARD] Module cleanup completed")
            
    except Exception as e:
        if log_queue:
            log_queue.put(f"❌ [AUTO-REWARD] Cleanup error: {str(e)}")

# Zusätzliche Utility-Funktionen
def get_active_users():
    """Gibt die Liste der aktiven User zurück"""
    return list(active_users)

def clear_active_users(log_queue=None):
    """Leert die Liste der aktiven User"""
    count = len(active_users)
    active_users.clear()
    if log_queue:
        log_queue.put(f"[AUTO-REWARD] Cleared {count} active users")

def is_auto_reward_running():
    """Prüft ob das Auto-Reward System läuft"""
    return auto_reward_task is not None and not auto_reward_task.done()

# Debug-Funktion für manuelles Testen
async def test_follow_reward(username, bot, log_queue):
    """Testet das Follow-Reward System manuell"""
    class MockFollower:
        def __init__(self, name):
            self.name = name
    
    mock_follower = MockFollower(username)
    await handle_follow(mock_follower, bot, log_queue)
    log_queue.put(f"[AUTO-REWARD] Test follow reward executed for {username}")

# Zusätzlicher Command für Admin-Funktionen
async def admin_command(ctx, action, *args):
    """Admin-Command für Auto-Reward System"""
    try:
        if not hasattr(ctx.bot, 'log_queue'):
            await ctx.send("❌ Log queue not available")
            return
        
        log_queue = ctx.bot.log_queue
        
        if action == "status":
            await status_command(ctx)
        elif action == "clear":
            clear_active_users(log_queue)
            await ctx.send(f"✅ Cleared active users list")
        elif action == "test" and args:
            username = args[0]
            await test_follow_reward(username, ctx.bot, log_queue)
            await ctx.send(f"✅ Test follow reward sent to {username}")
        elif action == "running":
            is_running = is_auto_reward_running()
            await ctx.send(f"🔄 Auto-reward is {'running' if is_running else 'stopped'}")
        else:
            await ctx.send("❌ Unknown action. Use: status, clear, test <username>, running")
            
    except Exception as e:
        await ctx.send(f"❌ Admin command error: {str(e)}")
        if hasattr(ctx.bot, 'log_queue'):
            ctx.bot.log_queue.put(f"[AUTO-REWARD] Admin command error: {str(e)}")