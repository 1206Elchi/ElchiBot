import os
import json
import importlib
import inspect
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from colorama import Fore, Style

@dataclass
class CommandConfig:
    """Konfiguration für einen einzelnen Command"""
    enabled: bool = True
    cooldown: int = 5  # Sekunden
    permission_level: str = "everyone"  # everyone, subscriber, vip, mod, owner
    max_uses_per_user: int = 0  # 0 = unlimited
    channels: List[str] = None  # None = alle Kanäle
    aliases: List[str] = None  # Alternative Namen für den Command
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = []
        if self.aliases is None:
            self.aliases = []

@dataclass
class ModuleConfig:
    """Basis-Konfiguration für Module"""
    enabled: bool = True
    auto_reload: bool = False
    debug_mode: bool = False
    commands: Dict[str, CommandConfig] = None
    custom_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.commands is None:
            self.commands = {}
        if self.custom_settings is None:
            self.custom_settings = {}

# Spezielle Modul-Konfigurationen
@dataclass
class ChatbotModuleConfig(ModuleConfig):
    """Konfiguration für Chatbot-Module"""
    response_chance: float = 0.1  # 10% Chance auf Response
    learn_from_chat: bool = False
    banned_words: List[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.banned_words is None:
            self.banned_words = []

@dataclass
class GameModuleConfig(ModuleConfig):
    """Konfiguration für Game-Module"""
    max_players: int = 10
    game_timeout: int = 300  # 5 Minuten
    enable_leaderboard: bool = True
    point_rewards: Dict[str, int] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.point_rewards is None:
            self.point_rewards = {"win": 100, "participation": 10}

@dataclass
class UtilityModuleConfig(ModuleConfig):
    """Konfiguration für Utility-Module"""
    rate_limit: int = 60  # Requests pro Minute
    cache_duration: int = 300  # Cache für 5 Minuten
    external_api: bool = False
    api_key: str = ""

@dataclass
class ModerationModuleConfig(ModuleConfig):
    """Konfiguration für Moderation-Module"""
    auto_timeout: bool = True
    timeout_duration: int = 300  # 5 Minuten
    warning_threshold: int = 3
    exempt_users: List[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        if self.exempt_users is None:
            self.exempt_users = []

@dataclass
class PointsModuleConfig(ModuleConfig):
    """Konfiguration für Punkte-Module"""
    base_reward: int = 10
    reward_interval: int = 600  # 10 Minuten
    multiplier_events: Dict[str, float] = None
    daily_bonus: int = 100
    
    def __post_init__(self):
        super().__post_init__()
        if self.multiplier_events is None:
            self.multiplier_events = {"raid": 2.0, "host": 1.5}

class ConfigManager:
    """Verwaltet alle Modul-Konfigurationen"""
    
    def __init__(self, log_queue=None):
        self.log_queue = log_queue
        self.config_path = Path("configs")
        self.modules_path = Path("modules")
        self.config_path.mkdir(exist_ok=True)
        
        # Mapping von Modul-Typen zu Config-Klassen
        self.config_types = {
            "chatbot": ChatbotModuleConfig,
            "game": GameModuleConfig,
            "utility": UtilityModuleConfig,
            "moderation": ModerationModuleConfig,
            "points": PointsModuleConfig,
            "default": ModuleConfig
        }
        
        self.loaded_configs = {}
        self.last_modified = {}
        
    def log(self, message):
        """Hilfsfunktion für Logging"""
        if self.log_queue:
            self.log_queue.put(f"{Fore.CYAN}[CONFIG]{Style.RESET_ALL} {message}")
        else:
            print(f"[CONFIG] {message}")
    
    def detect_module_type(self, module_name: str) -> str:
        """Erkennt den Typ eines Moduls basierend auf Code-Analyse"""
        try:
            module_path = self.modules_path / f"{module_name}.py"
            if not module_path.exists():
                return "default"
            
            # Lade das Modul
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Prüfe auf MODULE_TYPE Attribut
            if hasattr(module, 'MODULE_TYPE'):
                return module.MODULE_TYPE.lower()
            
            # Analysiere den Code für Hinweise
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Heuristische Erkennung basierend auf Schlüsselwörtern
            if any(word in content for word in ['game', 'player', 'score', 'leaderboard']):
                return "game"
            elif any(word in content for word in ['timeout', 'ban', 'moderate', 'filter']):
                return "moderation"
            elif any(word in content for word in ['points', 'coins', 'currency', 'reward']):
                return "points"
            elif any(word in content for word in ['api', 'request', 'weather', 'quote']):
                return "utility"
            elif any(word in content for word in ['chat', 'response', 'ai', 'reply']):
                return "chatbot"
            
            return "default"
            
        except Exception as e:
            self.log(f"Error detecting module type for {module_name}: {str(e)}")
            return "default"
    
    def extract_commands_from_module(self, module_name: str) -> List[str]:
        """Extrahiert Command-Namen aus einem Modul"""
        commands = []
        try:
            module_path = self.modules_path / f"{module_name}.py"
            if not module_path.exists():
                return commands
            
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Suche nach @bot.command() Dekorationen
            import re
            command_pattern = r'@bot\.command\(\s*name\s*=\s*[\'"]([^\'"]+)[\'"]'
            matches = re.findall(command_pattern, content)
            commands.extend(matches)
            
            # Suche nach @bot.command() ohne expliziten Namen
            function_pattern = r'@bot\.command\(\s*\)\s*async\s+def\s+(\w+)'
            matches = re.findall(function_pattern, content)
            commands.extend(matches)
            
            # Suche nach bot.add_command() Aufrufen
            add_command_pattern = r'bot\.add_command\(\s*commands\.Command\(\s*name\s*=\s*[\'"]([^\'"]+)[\'"]'
            matches = re.findall(add_command_pattern, content)
            commands.extend(matches)
            
        except Exception as e:
            self.log(f"Error extracting commands from {module_name}: {str(e)}")
        
        return list(set(commands))  # Entferne Duplikate
    
    def create_default_config(self, module_name: str) -> ModuleConfig:
        """Erstellt eine Standard-Konfiguration für ein Modul"""
        module_type = self.detect_module_type(module_name)
        config_class = self.config_types.get(module_type, ModuleConfig)
        
        # Erstelle Basis-Config
        config = config_class()
        
        # Extrahiere Commands und erstelle Config dafür
        commands = self.extract_commands_from_module(module_name)
        for command in commands:
            config.commands[command] = CommandConfig(
                enabled=True,
                cooldown=5,
                permission_level="everyone"
            )
        
        # Modul-spezifische Anpassungen
        if module_type == "points":
            config.custom_settings.update({
                "auto_reward_active_users": True,
                "reward_multiplier": 1.0,
                "daily_streak_bonus": True
            })
        elif module_type == "game":
            config.custom_settings.update({
                "allow_spectators": True,
                "save_game_stats": True,
                "announce_winners": True
            })
        elif module_type == "moderation":
            config.custom_settings.update({
                "log_actions": True,
                "notify_mods": True,
                "auto_purge_spam": False
            })
        
        return config
    
    def config_to_dict(self, config: ModuleConfig) -> Dict[str, Any]:
        """Konvertiert Config-Objekt zu Dictionary"""
        config_dict = asdict(config)
        
        # Konvertiere CommandConfig-Objekte
        if 'commands' in config_dict:
            commands_dict = {}
            for cmd_name, cmd_config in config_dict['commands'].items():
                if isinstance(cmd_config, CommandConfig):
                    commands_dict[cmd_name] = asdict(cmd_config)
                else:
                    commands_dict[cmd_name] = cmd_config
            config_dict['commands'] = commands_dict
        
        # Füge Metadaten hinzu
        config_dict['_metadata'] = {
            'created': datetime.now().isoformat(),
            'version': '1.0',
            'config_type': config.__class__.__name__
        }
        
        return config_dict
    
    def dict_to_config(self, config_dict: Dict[str, Any], module_name: str) -> ModuleConfig:
        """Konvertiert Dictionary zu Config-Objekt"""
        # Bestimme Config-Typ
        module_type = self.detect_module_type(module_name)
        config_class = self.config_types.get(module_type, ModuleConfig)
        
        # Entferne Metadaten
        config_dict = config_dict.copy()
        config_dict.pop('_metadata', None)
        
        # Konvertiere Commands
        if 'commands' in config_dict:
            commands = {}
            for cmd_name, cmd_data in config_dict['commands'].items():
                if isinstance(cmd_data, dict):
                    commands[cmd_name] = CommandConfig(**cmd_data)
                else:
                    commands[cmd_name] = cmd_data
            config_dict['commands'] = commands
        
        try:
            return config_class(**config_dict)
        except Exception as e:
            self.log(f"Error creating config object for {module_name}: {str(e)}")
            return self.create_default_config(module_name)
    
    def save_config(self, module_name: str, config: ModuleConfig):
        """Speichert Konfiguration für ein Modul"""
        config_file = self.config_path / f"{module_name}.json"
        
        try:
            config_dict = self.config_to_dict(config)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.loaded_configs[module_name] = config
            self.last_modified[module_name] = config_file.stat().st_mtime
            
            self.log(f"Saved config for module: {module_name}")
            
        except Exception as e:
            self.log(f"Error saving config for {module_name}: {str(e)}")
    
    def load_config(self, module_name: str) -> ModuleConfig:
        """Lädt Konfiguration für ein Modul"""
        config_file = self.config_path / f"{module_name}.json"
        
        # Prüfe ob bereits geladen und nicht verändert
        if module_name in self.loaded_configs:
            if config_file.exists():
                current_mtime = config_file.stat().st_mtime
                if current_mtime == self.last_modified.get(module_name, 0):
                    return self.loaded_configs[module_name]
        
        # Lade oder erstelle Config
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                
                config = self.dict_to_config(config_dict, module_name)
                self.loaded_configs[module_name] = config
                self.last_modified[module_name] = config_file.stat().st_mtime
                
                self.log(f"Loaded config for module: {module_name}")
                return config
                
            except Exception as e:
                self.log(f"Error loading config for {module_name}: {str(e)}")
                self.log("Creating default config...")
        
        # Erstelle Standard-Config
        config = self.create_default_config(module_name)
        self.save_config(module_name, config)
        return config
    
    def get_command_config(self, module_name: str, command_name: str) -> Optional[CommandConfig]:
        """Holt Command-Konfiguration"""
        config = self.load_config(module_name)
        return config.commands.get(command_name)
    
    def update_command_config(self, module_name: str, command_name: str, **kwargs):
        """Aktualisiert Command-Konfiguration"""
        config = self.load_config(module_name)
        
        if command_name not in config.commands:
            config.commands[command_name] = CommandConfig()
        
        # Aktualisiere Attribute
        for key, value in kwargs.items():
            if hasattr(config.commands[command_name], key):
                setattr(config.commands[command_name], key, value)
        
        self.save_config(module_name, config)
    
    def scan_and_update_configs(self):
        """Scannt alle Module und aktualisiert Konfigurationen"""
        if not self.modules_path.exists():
            self.log("Modules directory not found")
            return
        
        updated_count = 0
        
        for module_file in self.modules_path.glob("*.py"):
            if module_file.name == "__init__.py":
                continue
            
            module_name = module_file.stem
            config = self.load_config(module_name)
            
            # Prüfe auf neue Commands
            current_commands = set(config.commands.keys())
            detected_commands = set(self.extract_commands_from_module(module_name))
            
            new_commands = detected_commands - current_commands
            removed_commands = current_commands - detected_commands
            
            if new_commands or removed_commands:
                # Füge neue Commands hinzu
                for command in new_commands:
                    config.commands[command] = CommandConfig()
                    self.log(f"Added new command '{command}' to {module_name}")
                
                # Entferne alte Commands (optional, wird hier nur geloggt)
                for command in removed_commands:
                    self.log(f"Command '{command}' no longer found in {module_name}")
                
                self.save_config(module_name, config)
                updated_count += 1
        
        if updated_count > 0:
            self.log(f"Updated {updated_count} module configs")
        else:
            self.log("All module configs are up to date")
    
    def list_all_configs(self):
        """Listet alle verfügbaren Konfigurationen auf"""
        configs = []
        for config_file in self.config_path.glob("*.json"):
            module_name = config_file.stem
            config = self.load_config(module_name)
            configs.append({
                'module': module_name,
                'enabled': config.enabled,
                'commands': len(config.commands),
                'type': config.__class__.__name__
            })
        return configs

# Globale Instanz
config_manager = ConfigManager()

# Convenience-Funktionen
def get_config(module_name: str) -> ModuleConfig:
    """Holt Konfiguration für ein Modul"""
    return config_manager.load_config(module_name)

def get_command_config(module_name: str, command_name: str) -> Optional[CommandConfig]:
    """Holt Command-Konfiguration"""
    return config_manager.get_command_config(module_name, command_name)

def is_command_enabled(module_name: str, command_name: str) -> bool:
    """Prüft ob Command aktiviert ist"""
    cmd_config = get_command_config(module_name, command_name)
    if not cmd_config:
        return True  # Default: aktiviert
    
    module_config = get_config(module_name)
    return module_config.enabled and cmd_config.enabled

def get_command_cooldown(module_name: str, command_name: str) -> int:
    """Holt Cooldown für Command"""
    cmd_config = get_command_config(module_name, command_name)
    return cmd_config.cooldown if cmd_config else 5

def check_permission(module_name: str, command_name: str, user_level: str) -> bool:
    """Prüft Berechtigung für Command"""
    cmd_config = get_command_config(module_name, command_name)
    if not cmd_config:
        return True
    
    permission_hierarchy = {
        "everyone": 0,
        "subscriber": 1,
        "vip": 2,
        "mod": 3,
        "owner": 4
    }
    
    required_level = permission_hierarchy.get(cmd_config.permission_level, 0)
    user_level_num = permission_hierarchy.get(user_level, 0)
    
    return user_level_num >= required_level

# Initialisierung
def initialize_config_system(log_queue=None):
    """Initialisiert das Konfigurationssystem"""
    global config_manager
    config_manager = ConfigManager(log_queue)
    config_manager.scan_and_update_configs()
    
    return config_manager