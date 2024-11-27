import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from .console import console
import shutil
from datetime import datetime


class SystemPromptCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)

    def get_prompt_ids(self) -> List[str]:
        """Get all available prompt IDs"""
        console.message(f"Getting prompt ids from {self.path}") 
        return [f.stem for f in self.path.iterdir() if f.is_file()]
    
    def get_prompt(self, prompt_id: str) -> Dict[str, str]:
        """Get a system prompt by its ID"""
        prompt_file = self.path / f"{prompt_id}.json"
        if not prompt_file.exists():
            raise KeyError(f"No prompt found with ID: {prompt_id}")
            
        with open(prompt_file, 'r') as f:
            return json.load(f)
        
    def save_prompt(self, prompt_id: str, prompt: str, name: str, description: Optional[str] = None):
        """Save or update a system prompt with the given ID and metadata"""
        prompt_data = {
            "name": name,
            "description": description,
            "prompt": prompt,
            "created_at": datetime.now().isoformat()
        }
        with open(self.path / f"{prompt_id}.json", 'w') as f:
            json.dump(prompt_data, f)


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
            thread_data = json.load(f)
            return thread_data["messages"]

    def add_message(self, message: Dict, thread_id: str):
        """Add a message to a specific thread"""
        console.message(f"Adding message to thread {thread_id}")
        message_file = self.messages_dir / f"{thread_id}.json"
        
        if message_file.exists():
            with open(message_file, 'r') as f:
                thread_data = json.load(f)
                messages = thread_data["messages"]
        else:
            thread_data = {
                "created_at": datetime.now().isoformat(),
                "messages": []
            }
            messages = thread_data["messages"]
            
        messages.append(message)
        thread_data["updated_at"] = datetime.now().isoformat()
        
        with open(message_file, 'w') as f:
            json.dump(thread_data, f)

    def get_threads(self) -> List[Dict]:
        """
        Get all threads from the cache
        Returns a list of thread dictionaries with messages and metadata
        """
        threads = []
        for thread_file in self.messages_dir.glob('*.json'):
            try:
                with open(thread_file, 'r') as f:
                    thread_data = json.load(f)
                    threads.append({
                        "thread_id": thread_file.stem,
                        "created_at": thread_data.get("created_at", ""),
                        "updated_at": thread_data.get("updated_at", ""),
                        "messages": thread_data.get("messages", [])
                    })
            except json.JSONDecodeError:
                console.error(f"Error reading thread file: {thread_file}")
                continue
        
        # Sort threads by updated_at date, newest first
        return sorted(threads, key=lambda x: x.get("updated_at", ""), reverse=True)


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
        return self.message_cache.get_threads()
    
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