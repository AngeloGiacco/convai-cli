#!/usr/bin/env python3

import os
import sys
import json
import typing
from pathlib import Path

import typer
from elevenlabs import ElevenLabs, ConversationalConfig
from elevenlabs.types import AgentPlatformSettingsRequestModel
from elevenlabs.client import OMIT

from . import utils
from . import elevenlabsapi

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
    config_path: str = typer.Option(None, help="Custom config path (optional)")
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
    
    # Create default agent config
    default_agent_config = {
        "name": name,
        "conversation_config": {
            "model_id": "eleven_turbo_v2",
            "prompt_template": f"You are {name}, a helpful AI assistant.",
            "max_tokens": 200,
            "temperature": 0.7
        },
        "platform_settings": {},
        "tags": []
    }
    
    utils.write_agent_config(str(config_file_path), default_agent_config)
    typer.echo(f"📝 Created config file: {config_path}")
    
    # Create agent in ElevenLabs
    typer.echo(f"🚀 Creating agent '{name}' in ElevenLabs...")
    
    try:
        client = elevenlabsapi.get_elevenlabs_client()
        
        # Extract config components
        conversation_config = default_agent_config.get("conversation_config", {})
        platform_settings = default_agent_config.get("platform_settings")
        tags = default_agent_config.get("tags", [])
        
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
        config_hash = utils.calculate_config_hash(default_agent_config)
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


if __name__ == "__main__":
    app()
