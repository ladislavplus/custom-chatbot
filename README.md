# Custom Chatbot

A local, customizable Python command-line application that allows you to interact with a wide variety of Large Language Models (LLMs) through a rich, unified interface.

This application is powered by the [`litellm`](https://github.com/BerriAI/litellm) library, which provides a consistent interface for over 100 LLM providers, and is enhanced with a `rich` and `prompt_toolkit` powered UI for a modern command-line experience.

*(Image: A simple demo of the chatbot in action)*

## Features

-   **Flexible Model Configuration:** Easily add, remove, or switch between models from any `litellm`-supported provider via a simple `models_config.json` file.
-   **Advanced Command-Line UI:** A modern interface powered by `rich` and `prompt_toolkit`, featuring live-streaming markdown, syntax-highlighted tables, and command auto-completion.
-   **Fuzzy Model Switching:** Switch models on the fly with fuzzy name matching or by number.
-   **Full Conversation Management:**
    -   Save conversations to clean, readable Markdown files.
    -   Load previous conversations to continue where you left off.
    -   List all saved chats.
    -   Auto-saves the current session on exit.
-   **Customizable Personality:** Use the `/system` command to change the bot's personality or role at any time.
-   **Usage Statistics:** Track your conversation length and token usage with the `/stats` command.
-   **Secure API Key Management:** API keys are kept out of the source code and loaded securely from a `.env` file.

## Prerequisites

-   Python 3.8 or higher
-   (Optional) [Ollama](https://ollama.com/) installed and running for local model support.

## 1. Setup Instructions

### Step 1: Clone or Download the Project

First, get the project files onto your local machine.

```bash
# Example if using git
git clone <your-repo-url>
cd custom-chatbot
```

### Step 2: Create a Python Virtual Environment

It is highly recommended to use a virtual environment to manage dependencies.

```bash
# Create the virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

Install the required Python packages using pip.

```bash
pip install -r requirements.txt
```

### Step 4: Configure API Keys and Models

The application uses two configuration files: `.env` for API keys and `models_config.json` for model definitions.

1.  **API Keys:** Make a copy of the example `.env` file.
    ```bash
    # On Windows
    copy .env.example .env
    # On macOS/Linux
    cp .env.example .env
    ```
    Open the new `.env` file and add your API keys for the services you wish to use.

2.  **Models:** Make a copy of the example `models_config.json` file.
    ```bash
    # On Windows
    copy models_config.json.example models_config.json
    # On macOS/Linux
    cp models_config.json.example models_config.json
    ```
    Open `models_config.json` to see how models are defined. You can add, remove, or edit any model in this file. See the "Customizing Models" section below for more details.

### Step 5: (Optional) Set up Ollama for Local Models

If you want to run models completely offline:
1.  Download and install Ollama from [ollama.com](https://ollama.com/).
2.  Run the Ollama application.
3.  Pull a model, for example: `ollama run llama3`.
4.  Add the model to your `models_config.json`:
    ```json
    "ollama-llama3": {
      "litellm_string": "ollama/llama3",
      "provider": "Ollama",
      "description": "Llama 3 running locally via Ollama.",
      "use_case": "Local testing and development",
      "context_length": 8192
    }
    ```

## 2. How to Run

With your virtual environment active and your configuration files set up, start the application:

```bash
python main.py
```

You will be greeted with a welcome message and are now ready to chat!

## 3. Usage and Commands

Simply type your message and press Enter. To control the application, use the following slash commands. Use `Tab` to auto-complete commands and their arguments.

| Command | Description | Example |
| --- | --- | --- |
| `/help` | Displays the list of available commands. | `/help` |
| `/models` | Lists all available models from your config. | `/models` |
| `/switch <name>` | Switches the active model. Supports fuzzy matching and numbers. | `/switch llama` or `/switch 2` |
| `/system <prompt>` | Sets a new system prompt for the bot's personality. | `/system You are a pirate.` |
| `/new` | Starts a fresh chat session. | `/new` |
| `/save [filename]` | Saves the conversation to a Markdown file. | `/save my_convo` |
| `/load <filename>` | Loads a conversation from a file. | `/load my_convo` |
| `/list` | Lists all saved conversations. | `/list` |
| `/stats` | Shows statistics for the current session. | `/stats` |
| `/quit` or `/exit` | Exits the application (and auto-saves). | `/quit` |

## Customizing Models

Adding, editing, or removing models is done in the `models_config.json` file.

The file contains a single "models" object. Each key inside this object is the "friendly name" you'll use to refer to the model in the app.

### Structure of a Model Entry

```json
"friendly-name": {
  "litellm_string": "provider/model_name_string",
  "provider": "Provider Name",
  "description": "A short description of the model.",
  "use_case": "Example use case (optional).",
  "context_length": 1000000
}
```

-   `friendly-name`: The name you will use with `/switch` (e.g., "gemini-pro").
-   `litellm_string`: The official model string used by `litellm`. Refer to the [LiteLLM Supported Providers](https://docs.litellm.ai/docs/providers) documentation for a full list.
-   `provider`: The name of the provider (e.g., "Google", "Groq", "Ollama"). This is used for grouping models in the `/models` list.
-   `description`: A brief description that appears in the `/models` list.
-   `use_case` (Optional): A short description of the model's ideal use case.
-   `context_length` (Optional): The context length of the model.

### Example: Adding a New Model

To add Google's Gemini Pro, you would add the following to the `models` object in `models_config.json`:

```json
"gemini-pro": {
  "litellm_string": "gemini/gemini-2.5-pro",
  "provider": "Google",
  "description": "Most capable Gemini model",
  "context_length": 1000000,
  "use_case": "Complex reasoning and long context"
}
```

Remember to add your `ANTHROPIC_API_KEY` to the `.env` file, and `litellm` will handle the rest.