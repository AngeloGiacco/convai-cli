# ElevenLabs Conversational AI Agent Manager CLI

A powerful command-line interface (CLI) tool to manage your ElevenLabs Conversational AI agents using local configuration files. This tool enables testing and creation of agents across different environments with continuous updates via CLI. It only updates agents in ElevenLabs when their configuration hash changes, making it efficient for development and production workflows.

## Features

*   **Agent Configuration Management**: Define agents in a centralized `agents.json` file with support for different environments
*   **Hash-based Change Detection**: Only sync agents when their configuration actually changes
*   **Continuous Monitoring**: Watch mode automatically syncs agents when config files change
*   **Multi-environment Support**: Deploy the same agent across dev, staging, and production environments
*   **Integrated Testing**: Run tests for your agents with built-in test management
*   **Lock File System**: Track agent states and prevent unnecessary API calls
*   **Flexible Agent Structure**: Support custom config paths and test files per agent

## Prerequisites

*   Python 3.8+
*   An ElevenLabs account and API Key.

## Installation

This tool is built with Poetry.

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <repository_url>
    cd elevenlabs_cli
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

3.  **Activate the virtual environment (optional, but recommended):**
    ```bash
    poetry shell
    ```
    Alternatively, you can run commands using `poetry run <command>`.

## Configuration

Set your ElevenLabs API key as an environment variable:

```bash
export ELEVENLABS_API_KEY="your_api_key_here"
```
The CLI tool will use this key to authenticate with the ElevenLabs API.

## Directory Structure

The tool uses a flexible directory structure in your project:

```
your_project_root/
├── agents.json              # Central agent configuration file
├── agent_configs/           # Agent configuration files
│   ├── docs_support_agent.json
│   ├── customer_service_dev.json
│   └── sales_assistant_staging.json
├── tests/                   # Test files for agents
│   ├── test_docs_support.py
│   ├── test_customer_service.py
│   └── test_sales_assistant.py
├── convai.lock              # Lock file to store agent IDs and config hashes
└── pyproject.toml           # Project metadata and dependencies
```

### Central Agent Configuration (agents.json)

The `agents.json` file defines all your agents and their associated files:

```json
{
    "agents": [
        {
            "name": "[prod] Docs support agent",
            "id": "q6EtujId97WBxLEUlEgQ",
            "config": "agent_configs/docs_support_agent.json",
            "test_cases": "tests/test_docs_support.py"
        },
        {
            "name": "[dev] Customer service bot",
            "config": "agent_configs/customer_service_dev.json", 
            "test_cases": "tests/test_customer_service.py"
        }
    ]
}
```

## Quick Start

Here's how to get started in under 2 minutes:

```bash
# 1. Initialize your project
convai init

# 2. Add a new agent (creates config + uploads to ElevenLabs)
convai add "Customer Support Bot"

# 3. Edit the generated config file to customize your agent
# agent_configs/customer_support_bot.json

# 4. Sync changes to ElevenLabs
convai sync

# 5. Watch for automatic updates (optional)
convai watch
```

That's it! Your agent is now live and will automatically update whenever you change the config.

## Usage

The main entry point for the CLI is `convai` (after installation). You can also run it via `poetry run convai` or `python -m elevenlabs_cli_tool.main`.

### 1. Initialize Project

Run this command in the root of your project where you want to manage agents.

```bash
convai init
```
This will create:
*   An `agents.json` file
*   A `convai.lock` file

### 2. Add a New Agent

Create a new agent - this will create the config file, upload to ElevenLabs, and save the ID:

```bash
convai add "Docs support agent"
```

This will:
*   Create a config file at `agent_configs/docs_support_agent.json` with default settings
*   Upload the agent to ElevenLabs and get an ID
*   Add the agent to `agents.json` with the ID
*   Update the lock file

You can also specify a custom config path:
```bash
convai add "Customer service bot" --config-path "configs/custom_bot.json"
```

### 3. Configure Your Agent

Edit the generated config file (e.g., `agent_configs/docs_support_agent.json`):

```json
{
    "name": "Docs support agent",
    "conversation_config": {
        "model_id": "eleven_turbo_v2",
        "prompt_template": "You are a helpful documentation support agent...",
        "max_tokens": 300,
        "temperature": 0.3
    },
    "platform_settings": {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "stability": 0.75,
        "similarity_boost": 0.75
    },
    "tags": ["support", "documentation"]
}
```

### 4. Sync Changes

After editing agent configs, sync the changes to ElevenLabs:

```bash
# Sync all agents
convai sync

# Sync with dry run to see what would happen
convai sync --dry-run

# Sync for a specific environment
convai sync --env production
```

### 5. Watch Mode for Continuous Updates

Enable automatic syncing when config files change:

```bash
# Watch for changes and auto-sync
convai watch

# Watch with custom interval
convai watch --interval 10 --env production
```

### 6. Check Agent Status

View the current status of all agents:

```bash
convai status
```

### 7. List Agents

View all configured agents:

```bash
convai list-agents
```

## Common Workflows

### Managing Multiple Environments

```bash
# Add agents for different environments
convai add "[dev] Support Bot"
convai add "[prod] Support Bot" 

# Edit configs for different environments
# agent_configs/dev_support_bot.json - relaxed settings for development
# agent_configs/prod_support_bot.json - production-ready settings

# Sync specific environments
convai sync --env development
convai sync --env production
```

### Continuous Development Workflow

```bash
# Start watching for changes
convai watch --interval 5

# In another terminal, edit your agent configs
# Changes will automatically sync to ElevenLabs!

# Check status anytime
convai status
```

### Working with Existing Agents

If you already have agents in ElevenLabs, you can add them to your project:

```bash
# Initialize project
convai init

# Manually edit agents.json to add existing agents:
{
    "agents": [
        {
            "name": "My Existing Agent",
            "id": "your-existing-agent-id",
            "config": "agent_configs/existing_agent.json"
        }
    ]
}

# Create the config file with current settings
# Then sync to ensure everything is in sync
convai sync
```

## Development

(Optional: Add notes for developers if this project were to be contributed to, e.g., how to run tests)

```bash
poetry run pytest
```
