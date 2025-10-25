import sys
import logging
import logging.config
import argparse
import litellm
from chatbot import Chatbot
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from rich.live import Live
from prompt_toolkit.history import InMemoryHistory

# Initialize console for rich output
console = Console()

# --- Logging Configuration ---
LOGGING_ENABLED = False

def configure_logging(enabled):
    global LOGGING_ENABLED
    LOGGING_ENABLED = enabled
    if LOGGING_ENABLED:
        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s - %(levelname)s - %(message)s'
                },
            },
            'handlers': {
                'file': {
                    'level': 'INFO',
                    'class': 'logging.FileHandler',
                    'filename': 'chatbot.log',
                    'formatter': 'standard',
                    'encoding': 'utf-8',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['file'],
                    'level': 'INFO',
                    'propagate': False
                },
                'litellm': {
                    'handlers': ['file'],
                    'level': 'CRITICAL',
                    'propagate': False
                }
            }
        })
    else:
        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': True,
            'handlers': {
                'null': {
                    'class': 'logging.NullHandler',
                },
            },
            'loggers': {
                '': {
                    'handlers': ['null'],
                    'level': 'CRITICAL',
                },
                 'litellm': {
                    'handlers': ['null'],
                    'level': 'CRITICAL',
                    'propagate': False
                }
            }
        })

# --- End Logging Configuration ---

class CommandCompleter(Completer):
    def __init__(self, bot):
        self.bot = bot
        self.commands = bot.get_command_completions()

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        
        if not text.startswith('/'):
            return

        parts = text.split(' ')
        
        if ' ' not in text:
            # Completing the command itself
            for command in self.commands:
                if command.startswith(text):
                    yield Completion(command, start_position=-len(text))
        
        elif len(parts) == 2:
            command = parts[0]
            arg_text = parts[1]
            
            # Update completions dynamically
            if command == '/switch':
                options = self.bot.get_model_names()
            elif command == '/load':
                options = self.bot.get_saved_filenames()
            elif command == '/logging':
                options = ['ON', 'OFF']
            else:
                options = []
            
            for option in options:
                if option.startswith(arg_text):
                    yield Completion(option, start_position=-len(arg_text))

def print_help():
    """Display help information"""
    help_text = """
# Custom Chatbot - Commands

## Basic Commands
- `/help` - Show this help message
- `/quit` or `/exit` - Exit the application

## Model Management
- `/models` - List all available AI models
- `/switch <model>` - Switch to a different model (supports fuzzy matching and numbers)
- `/stats` - Show conversation statistics

## Conversation Management
- `/new` - Start a new conversation
- `/system <prompt>` - Set a new system prompt

## Save/Load
- `/save [filename]` - Save conversation to markdown
- `/load <filename>` - Load a previous conversation
- `/list` - List all saved conversations

## Logging
- `/logging <ON/OFF>` - Enable or disable logging

## Examples
```
/switch gemini      → Fuzzy matches to gemini-pro
/switch 3           → Switches to model #3
/save my_chat       → Saves as my_chat.md
/load my_chat       → Loads my_chat.md
```
"""
    console.print(Markdown(help_text))

def print_welcome(bot):
    """Display welcome message"""
    welcome = Panel(
        f"[bold]Custom Chatbot[/bold]\n\nCurrent model: [cyan]{bot.active_model_friendly}[/cyan]\n\nType [yellow]/help[/yellow] for commands or start chatting!",
        box=box.ROUNDED,
        border_style="dim"
    )
    console.print(welcome)
    if LOGGING_ENABLED: logging.info("Welcome message displayed.")

def print_models(bot):
    """Display available models in a formatted table"""
    models_by_provider, indexed = bot.get_models_list()
    
    for provider, models in sorted(models_by_provider.items()):
        table = Table(title=f"{provider} Models", box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("#", style="dim", width=3)
        table.add_column("Model", style="cyan")
        table.add_column("Description", style="dim")
        
        for model in models:
            marker = "→" if model["current"] else " "
            table.add_row(
                f"{marker}{model['index']}",
                model["name"],
                model["description"]
            )
        
        console.print(table)
        console.print()
    if LOGGING_ENABLED: logging.info("Displayed available models.")

def print_conversations(conversations):
    """Display saved conversations in a table"""
    if not conversations:
        console.print("No saved conversations found.", style="dim")
        if LOGGING_ENABLED: logging.info("No saved conversations found.")
        return
    
    table = Table(title="Saved Conversations", box=box.SIMPLE, show_header=True)
    table.add_column("Filename", style="cyan")
    table.add_column("Size", justify="right", style="dim")
    table.add_column("Modified", style="dim")
    
    for conv in conversations:
        size_kb = conv['size'] / 1024
        modified = conv['modified'].strftime('%Y-%m-%d %H:%M')
        table.add_row(conv['name'], f"{size_kb:.1f} KB", modified)
    
    console.print(table)
    if LOGGING_ENABLED: logging.info("Displayed saved conversations.")

def print_stats(stats):
    """Display conversation statistics"""
    table = Table(title="Conversation Statistics", box=box.ROUNDED, show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")
    
    table.add_row("Model", stats['model'])
    table.add_row("Total messages", str(stats['total_messages']))
    table.add_row("User messages", str(stats['user_messages']))
    table.add_row("Assistant messages", str(stats['assistant_messages']))
    if stats['total_tokens'] > 0:
        table.add_row("Total tokens", str(stats['total_tokens']))
    
    console.print(table)
    if LOGGING_ENABLED: logging.info("Displayed conversation statistics.")

def print_message(msg_type, content):
    """Print formatted messages based on type"""
    if msg_type == "success":
        console.print(f"✓ {content}", style="green")
    elif msg_type == "error":
        console.print(f"✗ {content}", style="red")
    elif msg_type == "warning":
        console.print(f"⚠ {content}", style="yellow")
    elif msg_type == "info":
        console.print(content, style="dim")
    else:
        console.print(content)
    if LOGGING_ENABLED: logging.info(f"Printed message: type={msg_type}, content='{content}'")

def handle_model_switch(bot, arg):
    """Handle model switching with fuzzy matching and numbered selection"""
    if not arg:
        console.print("⚠ Usage: /switch <model_name_or_number>", style="yellow")
        console.print("Use /models to see available models", style="dim")
        if LOGGING_ENABLED: logging.warning("Missing argument for /switch command.")
        return
    
    result = bot.switch_model(arg)
    
    if result[0] == "success":
        print_message("success", result[1])
        if LOGGING_ENABLED: logging.info(f"Switched model to {arg}.")
    elif result[0] == "error":
        print_message("error", result[1])
        if LOGGING_ENABLED: logging.error(f"Failed to switch model: {result[1]}")
    elif result[0] == "multiple":
        # Multiple matches found
        console.print("\nMultiple models match your query:", style="yellow")
        for i, (name, score) in enumerate(result[1], 1):
            console.print(f"  {i}. [cyan]{name}[/cyan]", style="dim")
        
        try:
            choice = console.input("\n[yellow]Select a model (1-5) or press Enter to cancel:[/yellow] ")
            if choice and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(result[1]):
                    model_name = result[1][idx][0]
                    handle_model_switch(bot, model_name)
        except (ValueError, IndexError):
            print_message("error", "Invalid selection")
            if LOGGING_ENABLED: logging.error("Invalid model selection.")

def main_loop():
    """Main application loop"""
    if LOGGING_ENABLED: logging.info("Starting main loop.")
    bot = Chatbot()
    print_welcome(bot)
    
    # Create prompt session with history and auto-completion
    session = PromptSession(history=InMemoryHistory())
    
    while True:
        try:
            # Use the new context-aware completer
            completer = CommandCompleter(bot)
            
            # Get user input with auto-completion
            user_input = session.prompt(
                f"[{bot.active_model_friendly}] You: ",
                completer=completer,
                complete_while_typing=True
            )
            
            if not user_input.strip():
                continue

            # Command Handling
            if user_input.startswith('/'):
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                if LOGGING_ENABLED: logging.info(f"Received command: {command} with arg: '{arg}'")

                if command in ('/quit', '/exit'):
                    # Auto-save on exit
                    if bot.conversation_history:
                        console.print("\n💾 Auto-saving conversation...", style="dim")
                        result = bot.save_conversation()
                        print_message(result[0], result[1])
                    console.print("\nGoodbye!\n", style="dim")
                    if LOGGING_ENABLED: logging.info("Exiting application.")
                    break
                    
                elif command == '/help':
                    print_help()
                    
                elif command == '/models':
                    print_models(bot)
                    
                elif command == '/new':
                    result = bot.start_new_chat()
                    print_message("success", result)
                    
                elif command == '/switch':
                    handle_model_switch(bot, arg)
                        
                elif command == '/system':
                    if not arg:
                        console.print("⚠ Usage: /system <new_prompt>", style="yellow")
                        console.print("Example: /system You are a helpful coding assistant", style="dim")
                    else:
                        result = bot.set_system_prompt(arg)
                        print_message("success", result)
                        
                elif command == '/save':
                    filename = arg if arg else None
                    result = bot.save_conversation(filename)
                    print_message(result[0], result[1])
                    
                elif command == '/load':
                    if not arg:
                        console.print("⚠ Usage: /load <filename>", style="yellow")
                        console.print("Use /list to see saved conversations", style="dim")
                    else:
                        result = bot.load_conversation(arg)
                        print_message(result[0], result[1])
                        if result[0] == 'success':
                            console.print(f"Current model set to [cyan]{bot.active_model_friendly}[/cyan].")

                elif command == '/list':
                    conversations = bot.list_saved_conversations()
                    if conversations is None:
                        print_message("error", "Error listing conversations")
                    else:
                        print_conversations(conversations)
                    
                elif command == '/stats':
                    stats = bot.get_stats()
                    print_stats(stats)
                
                elif command == '/logging':
                    if arg.upper() == 'ON':
                        configure_logging(True)
                        print_message("success", "Logging enabled.")
                    elif arg.upper() == 'OFF':
                        configure_logging(False)
                        print_message("success", "Logging disabled.")
                    else:
                        print_message("error", "Usage: /logging <ON/OFF>")
                    
                else:
                    print_message("error", f"Unknown command: {command}")
                    console.print("Type /help to see available commands", style="dim")

            # Regular Chat with Streaming Markdown
            else:
                if LOGGING_ENABLED: logging.info(f"User input: '{user_input}'")
                console.print()
                response_text = ""
                
                with Live(console=console, auto_refresh=False) as live:
                    live.update(Markdown("**Bot:**"), refresh=True)
                    # Stream the response
                    for msg_type, content in bot.get_chat_response_stream(user_input):
                        if msg_type == "content":
                            response_text += content
                            live.update(Markdown(f"**Bot:**\n{response_text}"), refresh=True)
                        elif msg_type == "error":
                            console.print(f"\n✗ {content}", style="red")
                            if LOGGING_ENABLED: logging.error(f"Error during response streaming: {content}")
                            break
                console.print()
                if LOGGING_ENABLED: logging.info(f"Bot response: '{response_text}'")

        except KeyboardInterrupt:
            console.print("\n\n⚠ Interrupted by user.", style="yellow")
            if bot.conversation_history:
                console.print("💾 Auto-saving conversation...", style="dim")
                result = bot.save_conversation()
                print_message(result[0], result[1])
            console.print("\nGoodbye!\n", style="dim")
            if LOGGING_ENABLED: logging.info("Exiting application due to KeyboardInterrupt.")
            break
            
        except EOFError:
            # Handle Ctrl+D
            if LOGGING_ENABLED: logging.info("Exiting application due to EOFError.")
            break
            
        except Exception as e:
            console.print(f"\n✗ An unexpected error occurred: {e}", style="red")
            console.print("Please try again or type /help for assistance.\n", style="dim")
            if LOGGING_ENABLED: logging.exception("An unexpected error occurred in the main loop.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Custom Chatbot')
    parser.add_argument('--logging', type=str.upper, choices=['ON', 'OFF'], default='OFF', help='Enable or disable logging')
    args = parser.parse_args()

    configure_logging(args.logging == 'ON')

    if LOGGING_ENABLED: logging.info("Application starting.")
    main_loop()
    if LOGGING_ENABLED: logging.info("Application finished.")