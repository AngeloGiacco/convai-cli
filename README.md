# ElevenLabs Conversational AI Agent Manager CLI

A powerful CLI tool to manage ElevenLabs Conversational AI agents using local configuration files. Features hash-based change detection, templates, multi-environment support, and continuous syncing.

## Features

- **Complete Agent Configuration**: Full ElevenLabs agent schema support (ASR, TTS, platform settings, etc.)
- **Template System**: Pre-built templates for common use cases
- **Multi-environment Support**: Deploy across dev, staging, production
- **Hash-based Updates**: Only sync when configuration actually changes
- **Continuous Monitoring**: Watch mode for automatic updates
- **Agent Import**: Fetch existing agents from ElevenLabs workspace
- **Configuration Validation**: Built-in config validation

## Installation

```bash
git clone <repository_url>
cd elevenlabs_cli
poetry install
poetry shell  # optional
```

## Configuration

Set your ElevenLabs API key:
```bash
export ELEVENLABS_API_KEY="your_api_key_here"
```

## Quick Start

```bash
# 1. Initialize project
convai init

# 2. Create agent with template
convai add "Customer Support Bot" --template customer-service

# 3. Edit configuration
# agent_configs/customer_support_bot.json

# 4. Validate and sync
convai validate agent_configs/customer_support_bot.json
convai sync

# 5. Watch for changes (optional)
convai watch
```

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

## Command Reference

| Command | Description |
|---------|-------------|
| `convai init` | Initialize a new project |
| `convai add <name>` | Create a new agent |
| `convai templates-list` | List available templates |
| `convai template-show <template>` | Show template configuration |
| `convai fetch` | Import agents from ElevenLabs |
| `convai validate <config>` | Validate configuration file |
| `convai sync` | Synchronize agents with ElevenLabs |
| `convai status` | Show agent status |
| `convai list-agents` | List configured agents |
| `convai watch` | Monitor and auto-sync changes |

your_project/
├── agents.json # Central agent configuration
├── agent_configs/ # Individual agent configs
├── convai.lock # State tracking
└── tests/ # Test files (optional)


## Templates

Available templates:
- **default**: Complete configuration with all fields
- **minimal**: Essential fields only
- **voice-only**: Voice conversation optimized
- **text-only**: Text conversation optimized
- **customer-service**: Customer support scenarios
- **assistant**: General AI assistant

```bash
# List templates
convai templates-list

# View template
convai template-show customer-service

# Use template
convai add "Agent Name" --template minimal
```

## Core Commands

### Project Management
```bash
convai init                              # Initialize project
convai add "Agent Name"                  # Create new agent
convai add "Agent" --template voice-only # Create with template
convai fetch                             # Import existing agents
```

### Configuration
```bash
convai validate config.json             # Validate config
convai sync                              # Sync all agents
convai sync --dry-run                    # Preview changes
convai sync --env production             # Environment-specific
```

### Monitoring
```bash
convai status                            # Show agent status
convai list-agents                       # List all agents
convai watch                             # Auto-sync on changes
```

## Agent Configuration

### Minimal Example
```json
{
    "name": "Support Bot",
    "conversation_config": {
        "agent": {
            "prompt": {
                "prompt": "You are a helpful customer service representative.",
                "llm": "gemini-2.0-flash",
                "temperature": 0.1
            },
            "language": "en"
        },
        "tts": {
            "model_id": "eleven_turbo_v2",
            "voice_id": "cjVigY5qzO86Huf0OWal"
        }
    },
    "tags": ["customer-service"]
}
```

### Complete Configuration
The CLI supports the full ElevenLabs schema including:
- **ASR Configuration**: Quality, provider, audio format
- **TTS Configuration**: Model, voice, streaming settings
- **Agent Settings**: Prompts, LLM, tools, knowledge base
- **Platform Settings**: Widget, privacy, call limits
- **Safety Controls**: Content filtering, evaluation

## Common Workflows

### New Project
```bash
convai init
convai add "My Agent" --template assistant
# Edit agent_configs/my_agent.json
convai sync
```

### Import Existing
```bash
convai init
convai fetch
convai status
convai sync
```

### Multi-Environment
```bash
convai add "[dev] Bot" --template customer-service
convai add "[prod] Bot" --template customer-service
# Edit configs for each environment
convai sync --env development
convai sync --env production
```

### Continuous Development
```bash
convai watch &
# Edit configs in another terminal - changes auto-sync
```

## Central Configuration (agents.json)

```json
{
    "agents": [
        {
            "name": "Production Support Agent",
            "id": "agent-id-from-elevenlabs",
            "config": "agent_configs/support_agent.json",
            "test_cases": "tests/test_support.py"
        }
    ]
}
```

## Troubleshooting

**Common Issues:**
1. **API Key**: Ensure `ELEVENLABS_API_KEY` is set
2. **Validation**: Use `convai validate` for config errors
3. **Sync Issues**: Check IDs in `convai.lock`
4. **Templates**: Use `convai templates-list` for available options

**Get Help:**
```bash
convai --help
convai <command> --help
convai status
```

## Command Reference

| Command | Description |
|---------|-------------|
| `convai init` | Initialize project |
| `convai add <name>` | Create new agent |
| `convai templates-list` | List available templates |
| `convai template-show <template>` | Show template configuration |
| `convai fetch` | Import agents from ElevenLabs |
| `convai validate <config>` | Validate configuration |
| `convai sync` | Synchronize agents |
| `convai status` | Show agent status |
| `convai list-agents` | List configured agents |
| `convai watch` | Monitor and auto-sync changes |

## Development

```bash
poetry run pytest
```