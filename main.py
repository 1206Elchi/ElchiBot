# main.py
import os
import sys
import threading
import time
import importlib
import inspect
from pathlib import Path
from dotenv import load_dotenv
from colorama import *
from twitchio.ext import commands
import multiprocessing
from queue import Queue
import signal
import asyncio
from modules.elchcoins import coinmanager

init()

# Globale Variablen für Input-Buffer
log_queue = Queue()
should_exit = False
input_active = False

def clear_current_line():
    """Löscht die aktuelle Zeile vollständig"""
    sys.stdout.write("\r" + " " * 120 + "\r")
    sys.stdout.flush()

def print_prompt():
    """Zeigt den Input-Prompt"""
    sys.stdout.write(f"{Fore.CYAN}> {Style.RESET_ALL}")
    sys.stdout.flush()

def log_with_buffer(message):
    """Fügt Log-Nachricht zur Queue hinzu"""
    log_queue.put(message)

def fatal_error(message, code):
    log_with_buffer(f"{Fore.RED}[FATAL ERROR]{Style.RESET_ALL} {message}")
    sys.exit(code)

def error(message):
    log_with_buffer(f"{Fore.MAGENTA}[ERROR]{Style.RESET_ALL} {message}")

def success(message):
    log_with_buffer(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")

def info(message):
    log_with_buffer(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} {message}")

def warning(message):
    log_with_buffer(f"{Fore.BLUE}[WARNING]{Style.RESET_ALL} {message}")

def load_env(required_vars):
    load_dotenv()
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        fatal_error(f"Missing environment variables: {', '.join(missing)}", 1)
    success("Environment variables loaded successfully")

required_env_vars = [
    "client_id",
    "client_secret", 
    "access_token",
    "bot_id",
    "owner_id",
    "channel",
    "prefix"
]

class ModuleManager:
    def __init__(self, bot, log_queue):
        self.bot = bot
        self.log_queue = log_queue
        self.modules = {}
        self.modules_path = Path("modules")
        
        # Erstelle modules Ordner falls nicht vorhanden
        self.modules_path.mkdir(exist_ok=True)
        
        # Erstelle __init__.py falls nicht vorhanden
        init_file = self.modules_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("")
    
    def load_modules(self):
        """Lädt alle Module aus dem modules Ordner"""
        if not self.modules_path.exists():
            self.log_queue.put(f"{Fore.YELLOW}[MODULE]{Style.RESET_ALL} Modules directory not found")
            return
        
        # Füge modules zum Python Path hinzu
        sys.path.insert(0, str(self.modules_path.parent))
        
        loaded_count = 0
        for file_path in self.modules_path.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
                
            module_name = file_path.stem
            try:
                # Importiere das Modul
                module = importlib.import_module(f"modules.{module_name}")
                
                # Suche nach setup_command Funktion
                if hasattr(module, 'setup_command'):
                    setup_func = getattr(module, 'setup_command')
                    
                    # Rufe setup_command auf
                    setup_func(self.bot, self.log_queue)
                    
                    self.modules[module_name] = module
                    loaded_count += 1
                    
                    self.log_queue.put(f"{Fore.GREEN}[MODULE]{Style.RESET_ALL} Loaded {module_name}")
                else:
                    self.log_queue.put(f"{Fore.RED}[MODULE]{Style.RESET_ALL} No setup_command found in {module_name}")
                    
            except Exception as e:
                self.log_queue.put(f"{Fore.RED}[MODULE]{Style.RESET_ALL} Failed to load {module_name}: {str(e)}")
        
        self.log_queue.put(f"{Fore.GREEN}[MODULE]{Style.RESET_ALL} Loaded {loaded_count} modules successfully")
    
    def reload_module(self, module_name):
        """Lädt ein spezifisches Modul neu"""
        if module_name not in self.modules:
            self.log_queue.put(f"{Fore.RED}[MODULE]{Style.RESET_ALL} Module {module_name} not found")
            return False
        
        try:
            # Entferne alte Commands
            if hasattr(self.modules[module_name], 'cleanup_command'):
                self.modules[module_name].cleanup_command(self.bot)
            
            # Lade Modul neu
            importlib.reload(self.modules[module_name])
            
            # Setup neue Commands
            if hasattr(self.modules[module_name], 'setup_command'):
                self.modules[module_name].setup_command(self.bot, self.log_queue)
                self.log_queue.put(f"{Fore.GREEN}[MODULE]{Style.RESET_ALL} Reloaded {module_name}")
                return True
            
        except Exception as e:
            self.log_queue.put(f"{Fore.RED}[MODULE]{Style.RESET_ALL} Failed to reload {module_name}: {str(e)}")
        
        return False
    
    def list_modules(self):
        """Listet alle geladenen Module auf"""
        if not self.modules:
            self.log_queue.put(f"{Fore.YELLOW}[MODULE]{Style.RESET_ALL} No modules loaded")
            return
        
        self.log_queue.put(f"{Fore.CYAN}[MODULE]{Style.RESET_ALL} Loaded modules:")
        for module_name in self.modules:
            self.log_queue.put(f"  - {module_name}")

class Bot(commands.Bot):
    def __init__(self, log_queue, command_queue):
        super().__init__(
            token=os.getenv("access_token"),
            client_id=os.getenv("client_id"),
            client_secret=os.getenv("client_secret"),
            bot_id=os.getenv("bot_id"),
            owner_id=os.getenv("owner_id"),
            prefix=os.getenv("prefix"),
            initial_channels=[c.strip() for c in os.getenv("channel").split(",") if c.strip()]
        )
        self.log_queue = log_queue
        self.command_queue = command_queue
        self.module_manager = ModuleManager(self, log_queue)
        self.running = True

    async def event_ready(self):
        channels = ", ".join([channel.name for channel in self.connected_channels])
        self.log_queue.put(f"{Fore.GREEN}[BOT]{Style.RESET_ALL} Connected as {Fore.CYAN}{self.nick}{Style.RESET_ALL} to channels: {Fore.YELLOW}{channels}{Style.RESET_ALL}")
        
        # Lade Module nach Bot-Start
        self.module_manager.load_modules()
        
        # Starte Command Handler
        asyncio.create_task(self.handle_console_commands())

    async def event_message(self, message):
        if message.echo:
            return
        
        # Auto-Reward: Füge aktive User hinzu
        try:
            from modules.auto_points import add_active_user
            add_active_user(message.author.name, self.log_queue)
        except ImportError:
            pass  # Modul nicht geladen
        except Exception as e:
            self.log_queue.put(f"[AUTO-REWARD] Error adding active user: {str(e)}")
        
        await self.handle_commands(message)
    
    async def handle_console_commands(self):
        """Behandelt Befehle aus der Console"""
        import asyncio
        
        while self.running:
            try:
                if not self.command_queue.empty():
                    command_data = self.command_queue.get_nowait()
                    command = command_data.get('command')
                    args = command_data.get('args', [])
                    
                    if command == 'modules':
                        self.module_manager.list_modules()
                    elif command == 'reload':
                        if args:
                            module_name = args[0]
                            self.module_manager.reload_module(module_name)
                        else:
                            self.log_queue.put(f"{Fore.RED}[MODULE]{Style.RESET_ALL} Usage: reload <module_name>")
                    elif command == 'send':
                        if args:
                            message = args[0]
                            target_channel = args[1] if len(args) > 1 else None
                            
                            if target_channel:
                                # Sende an bestimmten Kanal
                                channel = self.get_channel(target_channel)
                                if channel:
                                    await channel.send(message)
                                    self.log_queue.put(f"{Fore.GREEN}[SEND]{Style.RESET_ALL} Message sent to #{target_channel}")
                                else:
                                    self.log_queue.put(f"{Fore.RED}[SEND]{Style.RESET_ALL} Channel #{target_channel} not found")
                            else:
                                # Sende an alle verbundenen Kanäle
                                for channel in self.connected_channels:
                                    await channel.send(message)
                                self.log_queue.put(f"{Fore.GREEN}[SEND]{Style.RESET_ALL} Message sent to all channels")
                        else:
                            self.log_queue.put(f"{Fore.RED}[SEND]{Style.RESET_ALL} No message provided")
                    elif command == 'exit':
                        self.running = False
                        break
                        
                await asyncio.sleep(0.1)
            except Exception as e:
                self.log_queue.put(f"{Fore.RED}[BOT]{Style.RESET_ALL} Command handler error: {str(e)}")
                await asyncio.sleep(0.1)

def run_bot(log_queue, command_queue):
    import asyncio
    
    try:
        bot = Bot(log_queue, command_queue)
        asyncio.run(bot.run())
    except Exception as e:
        log_queue.put(f"{Fore.RED}[BOT ERROR]{Style.RESET_ALL} {str(e)}")

def log_handler():
    """Behandelt Log-Nachrichten aus der Queue"""
    global input_active
    
    while not should_exit:
        try:
            if not log_queue.empty():
                message = log_queue.get_nowait()
                
                if input_active:
                    clear_current_line()
                
                print(message)
                
                if input_active:
                    print_prompt()
                    
            time.sleep(0.05)
        except:
            break

def print_help():
    """Zeigt verfügbare Befehle an"""
    help_text = f"""
{Fore.CYAN}╔══════════════════════════════════════╗
║              TWITCH BOT              ║
╠══════════════════════════════════════╣
║ Available commands:                  ║
║                                      ║
║ {Fore.YELLOW}help{Fore.CYAN}     - Show this help message    ║
║ {Fore.YELLOW}status{Fore.CYAN}   - Show bot status           ║
║ {Fore.YELLOW}channels{Fore.CYAN} - List connected channels   ║
║ {Fore.YELLOW}modules{Fore.CYAN}  - List loaded modules       ║
║ {Fore.YELLOW}reload{Fore.CYAN}   - Reload a module           ║
║ {Fore.YELLOW}clear{Fore.CYAN}    - Clear console             ║
║ {Fore.YELLOW}exit{Fore.CYAN}     - Stop bot and exit         ║
║                                      ║
║ Press Ctrl+C to force exit           ║
╚══════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(help_text)

def safe_input(command_queue):
    """Sicherer Input Handler"""
    global should_exit, input_active
    
    # Willkommensnachricht
    print(f"\n{Fore.CYAN}╔══════════════════════════════════════╗")
    print(f"║      MODULAR TWITCH BOT CONSOLE      ║")
    print(f"║                                      ║")
    print(f"║ Type '{Fore.YELLOW}help{Fore.CYAN}' for available commands   ║")
    print(f"║ Type '{Fore.YELLOW}exit{Fore.CYAN}' to stop the bot          ║")
    print(f"╚══════════════════════════════════════╝{Style.RESET_ALL}\n")
    
    # Kurz warten für Bot-Connection
    time.sleep(3)
    
    while not should_exit:
        try:
            input_active = True
            print_prompt()
            
            line = input().strip()
            input_active = False
            
            if not line:
                continue
                
            parts = line.split()
            command = parts[0].lower()
            
            if command == "exit":
                info("Stopping bot...")
                command_queue.put({'command': 'exit'})
                should_exit = True
                return "exit"
                
            elif command == "help":
                print_help()
                
            elif command == "status":
                info("Bot is running and connected")
                
            elif command == "channels":
                channels = os.getenv("channel", "").split(",")
                channels_clean = [c.strip() for c in channels if c.strip()]
                info(f"Connected to channels: {', '.join(channels_clean)}")
                
            elif command == "modules":
                command_queue.put({'command': 'modules'})
                
            elif command == "reload":
                if len(parts) < 2:
                    error("Usage: reload <module_name>")
                else:
                    module_name = parts[1]
                    command_queue.put({'command': 'reload', 'args': [module_name]})
                
            elif command == "clear":
                os.system('cls' if os.name == 'nt' else 'clear')
                success("Console cleared")
            
            elif command == "points":
                if len(parts) < 2:
                    error("Usage: points <see/add/remove/reset/top> [username] [amount]")
                    continue

                action = parts[1].lower()
                
                if action == "top":
                    top_users = coinmanager.get_top_users(3)
                    if not top_users:
                        info("Noch keine Punkte vergeben.")
                    else:
                        print("🏆 Top 3 Users:")
                        for i, (name, pts) in enumerate(top_users, start=1):
                            print(f"{i}. {name} – {pts} Punkte")
                
                elif action in ["see", "add", "remove", "reset"]:
                    if len(parts) < 3:
                        error(f"Usage: points {action} <username> [amount]")
                        continue
                    
                    username = parts[2]

                    if action == "see":
                        points = coinmanager.get_user_points(username)
                        info(f"{username} has {points} points.")
                    elif action in ["add", "remove"]:
                        if len(parts) < 4:
                            error(f"Usage: points {action} <username> <amount>")
                            continue
                        try:
                            amount = int(parts[3])
                        except ValueError:
                            error("Amount must be a number.")
                            continue
                        if action == "add":
                            coinmanager.give_user_points(username, amount)
                            success(f"Gave {amount} points to {username}.")
                        else:
                            coinmanager.take_user_points(username, amount)
                            success(f"Removed {amount} points from {username}.")
                    elif action == "reset":
                        coinmanager.take_user_points(username, coinmanager.get_user_points(username))
                        success(f"{username}'s points have been reset to 0.")
                
                else:
                    error("Unknown points action. Use: see, add, remove, reset, top")
                
            elif command == "send":
                if len(parts) < 2:
                    error("Usage: send <message> [channel]")
                    continue

                # Alles nach "send" als Nachricht zusammenfügen (außer letztem Teil wenn es ein Kanal ist)
                if len(parts) > 2 and parts[-1].startswith('#'):
                    # Letzter Teil ist ein Kanal
                    channel = parts[-1][1:]  # Entferne # 
                    message = " ".join(parts[1:-1])
                else:
                    # Kein spezifischer Kanal angegeben
                    channel = None
                    message = " ".join(parts[1:])
                
                # Sende Befehl an Bot
                command_queue.put({'command': 'send', 'args': [message, channel]})
                
                if channel:
                    success(f"Sent message to #{channel}: {message}")
                else:
                    success(f"Sent message to all channels: {message}")

            else:
                error(f"Unknown command: '{line}' (type 'help' for available commands)")
                
        except KeyboardInterrupt:
            print()
            warning("Received interrupt signal")
            command_queue.put({'command': 'exit'})
            should_exit = True
            return "exit"
        except EOFError:
            command_queue.put({'command': 'exit'})
            should_exit = True
            return "exit"

def signal_handler(signum, frame):
    """Handler für Systemsignale"""
    global should_exit
    warning("Received termination signal")
    should_exit = True

def main():
    global should_exit
    
    # Signal Handler registrieren
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        load_env(required_env_vars)
        
        # Shared Queues für Inter-Process Communication
        manager = multiprocessing.Manager()
        shared_log_queue = manager.Queue()
        shared_command_queue = manager.Queue()
        
        # Starte Bot-Prozess
        p = multiprocessing.Process(target=run_bot, args=(shared_log_queue, shared_command_queue))
        p.start()
        
        # Übertrage Messages von shared queue zu lokaler queue
        def queue_transfer():
            while not should_exit:
                try:
                    if not shared_log_queue.empty():
                        message = shared_log_queue.get_nowait()
                        log_queue.put(message)
                except:
                    pass
                time.sleep(0.1)
        
        # Starte Threads
        transfer_thread = threading.Thread(target=queue_transfer, daemon=True)
        transfer_thread.start()
        
        log_thread = threading.Thread(target=log_handler, daemon=True)
        log_thread.start()
        
        # Input Handler
        safe_input(shared_command_queue)
        
        # Cleanup
        info("Shutting down...")
        p.terminate()
        p.join(timeout=5)
        
        if p.is_alive():
            warning("Force killing bot process...")
            p.kill()
            p.join()
            
        success("Bot stopped successfully")
        
    except Exception as e:
        fatal_error(f"Unexpected error: {str(e)}", 1)

if __name__ == "__main__":
    main()