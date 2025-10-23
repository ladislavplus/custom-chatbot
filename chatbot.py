import os
import json
import litellm
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

class Chatbot:
    def __init__(self):        
        load_dotenv(override=True)
        print("SSL_CERT_FILE =", os.getenv("SSL_CERT_FILE"))

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
            # Fallback to basic config
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
    
    def switch_model(self, friendly_name: str):
        """Switch to a different AI model"""
        if friendly_name not in self.models_config["models"]:
            return f"Error: Model '{friendly_name}' is not recognized. Use /models to see available models."
        
        model_info = self.models_config["models"][friendly_name]
        self.active_model_name = model_info["litellm_string"]
        self.active_model_friendly = friendly_name
        
        return f"✓ Switched to: {friendly_name} ({model_info['provider']})"

    def list_models(self):
        """List all available models grouped by provider"""
        models_by_provider = {}
        
        for name, info in self.models_config["models"].items():
            provider = info.get("provider", "Unknown")
            if provider not in models_by_provider:
                models_by_provider[provider] = []
            
            models_by_provider[provider].append({
                "name": name,
                "description": info.get("description", ""),
                "use_case": info.get("use_case", "")
            })
        
        output = "\n=== Available Models ===\n"
        for provider, models in sorted(models_by_provider.items()):
            output += f"\n[{provider}]\n"
            for model in models:
                output += f"  • {model['name']:<20} - {model['description']}"
                if model.get('use_case'):
                    output += f"\n    └─ Use case: {model['use_case']}"
                output += "\n"
        
        output += f"\nCurrent model: {self.active_model_friendly}\n"
        return output

    def set_system_prompt(self, prompt: str):
        """Set a new system prompt"""
        self.system_prompt = {"role": "system", "content": prompt}
        self.start_new_chat()
        return f"✓ System prompt updated. Conversation reset."

    def start_new_chat(self):
        """Start a new conversation"""
        self.conversation_history = []
        self.total_tokens_used = 0
        return "✓ New chat session started."

    def get_chat_response_stream(self, user_prompt: str):
        """Get streaming response from the AI model"""
        if not self.active_model_name:
            yield "Error: No model is currently active."
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
                    yield content
            
            # Update token usage if available
            if hasattr(chunk, 'usage') and chunk.usage:
                self.total_tokens_used += chunk.usage.total_tokens
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": user_prompt})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
        except Exception as e:
            error_msg = self._format_error(e)
            yield f"\n\n❌ Error: {error_msg}"
    
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
            return "⚠ No conversation to save."
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"chat_{self.active_model_friendly}_{timestamp}.md"
        
        # Ensure .md extension
        if not filename.endswith('.md'):
            filename += '.md'
        
        filepath = self.conversations_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Write header
                f.write(f"# Chat Conversation\n\n")
                f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Model:** {self.active_model_friendly} ({self.active_model_name})\n")
                f.write(f"**System Prompt:** {self.system_prompt['content']}\n")
                if self.total_tokens_used > 0:
                    f.write(f"**Total Tokens:** {self.total_tokens_used}\n")
                f.write(f"\n---\n\n")
                
                # Write conversation
                for msg in self.conversation_history:
                    role = msg['role'].capitalize()
                    content = msg['content']
                    f.write(f"## {role}\n\n{content}\n\n")
            
            return f"✓ Conversation saved to: {filepath}"
        
        except Exception as e:
            return f"❌ Error saving conversation: {e}"
    
    def load_conversation(self, filename: str):
        """Load conversation from a markdown file"""
        if not filename.endswith('.md'):
            filename += '.md'
        
        filepath = self.conversations_dir / filename
        
        if not filepath.exists():
            return f"❌ File not found: {filepath}"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the conversation
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
            
            # Add last message
            if current_role and current_content:
                self.conversation_history.append({
                    "role": current_role,
                    "content": '\n'.join(current_content).strip()
                })
            
            return f"✓ Loaded conversation from: {filepath} ({len(self.conversation_history)} messages)"
        
        except Exception as e:
            return f"❌ Error loading conversation: {e}"
    
    def list_saved_conversations(self):
        """List all saved conversations"""
        try:
            files = sorted(self.conversations_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            if not files:
                return "No saved conversations found."
            
            output = "\n=== Saved Conversations ===\n\n"
            for file in files:
                stat = file.stat()
                modified = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                size = stat.st_size
                output += f"  • {file.name:<50} ({size:>6} bytes, {modified})\n"
            
            return output
        
        except Exception as e:
            return f"❌ Error listing conversations: {e}"
    
    def get_stats(self):
        """Get conversation statistics"""
        msg_count = len(self.conversation_history)
        user_msgs = sum(1 for msg in self.conversation_history if msg['role'] == 'user')
        assistant_msgs = sum(1 for msg in self.conversation_history if msg['role'] == 'assistant')
        
        output = "\n=== Conversation Stats ===\n"
        output += f"Model: {self.active_model_friendly}\n"
        output += f"Total messages: {msg_count}\n"
        output += f"User messages: {user_msgs}\n"
        output += f"Assistant messages: {assistant_msgs}\n"
        if self.total_tokens_used > 0:
            output += f"Total tokens used: {self.total_tokens_used}\n"
        
        return output