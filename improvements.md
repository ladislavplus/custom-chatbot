Here is a list of possible enhancements for the `custom_chatbot` application.
This can serve as a roadmap for future development.

---

# Custom Chatbot: Potential Improvements & Future Roadmap

This document outlines potential features and enhancements for the `custom_chatbot` application. The ideas are categorized into tiers, from high-impact user-facing features to code quality and architectural improvements.

## Tier 1: Core Functionality & User Experience Enhancements

*These are high-impact features that would significantly improve the app's day-to-day usability.*

### 1. Streaming Responses
-   **Problem:** Currently, the user has to wait for the entire response to be generated before seeing any text, which can feel slow for long answers.
-   **Improvement:** Modify the `litellm` call to enable streaming (`stream=True`). This would involve iterating over the response chunks and printing them to the console as they arrive, giving the user immediate feedback.
-   **Implementation:**
    ```python
    # In chatbot.py
    response = litellm.completion(..., stream=True)
    full_response = ""
    for chunk in response:
        content = chunk.choices[0].delta.content or ""
        print(content, end='', flush=True)
        full_response += content
    ```

### 2. Save & Load Conversation History
-   **Problem:** All conversation history is lost when the application is closed.
-   **Improvement:** Add `/save <filename>` and `/load <filename>` commands.
    -   `/save`: Writes the `conversation_history` list to a file (e.g., JSON or Markdown).
    -   `/load`: Reads a previously saved file, populates the conversation history, and allows the user to continue a past conversation.
-   **Implementation:** Use Python's `json` library to dump and load the list of message dictionaries.

### 3. External Configuration File
-   **Problem:** The list of available models is hardcoded in `chatbot.py`. Changing settings requires editing the source code.
-   **Improvement:** Create a `config.yaml` or `config.toml` file to manage application settings.
-   **Configurable Items:**
    -   The list of available models.
    -   The default model on startup.
    -   The default system prompt.
    -   Model parameters like `temperature` or `max_tokens`.
-   **Implementation:** Use a library like `PyYAML` or `tomli` to parse the configuration file at startup.

### 4. Graphical User Interface (GUI)
-   **Problem:** The CLI is functional but not as user-friendly or visually appealing as a graphical interface.
-   **Improvement:** Wrap the chatbot logic in a simple web-based GUI. This would be the single biggest leap forward for the app's usability.
-   **Recommended Libraries:**
    -   **Streamlit:** Excellent for quickly building beautiful data and chat applications with pure Python.
    -   **Gradio:** Very simple to set up and great for creating demos for machine learning models.

### 5. Improved Multi-line Input
-   **Problem:** The standard `input()` function in the CLI makes it difficult to paste or write multi-line code snippets or prompts.
-   **Improvement:** Implement a more robust input mechanism.
    -   **Simple:** Allow users to use a special character (e.g., `"""` or `[END]`) to signal the end of a multi-line prompt.
    -   **Advanced:** Use a library like `prompt_toolkit` to create a more powerful terminal interface that naturally handles multi-line input and even offers syntax highlighting.

---

## Tier 2: Advanced Features & Extensibility

*These features would transform the app from a simple chat client into a more powerful and intelligent tool.*

### 1. Cost Tracking & Budgeting
-   **Problem:** Using proprietary models costs money, and it's easy to lose track of API expenses.
-   **Improvement:** Use `litellm`'s built-in cost tracking to display the cost of each interaction and the total cost for the session.
-   **Implementation:**
    ```python
    # After a successful litellm call
    cost = litellm.completion_cost(completion_response=response)
    print(f"\nCost for this completion: ${cost:.6f}")
    # Add this to a running session total.
    ```

### 2. Retrieval-Augmented Generation (RAG) - "Chat with your Documents"
-   **Problem:** The chatbot only knows what it was trained on and has no knowledge of your local files or data.
-   **Improvement:** Add a RAG pipeline. This would allow a user to point the chatbot at a directory of documents (PDFs, text files, etc.) and ask questions about their content.
-   **High-Level Steps:**
    1.  Add a command like `/load_docs <path>`.
    2.  Use a library like `langchain` or `llama-index` to load and split the documents.
    3.  Generate embeddings for the document chunks.
    4.  Store the embeddings in a local vector database (e.g., `ChromaDB`, `FAISS`).
    5.  When the user asks a question, retrieve the most relevant document chunks and inject them as context into the prompt sent to the LLM.

### 3. Function Calling / Tool Use
-   **Problem:** The chatbot can only talk; it cannot perform actions.
-   **Improvement:** Implement support for function calling, allowing the LLM to use pre-defined Python functions as "tools."
-   **Example Use Cases:**
    -   `get_current_weather("San Francisco")`
    -   `run_python_code("print(2+2)")`
    -   `search_web("latest AI news")`
-   **Implementation:** `litellm` supports the `tools` parameter for many models. Define your functions, pass them in the `litellm.completion` call, and handle the model's request to execute a function.

### 4. Model Parameter Control
-   **Problem:** The user has no control over the creativity (`temperature`) or length (`max_tokens`) of the model's output.
-   **Improvement:** Add commands to adjust these parameters on the fly.
    -   `/set temperature 0.8`
    -   `/set max_tokens 2048`
-   **Implementation:** Store these parameters in the `Chatbot` class and pass them into the `litellm.completion()` call.

---

## Tier 3: Code Quality & Developer Experience

*These improvements focus on making the codebase more robust, maintainable, and easier to distribute.*

### 1. Comprehensive Logging
-   **Problem:** Debugging is difficult as the application only prints to the console.
-   **Improvement:** Integrate Python's built-in `logging` module to write detailed logs to a file (`chatbot.log`).
-   **What to Log:**
    -   Application start and end times.
    -   Model switches.
    -   API errors with full tracebacks.
    -   Session costs.

### 2. Refactor Command Handling
-   **Problem:** The `if/elif` chain in `main.py` will become long and cumbersome as more commands are added.
-   **Improvement:** Refactor the command handling logic into a dictionary-based dispatcher (a "command map").
-   **Implementation:**
    ```python
    # In main.py
    command_map = {
        "/help": bot.print_help,
        "/models": bot.list_models,
        # ... etc.
    }
    handler = command_map.get(command)
    if handler:
        handler(arg)
    ```

### 3. Unit and Integration Testing
-   **Problem:** There are no automated tests, making it risky to add new features or refactor existing code.
-   **Improvement:** Add a testing suite using `pytest`.
-   **What to Test:**
    -   Command parsing logic.
    -   Correct functioning of `switch_model`, `set_system_prompt`, etc.
    -   Mock API calls to ensure `litellm` is being called with the correct parameters.

### 4. Packaging for Distribution
-   **Problem:** The application can only be run from the source code.
-   **Improvement:** Package the application so it can be easily installed and run.
-   **Options:**
    -   **`pyinstaller`:** Bundle the application and its dependencies into a single standalone executable for different operating systems.
    -   **`pyproject.toml` / `setup.py`:** Create a proper Python package that can be installed via `pip` (e.g., `pip install .`).
