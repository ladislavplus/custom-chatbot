import sys
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
            elif command == '/set':
                options = list(self.bot.get_default_llm_params().keys())
            elif command in ('/system', '/delprompt', '/insert'):
                options = list(self.bot.get_prompts().keys())
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
- `/new` - Start a new conversation (current session is discarded)
- `/system [alias]` - Set system prompt from a saved alias or raw text. Lists aliases if none given.

## Prompt Library
- `/prompts` - List all saved prompts
- `/addprompt <alias> <text>` - Save a new prompt
- `/delprompt <alias>` - Delete a prompt
- `/insert <alias>` - Insert a saved prompt's text into the input box

## LLM Settings
- `/settings` - Display current LLM parameter settings
- `/set <param> <value>` - Set a parameter (e.g., temperature, max_tokens)
- `/reset` - Reset all parameters to their default values

## Save/Load
- `/save [filename]` - Save conversation to markdown
- `/load <filename>` - Load a previous conversation
- `/list` - List all saved conversations

## Examples
```
/system coder       → Switches to the 'coder' system prompt
/addprompt idea Generate five startup ideas
/insert idea        → Puts the saved prompt text into the input box
/set temperature 0.9
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

def print_prompts(bot):
    """Display saved prompts in a table"""
    prompts = bot.get_prompts()
    if not prompts:
        console.print("No saved prompts found.", style="dim")
        return

    table = Table(title="Saved Prompts", box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Alias", style="cyan", max_width=20)
    table.add_column("Prompt Text", style="dim")

    for alias, text in prompts.items():
        # Truncate long prompt text for display
        display_text = text.replace('\n', ' ')
        if len(display_text) > 100:
            display_text = display_text[:97] + "..."
        table.add_row(alias, display_text)
    
    console.print(table)

def print_conversations(conversations):
    """Display saved conversations in a table"""
    if not conversations:
        console.print("No saved conversations found.", style="dim")
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

def print_stats(stats):
    """Display conversation statistics"""
    # Overall stats
    table = Table(title="Overall Statistics", box=box.ROUNDED, show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold")
    table.add_row("Current model", stats['model'])
    table.add_row("Total messages", str(stats['total_messages']))
    table.add_row("Total tokens", str(stats['total_tokens']))
    console.print(table)

    # Per-model stats
    if stats['model_token_usage']:
        console.print("\n[bold]Token Usage by Model[/bold]")
        for model, tokens in sorted(stats['model_token_usage'].items(), key=lambda item: item[1], reverse=True):
            model_table = Table(title=f"Model: [cyan]{model}[/cyan]", box=box.MINIMAL, show_header=False)
            model_table.add_column("Metric", style="dim")
            model_table.add_column("Value", style="bold")
            model_table.add_row("Tokens Used", str(tokens))
            console.print(model_table)

        # Suggestion if multiple models were used
        if len(stats['model_token_usage']) > 1:
            suggestion = "[bold]Tip:[/] You\'ve used multiple models. Review the token usage to choose the most cost-effective model for your needs."
            console.print(Panel(suggestion, border_style="dim"))

def print_settings(bot):
    """Display LLM parameters in a table"""
    settings = bot.get_llm_params()
    defaults = bot.get_default_llm_params()
    
    table = Table(title="LLM Settings", box=box.ROUNDED, show_header=True, header_style="bold")
    table.add_column("Parameter", style="cyan")
    table.add_column("Current Value", style="bold")
    table.add_column("Default Value", style="dim")
    
    for param, default_value in defaults.items():
        current_value = settings.get(param)
        
        # Format values for display
        current_str = str(current_value) if current_value is not None else "None"
        default_str = str(default_value) if default_value is not None else "None"

        if current_str != default_str:
            table.add_row(param, f"[yellow]{current_str}[/yellow]", default_str)
        else:
            table.add_row(param, current_str, default_str)
            
    console.print(table)

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

def handle_model_switch(bot, arg):
    """Handle model switching with fuzzy matching and numbered selection"""
    if not arg:
        console.print("⚠ Usage: /switch <model_name_or_number>", style="yellow")
        console.print("Use /models to see available models", style="dim")
        return
    
    result = bot.switch_model(arg)
    
    if result[0] == "success":
        print_message("success", result[1])
    elif result[0] == "error":
        print_message("error", result[1])
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

def main_loop():
    """Main application loop"""
    bot = Chatbot()
    print_welcome(bot)
    
    # Create prompt session with history and auto-completion
    session = PromptSession(history=InMemoryHistory())
    insert_text_for_next_prompt = ""
    
    while True:
        try:
            # Use the new context-aware completer
            completer = CommandCompleter(bot)
            
            # Get the token count for the current model
            current_model_tokens = bot.model_token_usage.get(bot.active_model_friendly, 0)

            prompt_str = f"[{bot.active_model_friendly}"
            if current_model_tokens > 0:
                prompt_str += f"/{current_model_tokens}t"
            prompt_str += "]"

            # Get user input with auto-completion
            user_input = session.prompt(
                f"{prompt_str} You: ",
                completer=completer,
                complete_while_typing=True,
                default=insert_text_for_next_prompt
            )
            insert_text_for_next_prompt = "" # Reset after use
            
            if not user_input.strip():
                continue

            # Command Handling
            if user_input.startswith('/'):
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                arg = parts[1].strip() if len(parts) > 1 else ""

                if command in ('/quit', '/exit'):
                    # Auto-save on exit
                    if bot.conversation_history:
                        console.print("\n💾 Auto-saving conversation...", style="dim")
                        result = bot.save_conversation()
                        print_message(result[0], result[1])
                    console.print("\nGoodbye!\n", style="dim")
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
                        # If no arg, list available prompts and show current
                        console.print(Panel(bot.system_prompt['content'], title="[bold]Current System Prompt[/bold]", border_style="dim"))
                        print_prompts(bot)
                        print_message("info", "Usage: /system <alias> or /system <full prompt text>")
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

                elif command == '/settings':
                    print_settings(bot)

                elif command == '/reset':
                    result = bot.reset_llm_params()
                    print_message(result[0], result[1])

                elif command == '/set':
                    parts = arg.split(' ', 1)
                    if len(parts) < 2 or not arg.strip():
                        print_message("warning", "Usage: /set <parameter> <value>")
                        print_message("info", "Example: /set temperature 0.8")
                    else:
                        param_name, value_str = parts
                        result = bot.set_llm_param(param_name, value_str)
                        print_message(result[0], result[1])

                elif command == '/prompts':
                    print_prompts(bot)

                elif command == '/addprompt':
                    parts = arg.split(' ', 1)
                    if len(parts) < 2 or not arg.strip():
                        print_message("warning", "Usage: /addprompt <alias> <prompt text>")
                    else:
                        alias, text = parts
                        result = bot.add_prompt(alias, text)
                        print_message(result[0], result[1])

                elif command == '/delprompt':
                    if not arg:
                        print_message("warning", "Usage: /delprompt <alias>")
                    else:
                        result = bot.remove_prompt(arg)
                        print_message(result[0], result[1])

                elif command == '/insert':
                    if not arg:
                        print_message("warning", "Usage: /insert <alias>")
                    else:
                        text = bot.get_prompt_text(arg)
                        if text:
                            insert_text_for_next_prompt = text
                        else:
                            print_message("error", f"Alias '{arg}' not found.")
                    continue
                    
                else:
                    print_message("error", f"Unknown command: {command}")
                    console.print("Type /help to see available commands", style="dim")

            # Regular Chat with Streaming Markdown
            else:
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
                            break
                console.print()

        except KeyboardInterrupt:
            console.print("\n\n⚠ Interrupted by user.", style="yellow")
            if bot.conversation_history:
                console.print("💾 Auto-saving conversation...", style="dim")
                result = bot.save_conversation()
                print_message(result[0], result[1])
            console.print("\nGoodbye!\n", style="dim")
            break
            
        except EOFError:
            # Handle Ctrl+D
            break
            
        except Exception as e:
            console.print(f"\n✗ An unexpected error occurred: {e}", style="red")
            console.print("Please try again or type /help for assistance.\n", style="dim")

if __name__ == "__main__":
    main_loop()