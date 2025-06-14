#!/usr/bin/env python3

import os
import sys
import json
import typing
from pathlib import Path
from dotenv import load_dotenv

import typer
from elevenlabs import ElevenLabs, ConversationalConfig
from elevenlabs.types import AgentPlatformSettingsRequestModel
from elevenlabs.client import OMIT

load_dotenv()

from . import utils
from . import elevenlabsapi
from . import templates

app = typer.Typer(help="ElevenLabs Conversational AI Agent Manager CLI")

# Default file names
AGENTS_CONFIG_FILE = "agents.json"
LOCK_FILE = "convai.lock"


@app.command()
def init(
    path: str = typer.Argument(".", help="Path to initialize the project in")
):
    """Initialize a new agent management project."""
    project_path = Path(path).resolve()
    
    # Create agents directory
    agents_dir = project_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    
    # Create agents.json if it doesn't exist
    agents_config_path = project_path / AGENTS_CONFIG_FILE
    if not agents_config_path.exists():
        default_config = {
            "agents": []
        }
        utils.write_agent_config(str(agents_config_path), default_config)
        typer.echo(f"Created {AGENTS_CONFIG_FILE}")
    
    # Create lock file if it doesn't exist
    lock_file_path = project_path / LOCK_FILE
    if not lock_file_path.exists():
        utils.save_lock_file(str(lock_file_path), {utils.LOCK_FILE_AGENTS_KEY: {}})
        typer.echo(f"Created {LOCK_FILE}")
    
    typer.echo(f"✅ Initialized agent management project in {project_path}")


@app.command()
def add(
    name: str = typer.Argument(help="Name of the agent to create"),
    config_path: str = typer.Option(None, help="Custom config path (optional)"),
    template: str = typer.Option("default", help="Template type to use (default, minimal, voice-only, text-only, customer-service, assistant)"),
    skip_upload: bool = typer.Option(False, "--skip-upload", help="Create config file only, don't upload to ElevenLabs")
):
    """Add a new agent - creates config, uploads to ElevenLabs, and saves ID."""
    
    # Check if agents.json exists
    agents_config_path = Path(AGENTS_CONFIG_FILE)
    if not agents_config_path.exists():
        typer.echo("❌ agents.json not found. Run 'convai init' first.", err=True)
        raise typer.Exit(1)
    
    # Load existing config
    agents_config = utils.read_agent_config(str(agents_config_path))
    
    # Check if agent already exists
    for agent in agents_config["agents"]:
        if agent["name"] == name:
            typer.echo(f"❌ Agent '{name}' already exists", err=True)
            raise typer.Exit(1)
    
    # Generate config path if not provided
    if not config_path:
        safe_name = name.lower().replace(" ", "_").replace("[", "").replace("]", "")
        config_path = f"agent_configs/{safe_name}.json"
    
    # Create config directory and file
    config_file_path = Path(config_path)
    config_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create agent config using template
    try:
        agent_config = templates.get_template_by_name(name, template)
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)
    
    utils.write_agent_config(str(config_file_path), agent_config)
    typer.echo(f"📝 Created config file: {config_path} (template: {template})")
    
    if skip_upload:
        # Create new agent entry without ID
        new_agent = {
            "name": name,
            "config": config_path
        }
        
        # Add new agent to config
        agents_config["agents"].append(new_agent)
        
        # Save updated agents.json
        utils.write_agent_config(str(agents_config_path), agents_config)
        
        typer.echo(f"✅ Added agent '{name}' to agents.json (local only)")
        typer.echo(f"💡 Edit {config_path} to customize your agent, then run 'convai sync' to upload")
        return
    
    # Create agent in ElevenLabs
    typer.echo(f"🚀 Creating agent '{name}' in ElevenLabs...")
    
    try:
        client = elevenlabsapi.get_elevenlabs_client()
        
        # Extract config components
        conversation_config = agent_config.get("conversation_config", {})
        platform_settings = agent_config.get("platform_settings")
        tags = agent_config.get("tags", [])
        
        # Create new agent
        agent_id = elevenlabsapi.create_agent_api(
            client=client,
            name=name,
            conversation_config_dict=conversation_config,
            platform_settings_dict=platform_settings,
            tags=tags
        )
        
        typer.echo(f"✅ Created agent in ElevenLabs with ID: {agent_id}")
        
        # Create new agent entry
        new_agent = {
            "name": name,
            "id": agent_id,
            "config": config_path
        }
        
        # Add new agent to config
        agents_config["agents"].append(new_agent)
        
        # Save updated agents.json
        utils.write_agent_config(str(agents_config_path), agents_config)
        
        # Update lock file
        lock_file_path = Path(LOCK_FILE)
        lock_data = utils.load_lock_file(str(lock_file_path))
        config_hash = utils.calculate_config_hash(agent_config)
        utils.update_agent_in_lock(lock_data, name, "default", agent_id, config_hash)
        utils.save_lock_file(str(lock_file_path), lock_data)
        
        typer.echo(f"✅ Added agent '{name}' to agents.json")
        typer.echo(f"💡 Edit {config_path} to customize your agent, then run 'convai sync' to update")
        
    except Exception as e:
        typer.echo(f"❌ Error creating agent in ElevenLabs: {e}")
        # Clean up config file if agent creation failed
        if config_file_path.exists():
            config_file_path.unlink()
        raise typer.Exit(1)


@app.command()
def templates_list():
    """List available agent templates."""
    template_options = templates.get_template_options()
    
    typer.echo("Available Agent Templates:")
    typer.echo("=" * 40)
    
    for template_name, description in template_options.items():
        typer.echo(f"\n🎯 {template_name}")
        typer.echo(f"   {description}")
    
    typer.echo(f"\n💡 Use 'convai add <name> --template <template_name>' to create an agent with a specific template")


@app.command()
def template_show(
    template_name: str = typer.Argument(help="Template name to show"),
    agent_name: str = typer.Option("example_agent", help="Agent name to use in template")
):
    """Show the configuration for a specific template."""
    try:
        template_config = templates.get_template_by_name(agent_name, template_name)
        typer.echo(f"Template: {template_name}")
        typer.echo("=" * 40)
        typer.echo(json.dumps(template_config, indent=2))
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)


@app.command()
def sync(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    environment: str = typer.Option(None, "--env", help="Target specific environment/tag")
):
    """Synchronize agents with ElevenLabs API when configs change."""
    
    # Load agents configuration
    agents_config_path = Path(AGENTS_CONFIG_FILE)
    if not agents_config_path.exists():
        typer.echo("❌ agents.json not found. Run 'init' first.", err=True)
        raise typer.Exit(1)
    
    agents_config = utils.read_agent_config(str(agents_config_path))
    
    # Load lock file
    lock_file_path = Path(LOCK_FILE)
    lock_data = utils.load_lock_file(str(lock_file_path))
    
    # Initialize ElevenLabs client
    if not dry_run:
        try:
            client = elevenlabsapi.get_elevenlabs_client()
        except ValueError as e:
            typer.echo(f"❌ {e}", err=True)
            raise typer.Exit(1)
    
    changes_made = False
    
    for agent_def in agents_config["agents"]:
        agent_name = agent_def["name"]
        config_path = agent_def["config"]
        existing_agent_id = agent_def.get("id")
        
        # Check if config file exists
        if not Path(config_path).exists():
            typer.echo(f"⚠️  Config file not found for {agent_name}: {config_path}")
            continue
        
        # Load agent config
        try:
            agent_config = utils.read_agent_config(config_path)
        except Exception as e:
            typer.echo(f"❌ Error reading config for {agent_name}: {e}")
            continue
        
        # Calculate config hash
        config_hash = utils.calculate_config_hash(agent_config)
        
        # Determine environment tag
        tag = environment or "default"
        
        # Check if agent needs updating
        locked_agent = utils.get_agent_from_lock(lock_data, agent_name, tag)
        
        needs_update = True
        
        if locked_agent:
            if locked_agent.get("hash") == config_hash:
                needs_update = False
                typer.echo(f"✅ {agent_name}: No changes")
            else:
                typer.echo(f"🔄 {agent_name}: Config changed, will update")
        else:
            typer.echo(f"🆕 {agent_name}: New config detected, will update")
        
        if not needs_update:
            continue
        
        if dry_run:
            typer.echo(f"[DRY RUN] Would update agent: {agent_name}")
            continue
        
        # Perform API operation
        try:
            agent_id = existing_agent_id
            
            if not agent_id:
                typer.echo(f"❌ No agent ID found for {agent_name}. Use 'convai add' to create new agents.")
                continue
            
            # Extract config components
            conversation_config = agent_config.get("conversation_config", {})
            platform_settings = agent_config.get("platform_settings")
            tags = agent_config.get("tags", [])
            
            # Add environment tag if specified
            if environment and environment not in tags:
                tags = tags + [environment]
            
            # Use name from config or default to agent definition name
            agent_display_name = agent_config.get("name", agent_name)
            
            # Update existing agent
            elevenlabsapi.update_agent_api(
                client=client,
                agent_id=agent_id,
                name=agent_display_name,
                conversation_config_dict=conversation_config,
                platform_settings_dict=platform_settings,
                tags=tags
            )
            typer.echo(f"✅ Updated agent {agent_name} (ID: {agent_id})")
            
            # Update lock file
            utils.update_agent_in_lock(lock_data, agent_name, tag, agent_id, config_hash)
            changes_made = True
            
        except Exception as e:
            typer.echo(f"❌ Error processing {agent_name}: {e}")
    
    # Save lock file if changes were made
    if changes_made and not dry_run:
        utils.save_lock_file(str(lock_file_path), lock_data)
        typer.echo("💾 Updated lock file")


@app.command()
def status():
    """Show the status of all agents."""
    
    # Load agents configuration
    agents_config_path = Path(AGENTS_CONFIG_FILE)
    if not agents_config_path.exists():
        typer.echo("❌ agents.json not found. Run 'init' first.", err=True)
        raise typer.Exit(1)
    
    agents_config = utils.read_agent_config(str(agents_config_path))
    lock_data = utils.load_lock_file(str(Path(LOCK_FILE)))
    
    if not agents_config["agents"]:
        typer.echo("No agents configured")
        return
    
    typer.echo("Agent Status:")
    typer.echo("=" * 50)
    
    for agent_def in agents_config["agents"]:
        agent_name = agent_def["name"]
        config_path = agent_def["config"]
        agent_id = agent_def.get("id", "Not set")
        
        typer.echo(f"\n📋 {agent_name}")
        typer.echo(f"   ID: {agent_id}")
        typer.echo(f"   Config: {config_path}")
        
        # Check config file status
        if Path(config_path).exists():
            try:
                agent_config = utils.read_agent_config(config_path)
                config_hash = utils.calculate_config_hash(agent_config)
                typer.echo(f"   Config Hash: {config_hash[:8]}...")
                
                # Check lock status for default environment
                locked_agent = utils.get_agent_from_lock(lock_data, agent_name, "default")
                if locked_agent:
                    if locked_agent.get("hash") == config_hash:
                        typer.echo("   Status: ✅ Synced")
                    else:
                        typer.echo("   Status: 🔄 Config changed (needs sync)")
                else:
                    typer.echo("   Status: 🆕 New (needs sync)")
                    
            except Exception as e:
                typer.echo(f"   Status: ❌ Config error: {e}")
        else:
            typer.echo(f"   Status: ❌ Config file not found")


@app.command()
def watch(
    environment: str = typer.Option("default", "--env", help="Environment to watch"),
    interval: int = typer.Option(5, "--interval", help="Check interval in seconds")
):
    """Watch for config changes and auto-sync agents."""
    import time
    
    typer.echo(f"👀 Watching for config changes (checking every {interval}s)...")
    typer.echo("Press Ctrl+C to stop")
    
    # Track file modification times
    file_timestamps = {}
    
    def get_file_mtime(file_path: Path) -> float:
        """Get file modification time, return 0 if file doesn't exist."""
        try:
            return file_path.stat().st_mtime if file_path.exists() else 0
        except OSError:
            return 0
    
    def check_for_changes() -> bool:
        """Check if any config files have changed."""
        # Load agents configuration
        agents_config_path = Path(AGENTS_CONFIG_FILE)
        if not agents_config_path.exists():
            return False
        
        try:
            agents_config = utils.read_agent_config(str(agents_config_path))
        except Exception:
            return False
        
        # Check agents.json itself
        agents_mtime = get_file_mtime(agents_config_path)
        if file_timestamps.get(str(agents_config_path), 0) != agents_mtime:
            file_timestamps[str(agents_config_path)] = agents_mtime
            typer.echo(f"📝 Detected change in {AGENTS_CONFIG_FILE}")
            return True
        
        # Check individual agent config files
        for agent_def in agents_config["agents"]:
            config_path = Path(agent_def["config"])
            if config_path.exists():
                config_mtime = get_file_mtime(config_path)
                if file_timestamps.get(str(config_path), 0) != config_mtime:
                    file_timestamps[str(config_path)] = config_mtime
                    typer.echo(f"📝 Detected change in {config_path}")
                    return True
        
        return False
    
    # Initialize file timestamps
    check_for_changes()
    
    try:
        while True:
            if check_for_changes():
                typer.echo("🔄 Running sync...")
                
                # Import the sync command context to avoid circular imports
                from typer.testing import CliRunner
                runner = CliRunner()
                
                # Call sync programmatically
                try:
                    # Load agents configuration
                    agents_config_path = Path(AGENTS_CONFIG_FILE)
                    if not agents_config_path.exists():
                        typer.echo("❌ agents.json not found")
                        time.sleep(interval)
                        continue
                    
                    agents_config = utils.read_agent_config(str(agents_config_path))
                    lock_file_path = Path(LOCK_FILE)
                    lock_data = utils.load_lock_file(str(lock_file_path))
                    
                    # Initialize ElevenLabs client
                    client = elevenlabsapi.get_elevenlabs_client()
                    changes_made = False
                    
                    for agent_def in agents_config["agents"]:
                        agent_name = agent_def["name"]
                        config_path = agent_def["config"]
                        existing_agent_id = agent_def.get("id")
                        
                        # Check if config file exists
                        if not Path(config_path).exists():
                            continue
                        
                        # Load agent config
                        try:
                            agent_config = utils.read_agent_config(config_path)
                        except Exception:
                            continue
                        
                        # Calculate config hash
                        config_hash = utils.calculate_config_hash(agent_config)
                        
                        # Check if agent needs updating
                        locked_agent = utils.get_agent_from_lock(lock_data, agent_name, environment)
                        
                        needs_update = True
                        if locked_agent and locked_agent.get("hash") == config_hash:
                            needs_update = False
                        
                        if not needs_update:
                            continue
                        
                        # Perform API operation
                        try:
                            agent_id = existing_agent_id or (locked_agent.get("id") if locked_agent else None)
                            
                            # Extract config components
                            conversation_config = agent_config.get("conversation_config", {})
                            platform_settings = agent_config.get("platform_settings")
                            tags = agent_config.get("tags", [])
                            
                            # Add environment tag if specified
                            if environment != "default" and environment not in tags:
                                tags = tags + [environment]
                            
                            # Use name from config or default to agent definition name
                            agent_display_name = agent_config.get("name", agent_name)
                            
                            if not agent_id:
                                # Create new agent
                                agent_id = elevenlabsapi.create_agent_api(
                                    client=client,
                                    name=agent_display_name,
                                    conversation_config_dict=conversation_config,
                                    platform_settings_dict=platform_settings,
                                    tags=tags
                                )
                                typer.echo(f"✅ Created agent {agent_name} with ID: {agent_id}")
                                
                                # Update agents.json with the new ID
                                if not existing_agent_id:
                                    agent_def["id"] = agent_id
                                    utils.write_agent_config(str(agents_config_path), agents_config)
                                
                            else:
                                # Update existing agent
                                elevenlabsapi.update_agent_api(
                                    client=client,
                                    agent_id=agent_id,
                                    name=agent_display_name,
                                    conversation_config_dict=conversation_config,
                                    platform_settings_dict=platform_settings,
                                    tags=tags
                                )
                                typer.echo(f"✅ Updated agent {agent_name} (ID: {agent_id})")
                            
                            # Update lock file
                            utils.update_agent_in_lock(lock_data, agent_name, environment, agent_id, config_hash)
                            changes_made = True
                            
                        except Exception as e:
                            typer.echo(f"❌ Error processing {agent_name}: {e}")
                    
                    # Save lock file if changes were made
                    if changes_made:
                        utils.save_lock_file(str(lock_file_path), lock_data)
                        typer.echo("💾 Updated lock file")
                    
                except Exception as e:
                    typer.echo(f"❌ Error during sync: {e}")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        typer.echo("\n👋 Stopping watch mode")


@app.command()
def list_agents():
    """List all configured agents."""
    
    # Load agents configuration
    agents_config_path = Path(AGENTS_CONFIG_FILE)
    if not agents_config_path.exists():
        typer.echo("❌ agents.json not found. Run 'init' first.", err=True)
        raise typer.Exit(1)
    
    agents_config = utils.read_agent_config(str(agents_config_path))
    
    if not agents_config["agents"]:
        typer.echo("No agents configured")
        return
    
    typer.echo("Configured Agents:")
    typer.echo("=" * 30)
    
    for i, agent_def in enumerate(agents_config["agents"], 1):
        typer.echo(f"{i}. {agent_def['name']}")
        typer.echo(f"   Config: {agent_def['config']}")
        if "id" in agent_def:
            typer.echo(f"   ID: {agent_def['id']}")
        typer.echo()


@app.command()
def fetch(
    output_dir: str = typer.Option("agent_configs", "--output-dir", help="Directory to store fetched agent configs"),
    search: str = typer.Option(None, "--search", help="Search agents by name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be fetched without making changes")
):
    """Fetch all agents from ElevenLabs workspace and add them to local configuration."""
    
    # Check if agents.json exists
    agents_config_path = Path(AGENTS_CONFIG_FILE)
    if not agents_config_path.exists():
        typer.echo("❌ agents.json not found. Run 'convai init' first.", err=True)
        raise typer.Exit(1)
    
    try:
        # Initialize ElevenLabs client
        client = elevenlabsapi.get_elevenlabs_client()
        
        # Fetch all agents from ElevenLabs
        typer.echo("🔍 Fetching agents from ElevenLabs...")
        agents_list = elevenlabsapi.list_agents_api(client, search=search)
        
        if not agents_list:
            typer.echo("No agents found in your ElevenLabs workspace.")
            return
        
        typer.echo(f"Found {len(agents_list)} agent(s)")
        
        # Load existing config
        agents_config = utils.read_agent_config(str(agents_config_path))
        existing_agent_names = {agent["name"] for agent in agents_config["agents"]}
        existing_agent_ids = {agent.get("id") for agent in agents_config["agents"]}
        
        # Load lock file
        lock_file_path = Path(LOCK_FILE)
        lock_data = utils.load_lock_file(str(lock_file_path))
        
        new_agents_added = 0
        updated_agents = 0
        
        for agent_meta in agents_list:
            agent_id = agent_meta["agent_id"]
            agent_name = agent_meta["name"]
            
            # Skip if agent already exists by ID
            if agent_id in existing_agent_ids:
                typer.echo(f"⏭️  Skipping '{agent_name}' - already exists (ID: {agent_id})")
                continue
            
            # Check for name conflicts
            if agent_name in existing_agent_names:
                # Generate a unique name
                counter = 1
                original_name = agent_name
                while agent_name in existing_agent_names:
                    agent_name = f"{original_name}_{counter}"
                    counter += 1
                typer.echo(f"⚠️  Name conflict: renamed '{original_name}' to '{agent_name}'")
            
            if dry_run:
                typer.echo(f"[DRY RUN] Would fetch agent: {agent_name} (ID: {agent_id})")
                continue
            
            try:
                # Fetch detailed agent configuration
                typer.echo(f"📥 Fetching config for '{agent_name}'...")
                agent_details = elevenlabsapi.get_agent_api(client, agent_id)
                
                # Extract configuration components
                conversation_config = agent_details.get("conversation_config", {})
                platform_settings = agent_details.get("platform_settings", {})
                tags = agent_details.get("tags", [])
                
                # Create agent config structure
                agent_config = {
                    "name": agent_name,
                    "conversation_config": conversation_config,
                    "platform_settings": platform_settings,
                    "tags": tags
                }
                
                # Generate config file path
                safe_name = agent_name.lower().replace(" ", "_").replace("[", "").replace("]", "")
                config_path = f"{output_dir}/{safe_name}.json"
                
                # Create config file
                config_file_path = Path(config_path)
                config_file_path.parent.mkdir(parents=True, exist_ok=True)
                utils.write_agent_config(str(config_file_path), agent_config)
                
                # Create new agent entry for agents.json
                new_agent = {
                    "name": agent_name,
                    "id": agent_id,
                    "config": config_path
                }
                
                # Add to agents config
                agents_config["agents"].append(new_agent)
                existing_agent_names.add(agent_name)
                existing_agent_ids.add(agent_id)
                
                # Update lock file
                config_hash = utils.calculate_config_hash(agent_config)
                utils.update_agent_in_lock(lock_data, agent_name, "default", agent_id, config_hash)
                
                typer.echo(f"✅ Added '{agent_name}' (config: {config_path})")
                new_agents_added += 1
                
            except Exception as e:
                typer.echo(f"❌ Error fetching agent '{agent_name}': {e}")
                continue
        
        if not dry_run and new_agents_added > 0:
            # Save updated agents.json
            utils.write_agent_config(str(agents_config_path), agents_config)
            
            # Save updated lock file
            utils.save_lock_file(str(lock_file_path), lock_data)
            
            typer.echo(f"💾 Updated {AGENTS_CONFIG_FILE} and {LOCK_FILE}")
        
        if dry_run:
            typer.echo(f"[DRY RUN] Would add {len([a for a in agents_list if a['agent_id'] not in existing_agent_ids])} new agent(s)")
        else:
            typer.echo(f"✅ Successfully added {new_agents_added} new agent(s)")
            if new_agents_added > 0:
                typer.echo(f"💡 You can now edit the config files in '{output_dir}/' and run 'convai sync' to update")
        
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error fetching agents: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def validate(
    config_path: str = typer.Argument(help="Path to the agent config file to validate")
):
    """Validate an agent configuration file."""
    config_file_path = Path(config_path)
    
    if not config_file_path.exists():
        typer.echo(f"❌ Config file not found: {config_path}", err=True)
        raise typer.Exit(1)
    
    try:
        agent_config = utils.read_agent_config(str(config_file_path))
        typer.echo(f"✅ Config file is valid JSON: {config_path}")
        
        # Basic validation checks
        required_fields = ["name", "conversation_config"]
        missing_fields = []
        
        for field in required_fields:
            if field not in agent_config:
                missing_fields.append(field)
        
        if missing_fields:
            typer.echo(f"⚠️  Missing required fields: {', '.join(missing_fields)}")
        else:
            typer.echo("✅ All required fields present")
        
        # Check conversation_config structure
        conv_config = agent_config.get("conversation_config", {})
        if "agent" in conv_config and "prompt" in conv_config["agent"]:
            prompt_config = conv_config["agent"]["prompt"]
            if "prompt" in prompt_config and prompt_config["prompt"]:
                typer.echo("✅ Agent prompt is configured")
            else:
                typer.echo("⚠️  Agent prompt is empty or missing")
        
        # Check for common issues
        if "platform_settings" in agent_config:
            platform = agent_config["platform_settings"]
            if platform.get("call_limits", {}).get("daily_limit", 0) <= 0:
                typer.echo("⚠️  Daily call limit is 0 or negative")
        
        typer.echo(f"📊 Config file size: {len(json.dumps(agent_config))} characters")
        
    except json.JSONDecodeError as e:
        typer.echo(f"❌ Invalid JSON in config file: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error validating config: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
