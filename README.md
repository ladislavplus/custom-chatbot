# Custom Chatbot

A local, customizable Python command-line application that allows you to interact with a wide variety of Large Language Models (LLMs) through a unified interface.

This application is powered by the [`litellm`](https://github.com/BerriAI/litellm) library, which provides a single, consistent interface for over 100 LLM providers. This makes it incredibly easy to switch between models from OpenAI, Groq, local Ollama instances, and many more.

 
*(Image: A simple demo of the chatbot in action)*

## Features

-   **Multi-Model Support:** Easily switch between different AI models from various providers.
-   **Unified Interface:** A single, simple command-line interface for all models.
-   **Command System:** Control the application with intuitive slash commands (e.g., `/switch`, `/models`).
-   **Conversation History:** The chatbot remembers the context of your current conversation.
-   **Customizable Personality:** Use the `/system` command to change the bot's personality or role on the fly.
-   **Secure API Key Management:** Your API keys are kept out of the source code and loaded securely from a `.env` file.

## Prerequisites

-   Python 3.8 or higher
-   (Optional) [Ollama](https://ollama.com/) installed and running for local model support.

## 1. Setup Instructions

### Step 1: Clone or Download the Project

First, get the project files onto your local machine.

```bash
# Example if using git
git clone <your-repo-url>
cd custom_chatbot
```
Or, simply create a `custom_chatbot` folder and place the provided Python files inside it.

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

### Step 4: Configure API Keys

The application uses a `.env` file to securely load your API keys.

1.  Make a copy of the example file:
    ```bash
    # On Windows
    copy .env.example .env
    # On macOS/Linux
    cp .env.example .env
    ```
2.  Open the new `.env` file in a text editor.
3.  Add your API keys for the services you wish to use. You only need to fill in the ones you have.

    ```ini
    # .env
    OPENAI_API_KEY="sk-..."
    GROQ_API_KEY="gsk_..."
    ```

### Step 5: (Optional) Set up Ollama for Local Models

If you want to run models completely offline:
1.  Download and install Ollama from [ollama.com](https://ollama.com/).
2.  Run the Ollama application.
3.  Pull a model from the command line, for example:
    ```bash
    ollama run llama3
    ```
The chatbot will automatically detect and connect to your running Ollama instance.

## 2. How to Run

With your virtual environment active and your `.env` file configured, start the application by running `main.py`:

```bash
python main.py
```

You will be greeted with a welcome message and are now ready to chat!

## 3. Usage and Commands

Simply type your message and press Enter to chat with the currently active model. To control the application, use the following slash commands:

| Command               | Description                                                               | Example                                   |
| --------------------- | ------------------------------------------------------------------------- | ----------------------------------------- |
| `/help`               | Displays the list of available commands.                                  | `/help`                                   |
| `/models`             | Lists all the AI models you can switch to.                                | `/models`                                 |
| `/switch <model_name>`| Switches the active AI model for the conversation.                        | `/switch groq-llama3-8b`                  |
| `/system <prompt>`    | Sets a new system prompt to define the bot's personality or role.         | `/system You are a sarcastic pirate.`     |
| `/new`                | Clears the current conversation history and starts a fresh chat.          | `/new`                                    |
| `/quit` or `/exit`    | Exits the application.                                                    | `/quit`                                   |

## Adding New Models

Thanks to `litellm`, adding a new model is incredibly simple:

1.  Open the `chatbot.py` file.
2.  Find the `AVAILABLE_MODELS` dictionary.
3.  Add a new entry with a "friendly name" as the key and the official `litellm` model string as the value.

For example, to add Anthropic's Claude 3 Haiku, you would add:
```python
AVAILABLE_MODELS = {
    # ... existing models
    "claude-3-haiku": "anthropic/claude-3-haiku-20240307",
}
```
4.  Make sure you have the corresponding API key (e.g., `ANTHROPIC_API_KEY`) set in your `.env` file. `litellm` will automatically find and use it.

Refer to the [LiteLLM Supported Providers](https://docs.litellm.ai/docs/providers) documentation for a full list of available model strings.
