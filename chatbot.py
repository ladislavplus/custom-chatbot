# chatbot.py

import os
import litellm
from dotenv import load_dotenv

# With litellm, we just need to know the model string.
# The format is often 'provider/model_name'.
# See litellm docs for a full list: https://docs.litellm.ai/docs/providers
AVAILABLE_MODELS = {
    # Friendly Name: litellm Model String
    "gpt-4o": "openai/gpt-4o",
    "gpt-3.5": "openai/gpt-3.5-turbo",
    "groq-llama3-8b": "groq/llama3-8b-8192",
    "groq-mixtral": "groq/mixtral-8x7b-32768",
    "ollama-llama3": "ollama/llama3", # Assumes you have 'llama3' pulled in Ollama
    "ollama-mistral": "ollama/mistral", # Assumes you have 'mistral' pulled in Ollama
}

class Chatbot:
    def __init__(self):
        load_dotenv()
        self.conversation_history = []
        self.system_prompt = {"role": "system", "content": "You are a helpful assistant."}
        
        self.active_model_name = None
        
        # Set a sensible default model based on available API keys
        if os.getenv("OPENAI_API_KEY"):
            self.switch_model("gpt-4o")
        elif os.getenv("GROQ_API_KEY"):
            self.switch_model("groq-llama3-8b")
        else:
            # Fallback to Ollama if no keys are present
            self.switch_model("ollama-llama3")

    def switch_model(self, friendly_name: str):
        if friendly_name not in AVAILABLE_MODELS:
            return f"Error: Model '{friendly_name}' is not recognized."
        
        # We store the full litellm model string
        self.active_model_name = AVAILABLE_MODELS[friendly_name]
        return f"Switched to model: {friendly_name} ({self.active_model_name})"

    def list_models(self):
        return "Available models (use the friendly name to switch):\n" + "\n".join([f" - {name}" for name in AVAILABLE_MODELS.keys()])

    def set_system_prompt(self, prompt: str):
        self.system_prompt = {"role": "system", "content": prompt}
        self.start_new_chat() # Reset chat history when system prompt changes
        return f"System prompt updated. Conversation has been reset."

    def start_new_chat(self):
        self.conversation_history = []
        return "New chat session started."

    def get_chat_response(self, user_prompt: str):
        if not self.active_model_name:
            return "Error: No model is currently active. Please configure an API key or run Ollama."
            
        messages = [self.system_prompt] + self.conversation_history + [{"role": "user", "content": user_prompt}]
        
        try:
            # The single, unified call to any LLM provider!
            response = litellm.completion(
                model=self.active_model_name,
                messages=messages
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            # Add user prompt and AI response to history
            self.conversation_history.append({"role": "user", "content": user_prompt})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
            return response_text

        except Exception as e:
            # litellm raises detailed exceptions, we can catch them all here
            error_message = f"An error occurred with the API call: {e}"
            print(error_message) # Also print to console for debugging
            return error_message
