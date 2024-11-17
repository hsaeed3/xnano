import json
from pathlib import Path
from typing import Dict, List
from .console import console
import shutil


class SystemPromptCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

    def get_thread_ids(self) -> List[str]:
        console.message(f"Getting thread ids from {self.path}") 
        return [f.stem for f in self.path.iterdir() if f.is_file()]
    
    def get_system_prompt(self, thread_id: str) -> str:
        with open(self.path / f"{thread_id}.json", 'r') as f:
            return json.load(f)
        
    def add_system_prompt(self, thread_id: str, system_prompt: str):
        with open(self.path / f"{thread_id}.json", 'w') as f:
            json.dump(system_prompt, f)


class MessageCache:
    def __init__(self, messages_dir: Path):
        self.messages_dir = messages_dir
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    def get_messages(self, thread_id: str) -> List[Dict]:
        """Get messages for a specific thread"""
        console.message(f"Getting messages for thread {thread_id}")
        message_file = self.messages_dir / f"{thread_id}.json"
            
        if not message_file.exists():
            return []
            
        with open(message_file, 'r') as f:
            return json.load(f)

    def add_message(self, message: Dict, thread_id: str):
        """Add a message to a specific thread"""
        console.message(f"Adding message to thread {thread_id}")
        message_file = self.messages_dir / f"{thread_id}.json"
        
        messages = self.get_messages(thread_id)
        messages.append(message)
        
        with open(message_file, 'w') as f:
            json.dump(messages, f)

    def get_thread_ids(self) -> List[str]:
        """Get all thread IDs"""
        return [f.stem for f in self.messages_dir.iterdir() if f.is_file() and f.suffix == '.json']


class Cache:
    def __init__(self):
        console.message("Initializing cache")
        self.cache_dir = Path.home() / '.cache' / 'xnano'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create cache subdirectories
        self.messages_dir = self.cache_dir / 'messages'
        self.system_prompts_dir = self.cache_dir / 'system_prompts'
        
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        self.system_prompts_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize caches
        self.system_prompt_cache = SystemPromptCache(self.system_prompts_dir)
        self.message_cache = MessageCache(self.messages_dir)

    def get_thread_ids(self) -> List[str]:
        """Get all thread IDs"""
        console.message("Getting thread ids")
        return self.message_cache.get_thread_ids()
    
    def clear_message_cache(self, thread_id: str):
        """Clear message cache for a specific thread"""
        console.message(f"Clearing message cache for {thread_id}")
        message_file = self.messages_dir / f"{thread_id}.json"
        message_file.unlink(missing_ok=True)

    def reset(self):
        """Reset the entire cache"""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.__init__()


cache = Cache()