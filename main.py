# main.py

from chatbot import Chatbot
import os
from dotenv import load_dotenv


def print_help():
    print("\n--- Custom Chatbot Commands ---")
    print("/help               - Show this help message")
    print("/models             - List all available AI models")
    print("/switch <model>     - Switch to a different AI model (e.g., /switch gpt-4o)")
    print("/system <prompt>    - Set a new system prompt for the bot's personality")
    print("/new                - Start a new, fresh conversation")
    print("/quit or /exit      - Exit the application")
    print("---------------------------------\n")

def main_loop():
    bot = Chatbot()
    print("Welcome to Custom Chatbot!")
    print(f"Current model set to: {bot.active_model_name}")
    print('Type /help for a list of commands.')

    while True:
        try:
            user_input = input("\nYou: ")
            
            if not user_input.strip():
                continue

            # Command Handling
            if user_input.startswith('/'):
                parts = user_input.split(' ', 1)
                command = parts[0]
                arg = parts[1] if len(parts) > 1 else ""

                if command in ('/quit', '/exit'):
                    print("Goodbye!")
                    break
                elif command == '/help':
                    print_help()
                elif command == '/models':
                    print(bot.list_models())
                elif command == '/new':
                    print(bot.start_new_chat())
                elif command == '/switch':
                    if not arg:
                        print("Usage: /switch <model_name>")
                    else:
                        print(bot.switch_model(arg))
                elif command == '/system':
                    if not arg:
                        print("Usage: /system <new_prompt>")
                    else:
                        print(bot.set_system_prompt(arg))
                else:
                    print(f"Unknown command: {command}")

            # Regular Chat
            else:
                response = bot.get_chat_response(user_input)
                print(f"\nBot: {response}")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

def check_certif():
    # load_dotenv()
    load_dotenv(override=True)
    print("SSL_CERT_FILE = ", os.getenv("SSL_CERT_FILE"))

if __name__ == "__main__":
    main_loop()
    # check_certif()

