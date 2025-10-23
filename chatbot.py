import os
import json
import litellm
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

class Chatbot:
    def __init__(self):        
        load_dotenv(override=True)
        
        self.conversation_history = []
        self.system_prompt = {"role": "system", "content": "You are a helpful assistant."}
        self.active_model_name = None
        self.active_model_friendly = None
        self.models_config = self._load_models_config()
        self.total_tokens_used = 0
        
        # Create conversations directory if it doesn't exist
        self.conversations_dir = Path("conversations")
        self.conversations_dir.mkdir(exist_ok=True)
        
        # Set default model
        self.switch_model("gpt120b")
        
    def _load_models_config(self):
        """Load models configuration from JSON file"""
        config_file = Path("models_config.json")
        
        if not config_file.exists():
            print("Warning: models_config.json not found. Using default models.")
            return {
                "models": {
                    "gpt120b": {
                        "litellm_string": "groq/openai/gpt-oss-120b",
                        "provider": "Groq",
                        "description": "Default model"
                    }
                }
            }
        
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading models_config.json: {e}")
            return {"models": {}}
    
    def _fuzzy_match_model(self, query: str):
        """Find best matching model using fuzzy matching"""
        query = query.lower()
        matches = []
        
        for name in self.models_config["models"].keys():
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, query.lower(), name.lower()).ratio()
            # Also check if query is a substring
            if query in name.lower():
                ratio += 0.3  # Boost substring matches
            matches.append((name, ratio))
        
        # Sort by similarity
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Get top matches (similarity > 0.4)
        good_matches = [m for m in matches if m[1] > 0.4]
        
        return good_matches[:5] if good_matches else []
    
    def switch_model(self, identifier: str):
        """Switch to a different AI model by name, number, or fuzzy match"""
        # Try direct match first
        if identifier in self.models_config["models"]:
            model_info = self.models_config["models"][identifier]
            self.active_model_name = model_info["litellm_string"]
            self.active_model_friendly = identifier
            return ("success", f"Switched to: {identifier} ({model_info['provider']})")
        
        # Try numbered selection
        if identifier.isdigit():
            model_list = list(self.models_config["models"].keys())
            idx = int(identifier) - 1
            if 0 <= idx < len(model_list):
                model_name = model_list[idx]
                return self.switch_model(model_name)
            else:
                return ("error", f"Invalid model number. Use 1-{len(model_list)}")
        
        # Try fuzzy matching
        matches = self._fuzzy_match_model(identifier)
        
        if not matches:
            return ("error", f"No models found matching '{identifier}'")
        
        if len(matches) == 1:
            # Single match, switch to it
            return self.switch_model(matches[0][0])
        
        # Multiple matches, return them for user to choose
        return ("multiple", matches)

    def get_models_list(self):
        """Get structured list of models grouped by provider"""
        models_by_provider = {}
        model_index = 1
        indexed_models = []
        
        for name, info in self.models_config["models"].items():
            provider = info.get("provider", "Unknown")
            if provider not in models_by_provider:
                models_by_provider[provider] = []
            
            model_entry = {
                "index": model_index,
                "name": name,
                "description": info.get("description", ""),
                "use_case": info.get("use_case", ""),
                "current": name == self.active_model_friendly
            }
            
            models_by_provider[provider].append(model_entry)
            indexed_models.append((model_index, name))
            model_index += 1
        
        return models_by_provider, indexed_models

    def set_system_prompt(self, prompt: str):
        """Set a new system prompt"""
        self.system_prompt = {"role": "system", "content": prompt}
        self.start_new_chat()
        return "System prompt updated. Conversation reset."

    def start_new_chat(self):
        """Start a new conversation"""
        self.conversation_history = []
        self.total_tokens_used = 0
        return "New chat session started."

    def get_chat_response_stream(self, user_prompt: str):
        """Get streaming response from the AI model"""
        if not self.active_model_name:
            yield ("error", "No model is currently active.")
            return
            
        messages = [self.system_prompt] + self.conversation_history + [{"role": "user", "content": user_prompt}]
        
        try:
            response_text = ""
            
            # Stream the response
            response = litellm.completion(
                model=self.active_model_name,
                messages=messages,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_text += content
                    yield ("content", content)
            
            # Update token usage if available
            if hasattr(chunk, 'usage') and chunk.usage:
                self.total_tokens_used += chunk.usage.total_tokens
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": user_prompt})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
        except Exception as e:
            error_msg = self._format_error(e)
            yield ("error", error_msg)
    
    def _format_error(self, error):
        """Format error messages to be more user-friendly"""
        error_str = str(error).lower()
        
        if "api key" in error_str or "authentication" in error_str:
            return "API key is missing or invalid. Check your .env file."
        elif "rate limit" in error_str:
            return "Rate limit exceeded. Please wait a moment and try again."
        elif "timeout" in error_str or "connection" in error_str:
            return "Connection timeout. Check your internet connection."
        elif "not found" in error_str or "404" in error_str:
            return "Model not found. The model may have been deprecated."
        else:
            return str(error)
    
    def save_conversation(self, filename: str = None):
        """Save conversation to a markdown file"""
        if not self.conversation_history:
            return ("warning", "No conversation to save.")
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_{self.active_model_friendly}_{timestamp}.md"
        
        if not filename.endswith('.md'):
            filename += '.md'
        
        filepath = self.conversations_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Chat Conversation\n\n")
                f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Model:** {self.active_model_friendly} ({self.active_model_name})\n")
                f.write(f"**System Prompt:** {self.system_prompt['content']}\n")
                if self.total_tokens_used > 0:
                    f.write(f"**Total Tokens:** {self.total_tokens_used}\n")
                f.write(f"\n---\n\n")
                
                for msg in self.conversation_history:
                    role = msg['role'].capitalize()
                    content = msg['content']
                    f.write(f"## {role}\n\n{content}\n\n")
            
            return ("success", f"Conversation saved to: {filepath}")
        
        except Exception as e:
            return ("error", f"Error saving conversation: {e}")
    
    def load_conversation(self, filename: str):
        """Load conversation from a markdown file"""
        if not filename.endswith('.md'):
            filename += '.md'
        
        filepath = self.conversations_dir / filename
        
        if not filepath.exists():
            return ("error", f"File not found: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.conversation_history = []
            lines = content.split('\n')
            
            current_role = None
            current_content = []
            
            for line in lines:
                if line.startswith('## User'):
                    if current_role and current_content:
                        self.conversation_history.append({
                            "role": current_role,
                            "content": '\n'.join(current_content).strip()
                        })
                    current_role = "user"
                    current_content = []
                elif line.startswith('## Assistant'):
                    if current_role and current_content:
                        self.conversation_history.append({
                            "role": current_role,
                            "content": '\n'.join(current_content).strip()
                        })
                    current_role = "assistant"
                    current_content = []
                elif current_role and not line.startswith('#') and not line.startswith('**') and not line.startswith('---'):
                    if line.strip():
                        current_content.append(line)
            
            if current_role and current_content:
                self.conversation_history.append({
                    "role": current_role,
                    "content": '\n'.join(current_content).strip()
                })
            
            return ("success", f"Loaded conversation from: {filepath} ({len(self.conversation_history)} messages)")
        
        except Exception as e:
            return ("error", f"Error loading conversation: {e}")
    
    def list_saved_conversations(self):
        """List all saved conversations"""
        try:
            files = sorted(self.conversations_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if not files:
                return []
            
            conversations = []
            for file in files:
                stat = file.stat()
                conversations.append({
                    "name": file.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime)
                })
            
            return conversations
        
        except Exception as e:
            return None
    
    def get_stats(self):
        """Get conversation statistics"""
        msg_count = len(self.conversation_history)
        user_msgs = sum(1 for msg in self.conversation_history if msg['role'] == 'user')
        assistant_msgs = sum(1 for msg in self.conversation_history if msg['role'] == 'assistant')
        
        return {
            "model": self.active_model_friendly,
            "total_messages": msg_count,
            "user_messages": user_msgs,
            "assistant_messages": assistant_msgs,
            "total_tokens": self.total_tokens_used
        }
    
    def get_command_completions(self):
        """Get list of available commands for auto-completion"""
        return [
            "/help", "/quit", "/exit", "/models", "/switch", 
            "/new", "/system", "/save", "/load", "/list", "/stats"
        ]
    
    def get_model_names(self):
        """Get list of model names for auto-completion"""
        return list(self.models_config["models"].keys())
    
    def get_saved_filenames(self):
        """Get list of saved conversation filenames for auto-completion"""
        try:
            files = list(self.conversations_dir.glob("*.md"))
            return [f.stem for f in files]  # Return without .md extension
        except:
            return []