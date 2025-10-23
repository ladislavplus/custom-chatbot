import sys
from chatbot import Chatbot

def print_help():
    """Display help information"""
    help_text = """
╔════════════════════════════════════════════════════════════════╗
║                    CUSTOM CHATBOT - COMMANDS                   ║
╚════════════════════════════════════════════════════════════════╝

BASIC COMMANDS:
  /help                    Show this help message
  /quit or /exit           Exit the application
  
MODEL MANAGEMENT:
  /models                  List all available AI models
  /switch <model>          Switch to a different model
  /stats                   Show conversation statistics
  
CONVERSATION MANAGEMENT:
  /new                     Start a new conversation
  /system <prompt>         Set a new system prompt
  
SAVE/LOAD:
  /save [filename]         Save conversation to markdown
  /load <filename>         Load a previous conversation
  /list                    List all saved conversations
  
EXAMPLES:
  /switch gemini-flash     Switch to Gemini Flash model
  /save my_chat            Save current chat as my_chat.md
  /load my_chat            Load my_chat.md conversation
  /system You are a coding expert who explains concepts clearly.

════════════════════════════════════════════════════════════════
"""
    print(help_text)

def print_welcome(bot):
    """Display welcome message"""
    print("\n" + "="*70)
    print("  🤖  CUSTOM CHATBOT - Enhanced Edition")
    print("="*70)
    print(f"Current model: {bot.active_model_friendly}")
    print("Type /help for commands or start chatting!")
    print("="*70 + "\n")

def main_loop():
    """Main application loop"""
    bot = Chatbot()
    print_welcome(bot)
    
    while True:
        try:
            # Show prompt with current model
            user_input = input(f"\n[{bot.active_model_friendly}] You: ")
            
            if not user_input.strip():
                continue

            # Command Handling
            if user_input.startswith('/'):
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if command in ('/quit', '/exit'):
                    # Auto-save on exit
                    if bot.conversation_history:
                        print("\n💾 Auto-saving conversation before exit...")
                        result = bot.save_conversation()
                        print(result)
                    print("\n👋 Goodbye!\n")
                    break
                    
                elif command == '/help':
                    print_help()
                    
                elif command == '/models':
                    print(bot.list_models())
                    
                elif command == '/new':
                    result = bot.start_new_chat()
                    print(f"\n{result}")
                    
                elif command == '/switch':
                    if not arg:
                        print("\n⚠ Usage: /switch <model_name>")
                        print("Use /models to see available models")
                    else:
                        result = bot.switch_model(arg)
                        print(f"\n{result}")
                        
                elif command == '/system':
                    if not arg:
                        print("\n⚠ Usage: /system <new_prompt>")
                        print("Example: /system You are a helpful coding assistant")
                    else:
                        result = bot.set_system_prompt(arg)
                        print(f"\n{result}")
                        
                elif command == '/save':
                    filename = arg if arg else None
                    result = bot.save_conversation(filename)
                    print(f"\n{result}")
                    
                elif command == '/load':
                    if not arg:
                        print("\n⚠ Usage: /load <filename>")
                        print("Use /list to see saved conversations")
                    else:
                        result = bot.load_conversation(arg)
                        print(f"\n{result}")
                        
                elif command == '/list':
                    result = bot.list_saved_conversations()
                    print(result)
                    
                elif command == '/stats':
                    result = bot.get_stats()
                    print(result)
                    
                else:
                    print(f"\n❌ Unknown command: {command}")
                    print("Type /help to see available commands")

            # Regular Chat with Streaming
            else:
                print(f"\n🤖 Bot: ", end='', flush=True)
                
                # Stream the response
                for chunk in bot.get_chat_response_stream(user_input):
                    print(chunk, end='', flush=True)
                
                print()  # New line after response

        except KeyboardInterrupt:
            print("\n\n⚠ Interrupted by user.")
            print("💾 Auto-saving conversation...")
            if bot.conversation_history:
                result = bot.save_conversation()
                print(result)
            print("\n👋 Goodbye!\n")
            break
            
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")
            print("Please try again or type /help for assistance.\n")

if __name__ == "__main__":
    main_loop()
