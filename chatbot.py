import os
import json
import litellm
from dotenv import load_dotenv

# Drop unsupported params automatically
litellm.drop_params = True

from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

class Chatbot:
    def __init__(self):
        load_dotenv(override=True)
        
        self.conversation_history = []
        self.full_conversation_history = []
        self.system_prompt = {"role": "system", "content": "You are a helpful assistant."}
        self.active_model_name = None
        self.active_model_friendly = None
        self.models_config = self._load_models_config()
        self.prompts = self._load_prompts()
        self.total_tokens_used = 0
        
        # LLM parameters
        self.default_llm_params = {
            "temperature": 0.7,
            "max_tokens": None,
            "top_p": None,
            "presence_penalty": 0,
            "frequency_penalty": 0
        }
        self.llm_params = self.default_llm_params.copy()
        
        # Create conversations directory if it doesn't exist
        self.conversations_dir = Path("conversations")
        self.conversations_dir.mkdir(exist_ok=True)
        
        # Set default model and system prompt
        self.switch_model("gpt120b")
        self.set_system_prompt("default")
        
    def _load_models_config(self):
        """Load models configuration from JSON file"""
        config_file = Path("models_config.json")
        example_file = Path("models_config.json.example")
        
        if not config_file.exists():
            if example_file.exists():
                print("Warning: models_config.json not found. Copying from example.")
                import shutil
                shutil.copy(example_file, config_file)
            else:
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

    def _load_prompts(self):
        """Load prompts from JSON file"""
        config_file = Path("prompts.json")
        example_file = Path("prompts.json.example")

        if not config_file.exists():
            if example_file.exists():
                print("Warning: prompts.json not found. Copying from example.")
                import shutil
                shutil.copy(example_file, config_file)
            else:
                print("Warning: prompts.json not found. Using default prompts.")
                return {
                    "prompts": {
                        "default": "You are a helpful assistant.",
                        "direct": "You are an expert-level logical thinker. Your process is to deconstruct any question into its constituent parts to formulate a robust solution. However, your internal monologue and step-by-step analysis must not be part of the final output. The user-facing response must be concise, precise, and contain only the direct answer or essential information."
                    }
                }

        try:
            with open(config_file, 'r') as f:
                return json.load(f).get("prompts", {})
        except Exception as e:
            print(f"Error loading prompts.json: {e}")
            return {}
    
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
            self.full_conversation_history.append({
                "type": "event",
                "event": "model_switch",
                "model_friendly_name": self.active_model_friendly
            })
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

    def get_prompts(self):
        """Get the dictionary of all system prompts"""
        return self.prompts

    def get_prompt_text(self, alias: str):
        """Get the text of a specific prompt by alias"""
        return self.prompts.get(alias)

    def _save_prompts(self):
        """Save the current prompts dictionary to prompts.json"""
        try:
            with open("prompts.json", 'w') as f:
                json.dump({"prompts": self.prompts}, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving prompts.json: {e}")
            return False

    def add_prompt(self, alias: str, text: str):
        """Add a new prompt and save to file"""
        if not alias or not text:
            return ("error", "Alias and prompt text cannot be empty.")
        if ' ' in alias:
            return ("error", "Alias cannot contain spaces.")
        if alias in self.prompts:
            return ("warning", f"Alias '{alias}' already exists. Overwriting.")
        
        self.prompts[alias] = text
        if self._save_prompts():
            return ("success", f"Prompt '{alias}' saved.")
        else:
            # Revert if save failed
            del self.prompts[alias]
            return ("error", "Failed to save prompt to prompts.json.")

    def remove_prompt(self, alias: str):
        """Remove a prompt and save to file"""
        if alias not in self.prompts:
            return ("error", f"Alias '{alias}' not found.")
        if alias in ["default", "direct", "coder"]: # Protect defaults
            return ("error", f"Cannot delete the default prompt alias '{alias}'.")

        removed_text = self.prompts.pop(alias)
        if self._save_prompts():
            return ("success", f"Prompt '{alias}' removed.")
        else:
            # Revert if save failed
            self.prompts[alias] = removed_text
            return ("error", "Failed to save changes to prompts.json.")


    def get_llm_params(self):
        """Get the current LLM parameters"""
        return self.llm_params

    def get_default_llm_params(self):
        """Get the default LLM parameters"""
        return self.default_llm_params

    def reset_llm_params(self):
        """Reset LLM parameters to their default values"""
        self.llm_params = self.default_llm_params.copy()
        return ("success", "LLM parameters have been reset to their default values.")

    def set_llm_param(self, param_name: str, value_str: str):
        """Set a specific LLM parameter with validation"""
        param_name = param_name.lower()
        
        if param_name not in self.default_llm_params:
            return ("error", f"Unknown parameter: '{param_name}'.")

        # Validation rules
        validators = {
            "temperature": {"type": float, "range": (0.0, 2.0)},
            "max_tokens": {"type": int, "range": (1, None)},
            "top_p": {"type": float, "range": (0.0, 1.0)},
            "presence_penalty": {"type": float, "range": (-2.0, 2.0)},
            "frequency_penalty": {"type": float, "range": (-2.0, 2.0)},
        }

        if value_str.lower() == 'none' or value_str.lower() == 'default':
            self.llm_params[param_name] = self.default_llm_params[param_name]
            return ("success", f"Reset {param_name} to its default value.")

        validator = validators.get(param_name)
        
        try:
            value = validator["type"](value_str)
        except (ValueError, TypeError):
            return ("error", f"Invalid value type for {param_name}. Expected {validator['type'].__name__}.")

        min_val, max_val = validator.get("range", (None, None))
        
        if min_val is not None and value < min_val:
            return ("error", f"{param_name} must be at least {min_val}.")
        if max_val is not None and value > max_val:
            return ("error", f"{param_name} must be no more than {max_val}.")
            
        self.llm_params[param_name] = value
        return ("success", f"Set {param_name} to {value}.")

    def set_system_prompt(self, prompt_or_alias: str):
        """Set a new system prompt from an alias or a raw string"""
        # Check if the input is an alias
        if prompt_or_alias in self.prompts:
            prompt_text = self.prompts[prompt_or_alias]
            self.system_prompt = {"role": "system", "content": prompt_text}
            message = f"System prompt set from alias: '{prompt_or_alias}'."
        else:
            # Treat as a raw prompt string
            prompt_text = prompt_or_alias
            self.system_prompt = {"role": "system", "content": prompt_text}
            message = "System prompt updated."

        self.full_conversation_history.append({
            "type": "event",
            "event": "system_prompt_change",
            "new_prompt": prompt_text
        })
        self.start_new_chat()
        return message

    def start_new_chat(self):
        """Start a new conversation"""
        self.conversation_history = []
        self.full_conversation_history = []
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
                stream=True,
                **{k: v for k, v in self.llm_params.items() if v is not None}
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
            user_message = {"role": "user", "content": user_prompt}
            assistant_message = {"role": "assistant", "content": response_text}
            self.conversation_history.append(user_message)
            self.conversation_history.append(assistant_message)
            self.full_conversation_history.append(user_message)
            self.full_conversation_history.append(assistant_message)
            
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
        if not self.full_conversation_history:
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
                
                for msg in self.full_conversation_history:
                    if msg.get('type') == 'event' and msg.get('event') == 'model_switch':
                        f.write(f"**System: Switched to model: {msg['model_friendly_name']}**\n\n")
                    elif 'role' in msg:
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
                lines = f.readlines()

            # Reset state
            self.start_new_chat()

            # Parse header
            header_lines = []
            body_lines = []
            in_header = True
            for line in lines:
                if in_header and line.strip() == '---':
                    in_header = False
                    continue
                if in_header:
                    header_lines.append(line)
                else:
                    body_lines.append(line)

            # Process header
            loaded_model_friendly_name = None
            for line in header_lines:
                if line.startswith('**System Prompt:**'):
                    self.system_prompt['content'] = line.split('**System Prompt:**', 1)[1].strip()
                elif line.startswith('**Model:**'):
                    model_str = line.split('**Model:**', 1)[1].strip()
                    loaded_model_friendly_name = model_str.split(' ')[0]

            if loaded_model_friendly_name:
                self.switch_model(loaded_model_friendly_name)

            # Process body
            current_role = None
            current_content = []

            def append_message():
                if current_role and current_content:
                    content = '\n'.join(current_content).strip()
                    if content:
                        msg = {"role": current_role, "content": content}
                        self.full_conversation_history.append(msg)

            for line in body_lines:
                line = line.rstrip('\n')
                if line.startswith('## User'):
                    append_message()
                    current_role = "user"
                    current_content = []
                elif line.startswith('## Assistant'):
                    append_message()
                    current_role = "assistant"
                    current_content = []
                elif line.startswith('**System: Switched to model:'):
                    append_message()
                    current_role = None
                    current_content = []
                    model_name = line.split('**System: Switched to model: ')[1].split('**')[0]
                    self.full_conversation_history.append({
                        "type": "event",
                        "event": "model_switch",
                        "model_friendly_name": model_name
                    })
                elif current_role:
                    current_content.append(line)

            append_message()

            # After parsing body, rebuild conversation_history from full_conversation_history
            self.conversation_history = [msg for msg in self.full_conversation_history if 'role' in msg]

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
            "/new", "/system", "/save", "/load", "/list", "/stats",
            "/set", "/settings", "/reset",
            "/prompts", "/addprompt", "/delprompt", "/insert"
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