import json
from pathlib import Path
from dotenv import load_dotenv

import typer

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
    agents_dir = project_path / "agent_configs"
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
    skip_upload: bool = typer.Option(False, "--skip-upload", help="Create config file only, don't upload to ElevenLabs"),
    environment: str = typer.Option("prod", "--env", help="Environment to create agent for")
):
    """Add a new agent - creates config, uploads to ElevenLabs, and saves ID."""
    
    # Check if agents.json exists
    agents_config_path = Path(AGENTS_CONFIG_FILE)
    if not agents_config_path.exists():
        typer.echo("❌ agents.json not found. Run 'convai init' first.", err=True)
        raise typer.Exit(1)
    
    # Load existing config
    agents_config = utils.read_agent_config(str(agents_config_path))
    
    # Load lock file to check environment-specific agents
    lock_file_path = Path(LOCK_FILE)
    lock_data = utils.load_lock_file(str(lock_file_path))
    
    # Check if agent already exists for this specific environment
    locked_agent = utils.get_agent_from_lock(lock_data, name, environment)
    if locked_agent and locked_agent.get("id"):
        typer.echo(f"❌ Agent '{name}' already exists for environment '{environment}'", err=True)
        raise typer.Exit(1)
    
    # Check if agent name exists in agents.json
    existing_agent = None
    for agent in agents_config["agents"]:
        if agent["name"] == name:
            existing_agent = agent
            break
    
    # Generate environment-specific config path if not provided
    if not config_path:
        safe_name = name.lower().replace(" ", "_").replace("[", "").replace("]", "")
        config_path = f"agent_configs/{environment}/{safe_name}.json"
    
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
    
    if existing_agent:
        typer.echo(f"📋 Agent '{name}' exists, adding new environment '{environment}'")
    else:
        typer.echo(f"🆕 Creating new agent '{name}' for environment '{environment}'")
    
    if skip_upload:
        if not existing_agent:
            # Create new agent entry - we'll store config path per environment in a different structure
            new_agent = {
                "name": name,
                "environments": {
                    environment: {
                        "config": config_path
                    }
                }
            }
            
            # Add new agent to config
            agents_config["agents"].append(new_agent)
            typer.echo(f"✅ Added agent '{name}' to agents.json (local only)")
        else:
            # Add environment to existing agent
            if "environments" not in existing_agent:
                # Migrate old format to new format
                old_config = existing_agent.get("config", "")
                existing_agent["environments"] = {"default": {"config": old_config}}
                if "config" in existing_agent:
                    del existing_agent["config"]
            
            existing_agent["environments"][environment] = {"config": config_path}
            typer.echo(f"✅ Added environment '{environment}' to existing agent '{name}' (local only)")
        
        # Save updated agents.json
        utils.write_agent_config(str(agents_config_path), agents_config)
        
        typer.echo(f"💡 Edit {config_path} to customize your agent, then run 'convai sync --env {environment}' to upload")
        return
    
    # Create agent in ElevenLabs
    typer.echo(f"🚀 Creating agent '{name}' in ElevenLabs (environment: {environment})...")
    
    try:
        client = elevenlabsapi.get_elevenlabs_client()
        
        # Extract config components
        conversation_config = agent_config.get("conversation_config", {})
        platform_settings = agent_config.get("platform_settings")
        tags = agent_config.get("tags", [])
        
        # Add environment tag if specified and not already present
        if environment and environment not in tags:
            tags = tags + [environment]
        
        # Create new agent
        agent_id = elevenlabsapi.create_agent_api(
            client=client,
            name=name,
            conversation_config_dict=conversation_config,
            platform_settings_dict=platform_settings,
            tags=tags
        )
        
        typer.echo(f"✅ Created agent in ElevenLabs with ID: {agent_id}")
        
        if not existing_agent:
            # Create new agent entry with environment-specific config paths
            new_agent = {
                "name": name,
                "environments": {
                    environment: {
                        "config": config_path
                    }
                }
            }
            
            # Add new agent to config
            agents_config["agents"].append(new_agent)
            typer.echo(f"✅ Added agent '{name}' to agents.json")
        else:
            # Add environment to existing agent
            if "environments" not in existing_agent:
                # Migrate old format to new format
                old_config = existing_agent.get("config", "")
                existing_agent["environments"] = {"default": {"config": old_config}}
                if "config" in existing_agent:
                    del existing_agent["config"]
            
            existing_agent["environments"][environment] = {"config": config_path}
            typer.echo(f"✅ Added environment '{environment}' to existing agent '{name}'")
        
        # Save updated agents.json
        utils.write_agent_config(str(agents_config_path), agents_config)
        
        # Update lock file with environment-specific agent ID
        config_hash = utils.calculate_config_hash(agent_config)
        utils.update_agent_in_lock(lock_data, name, environment, agent_id, config_hash)
        utils.save_lock_file(str(lock_file_path), lock_data)
        
        typer.echo(f"💡 Edit {config_path} to customize your agent, then run 'convai sync --env {environment}' to update")
        
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
    agent_name: str = typer.Option(None, "--agent", help="Specific agent name to sync (defaults to all agents)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    environment: str = typer.Option(None, "--env", help="Target specific environment (defaults to all environments)")
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
    
    # Filter agents if specific agent name provided
    agents_to_process = agents_config["agents"]
    if agent_name:
        agents_to_process = [agent for agent in agents_config["agents"] if agent["name"] == agent_name]
        if not agents_to_process:
            typer.echo(f"❌ Agent '{agent_name}' not found in configuration", err=True)
            raise typer.Exit(1)
    
    # Determine environments to sync
    environments_to_sync = []
    if environment:
        environments_to_sync = [environment]
    else:
        # Collect all unique environments from all agents
        env_set = set()
        for agent_def in agents_to_process:
            if "environments" in agent_def:
                env_set.update(agent_def["environments"].keys())
            else:
                # Old format compatibility - assume "prod" as default
                env_set.add("prod")
        environments_to_sync = list(env_set)
        
        if not environments_to_sync:
            typer.echo("No environments found to sync")
            return
        
        typer.echo(f"🔄 Syncing all environments: {', '.join(environments_to_sync)}")
    
    changes_made = False
    
    for current_env in environments_to_sync:
        typer.echo(f"\n📍 Processing environment: {current_env}")
        
        for agent_def in agents_to_process:
            agent_name = agent_def["name"]
            
            # Handle both old and new config structure
            config_path = None
            if "environments" in agent_def:
                # New structure - get config for specific environment
                if current_env in agent_def["environments"]:
                    config_path = agent_def["environments"][current_env]["config"]
                else:
                    typer.echo(f"⚠️  Agent '{agent_name}' not configured for environment '{current_env}'")
                    continue
            else:
                # Old structure - backward compatibility
                config_path = agent_def.get("config")
                if not config_path:
                    typer.echo(f"⚠️  No config path found for agent '{agent_name}'")
                    continue
            
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
            
            # Get environment-specific agent data from lock file
            locked_agent = utils.get_agent_from_lock(lock_data, agent_name, current_env)
            
            needs_update = True
            
            if locked_agent:
                if locked_agent.get("hash") == config_hash:
                    needs_update = False
                    typer.echo(f"✅ {agent_name}: No changes (environment: {current_env})")
                else:
                    typer.echo(f"🔄 {agent_name}: Config changed, will update (environment: {current_env})")
            else:
                typer.echo(f"🆕 {agent_name}: New environment detected, will create/update (environment: {current_env})")
            
            if not needs_update:
                continue
            
            if dry_run:
                typer.echo(f"[DRY RUN] Would update agent: {agent_name} (environment: {current_env})")
                continue
            
            # Perform API operation
            try:
                # Get environment-specific agent ID from lock file
                agent_id = locked_agent.get("id") if locked_agent else None
                
                # Extract config components
                conversation_config = agent_config.get("conversation_config", {})
                platform_settings = agent_config.get("platform_settings")
                tags = agent_config.get("tags", [])
                
                # Add environment tag if specified and not already present
                if current_env and current_env not in tags:
                    tags = tags + [current_env]
                
                # Use name from config or default to agent definition name
                agent_display_name = agent_config.get("name", agent_name)
                
                if not agent_id:
                    # Create new agent for this environment
                    agent_id = elevenlabsapi.create_agent_api(
                        client=client,
                        name=agent_display_name,
                        conversation_config_dict=conversation_config,
                        platform_settings_dict=platform_settings,
                        tags=tags
                    )
                    typer.echo(f"✅ Created agent {agent_name} for environment '{current_env}' (ID: {agent_id})")
                else:
                    # Update existing environment-specific agent
                    elevenlabsapi.update_agent_api(
                        client=client,
                        agent_id=agent_id,
                        name=agent_display_name,
                        conversation_config_dict=conversation_config,
                        platform_settings_dict=platform_settings,
                        tags=tags
                    )
                    typer.echo(f"✅ Updated agent {agent_name} for environment '{current_env}' (ID: {agent_id})")
                
                # Update lock file with environment-specific data
                utils.update_agent_in_lock(lock_data, agent_name, current_env, agent_id, config_hash)
                changes_made = True
                
            except Exception as e:
                typer.echo(f"❌ Error processing {agent_name}: {e}")
    
    # Save lock file if changes were made
    if changes_made and not dry_run:
        utils.save_lock_file(str(lock_file_path), lock_data)
        typer.echo("💾 Updated lock file")


@app.command()
def status(
    agent_name: str = typer.Option(None, "--agent", help="Specific agent name to check (defaults to all agents)"),
    environment: str = typer.Option(None, "--env", help="Environment to check status for (defaults to all environments)")
):
    """Show the status of agents."""
    
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
    
    # Filter agents if specific agent name provided
    agents_to_show = agents_config["agents"]
    if agent_name:
        agents_to_show = [agent for agent in agents_config["agents"] if agent["name"] == agent_name]
        if not agents_to_show:
            typer.echo(f"❌ Agent '{agent_name}' not found in configuration", err=True)
            raise typer.Exit(1)
    
    # Determine environments to show
    environments_to_show = []
    if environment:
        environments_to_show = [environment]
        typer.echo(f"Agent Status (Environment: {environment}):")
    else:
        # Collect all unique environments from all agents
        env_set = set()
        for agent_def in agents_to_show:
            if "environments" in agent_def:
                env_set.update(agent_def["environments"].keys())
            else:
                # Old format compatibility - assume "prod" as default
                env_set.add("prod")
        environments_to_show = list(env_set)
        typer.echo("Agent Status (All Environments):")
    
    typer.echo("=" * 50)
    
    for agent_def in agents_to_show:
        agent_name_current = agent_def["name"]
        
        for current_env in environments_to_show:
            # Handle both old and new config structure
            config_path = None
            if "environments" in agent_def:
                if current_env in agent_def["environments"]:
                    config_path = agent_def["environments"][current_env]["config"]
                else:
                    continue  # Skip if agent not configured for this environment
            else:
                # Old structure - backward compatibility
                config_path = agent_def.get("config")
                if not config_path:
                    continue
            
            # Get environment-specific agent ID from lock file
            locked_agent = utils.get_agent_from_lock(lock_data, agent_name_current, current_env)
            agent_id = locked_agent.get("id") if locked_agent else "Not created for this environment"
            
            typer.echo(f"\n📋 {agent_name_current}")
            typer.echo(f"   Environment: {current_env}")
            typer.echo(f"   Agent ID: {agent_id}")
            typer.echo(f"   Config: {config_path}")
            
            # Check config file status
            if Path(config_path).exists():
                try:
                    agent_config = utils.read_agent_config(config_path)
                    config_hash = utils.calculate_config_hash(agent_config)
                    typer.echo(f"   Config Hash: {config_hash[:8]}...")
                    
                    # Check lock status for specified environment
                    if locked_agent:
                        if locked_agent.get("hash") == config_hash:
                            typer.echo(f"   Status: ✅ Synced ({current_env})")
                        else:
                            typer.echo(f"   Status: 🔄 Config changed (needs sync for {current_env})")
                    else:
                        typer.echo(f"   Status: 🆕 New (needs sync for {current_env})")
                        
                except Exception as e:
                    typer.echo(f"   Status: ❌ Config error: {e}")
            else:
                typer.echo(f"   Status: ❌ Config file not found")


@app.command()
def watch(
    agent_name: str = typer.Option(None, "--agent", help="Specific agent name to watch (defaults to all agents)"),
    environment: str = typer.Option("prod", "--env", help="Environment to watch"),
    interval: int = typer.Option(5, "--interval", help="Check interval in seconds")
):
    """Watch for config changes and auto-sync agents."""
    import time
    
    typer.echo(f"👀 Watching for config changes (checking every {interval}s)...")
    if agent_name:
        typer.echo(f"Agent: {agent_name}")
    else:
        typer.echo("Agent: All agents")
    typer.echo(f"Environment: {environment}")
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
        
        # Filter agents if specific agent name provided
        agents_to_watch = agents_config["agents"]
        if agent_name:
            agents_to_watch = [agent for agent in agents_config["agents"] if agent["name"] == agent_name]
        
        # Check agents.json itself
        agents_mtime = get_file_mtime(agents_config_path)
        if file_timestamps.get(str(agents_config_path), 0) != agents_mtime:
            file_timestamps[str(agents_config_path)] = agents_mtime
            typer.echo(f"📝 Detected change in {AGENTS_CONFIG_FILE}")
            return True
        
        # Check individual agent config files
        for agent_def in agents_to_watch:
            # Handle both old and new config structure
            config_paths = []
            if "environments" in agent_def:
                if environment in agent_def["environments"]:
                    config_paths.append(agent_def["environments"][environment]["config"])
            else:
                # Old structure - backward compatibility
                if "config" in agent_def:
                    config_paths.append(agent_def["config"])
            
            for config_path in config_paths:
                config_path_obj = Path(config_path)
                if config_path_obj.exists():
                    config_mtime = get_file_mtime(config_path_obj)
                    if file_timestamps.get(str(config_path_obj), 0) != config_mtime:
                        file_timestamps[str(config_path_obj)] = config_mtime
                        typer.echo(f"📝 Detected change in {config_path}")
                        return True
        
        return False
    
    # Initialize file timestamps
    check_for_changes()
    
    try:
        while True:
            if check_for_changes():
                typer.echo("🔄 Running sync...")
                
                # Call sync programmatically with the same parameters
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
                    
                    # Filter agents if specific agent name provided
                    agents_to_process = agents_config["agents"]
                    if agent_name:
                        agents_to_process = [agent for agent in agents_config["agents"] if agent["name"] == agent_name]
                    
                    # Initialize ElevenLabs client
                    client = elevenlabsapi.get_elevenlabs_client()
                    changes_made = False
                    
                    for agent_def in agents_to_process:
                        current_agent_name = agent_def["name"]
                        
                        # Handle both old and new config structure
                        config_path = None
                        if "environments" in agent_def:
                            if environment in agent_def["environments"]:
                                config_path = agent_def["environments"][environment]["config"]
                            else:
                                continue
                        else:
                            # Old structure - backward compatibility
                            config_path = agent_def.get("config")
                            if not config_path:
                                continue
                        
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
                        
                        # Get environment-specific agent data from lock file
                        locked_agent = utils.get_agent_from_lock(lock_data, current_agent_name, environment)
                        
                        needs_update = True
                        if locked_agent and locked_agent.get("hash") == config_hash:
                            needs_update = False
                        
                        if not needs_update:
                            continue
                        
                        # Perform API operation
                        try:
                            # Get environment-specific agent ID from lock file
                            agent_id = locked_agent.get("id") if locked_agent else None
                            
                            # Extract config components
                            conversation_config = agent_config.get("conversation_config", {})
                            platform_settings = agent_config.get("platform_settings")
                            tags = agent_config.get("tags", [])
                            
                            # Add environment tag if specified and not already present
                            if environment and environment not in tags:
                                tags = tags + [environment]
                            
                            # Use name from config or default to agent definition name
                            agent_display_name = agent_config.get("name", current_agent_name)
                            
                            if not agent_id:
                                # Create new agent for this environment
                                agent_id = elevenlabsapi.create_agent_api(
                                    client=client,
                                    name=agent_display_name,
                                    conversation_config_dict=conversation_config,
                                    platform_settings_dict=platform_settings,
                                    tags=tags
                                )
                                typer.echo(f"✅ Created agent {current_agent_name} for environment '{environment}' (ID: {agent_id})")
                            else:
                                # Update existing environment-specific agent
                                elevenlabsapi.update_agent_api(
                                    client=client,
                                    agent_id=agent_id,
                                    name=agent_display_name,
                                    conversation_config_dict=conversation_config,
                                    platform_settings_dict=platform_settings,
                                    tags=tags
                                )
                                typer.echo(f"✅ Updated agent {current_agent_name} for environment '{environment}' (ID: {agent_id})")
                            
                            # Update lock file with environment-specific data
                            utils.update_agent_in_lock(lock_data, current_agent_name, environment, agent_id, config_hash)
                            changes_made = True
                            
                        except Exception as e:
                            typer.echo(f"❌ Error processing {current_agent_name}: {e}")
                    
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
        
        # Handle both old and new config structure
        if "environments" in agent_def:
            # New structure - show all environments
            typer.echo("   Environments:")
            for env_name, env_config in agent_def["environments"].items():
                typer.echo(f"     {env_name}: {env_config['config']}")
        else:
            # Old structure - backward compatibility
            config_path = agent_def.get("config", "No config path")
            typer.echo(f"   Config: {config_path}")
        
        typer.echo()


@app.command()
def fetch(
    agent_name: str = typer.Option(None, "--agent", help="Specific agent name pattern to search for"),
    output_dir: str = typer.Option("agent_configs", "--output-dir", help="Directory to store fetched agent configs"),
    search: str = typer.Option(None, "--search", help="Search agents by name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be fetched without making changes"),
    environment: str = typer.Option("prod", "--env", help="Environment to associate fetched agents with")
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
        
        # Use agent_name as search term if provided, otherwise use search parameter
        search_term = agent_name or search
        
        # Fetch all agents from ElevenLabs
        typer.echo("🔍 Fetching agents from ElevenLabs...")
        agents_list = elevenlabsapi.list_agents_api(client, search=search_term)
        
        if not agents_list:
            typer.echo("No agents found in your ElevenLabs workspace.")
            return
        
        typer.echo(f"Found {len(agents_list)} agent(s)")
        
        # Load existing config
        agents_config = utils.read_agent_config(str(agents_config_path))
        existing_agent_names = {agent["name"] for agent in agents_config["agents"]}
        
        # Load lock file to check for existing agent IDs per environment
        lock_file_path = Path(LOCK_FILE)
        lock_data = utils.load_lock_file(str(lock_file_path))
        existing_agent_ids = set()
        
        # Collect all existing agent IDs across all environments
        for agent_name_key, environments in lock_data.get(utils.LOCK_FILE_AGENTS_KEY, {}).items():
            for env_name, env_data in environments.items():
                if "id" in env_data:
                    existing_agent_ids.add(env_data["id"])
        
        new_agents_added = 0
        
        for agent_meta in agents_list:
            agent_id = agent_meta["agent_id"]
            agent_name_remote = agent_meta["name"]
            
            # Skip if agent already exists by ID (in any environment)
            if agent_id in existing_agent_ids:
                typer.echo(f"⏭️  Skipping '{agent_name_remote}' - already exists (ID: {agent_id})")
                continue
            
            # Check for name conflicts
            if agent_name_remote in existing_agent_names:
                # Generate a unique name
                counter = 1
                original_name = agent_name_remote
                while agent_name_remote in existing_agent_names:
                    agent_name_remote = f"{original_name}_{counter}"
                    counter += 1
                typer.echo(f"⚠️  Name conflict: renamed '{original_name}' to '{agent_name_remote}'")
            
            if dry_run:
                typer.echo(f"[DRY RUN] Would fetch agent: {agent_name_remote} (ID: {agent_id}) for environment: {environment}")
                continue
            
            try:
                # Fetch detailed agent configuration
                typer.echo(f"📥 Fetching config for '{agent_name_remote}'...")
                agent_details = elevenlabsapi.get_agent_api(client, agent_id)
                
                # Extract configuration components
                conversation_config = agent_details.get("conversation_config", {})
                platform_settings = agent_details.get("platform_settings", {})
                tags = agent_details.get("tags", [])
                
                # Create agent config structure
                agent_config = {
                    "name": agent_name_remote,
                    "conversation_config": conversation_config,
                    "platform_settings": platform_settings,
                    "tags": tags
                }
                
                # Generate config file path
                safe_name = agent_name_remote.lower().replace(" ", "_").replace("[", "").replace("]", "")
                config_path = f"{output_dir}/{safe_name}.json"
                
                # Create config file
                config_file_path = Path(config_path)
                config_file_path.parent.mkdir(parents=True, exist_ok=True)
                utils.write_agent_config(str(config_file_path), agent_config)
                
                # Create new agent entry for agents.json (NO ID field - stored in lock file per environment)
                new_agent = {
                    "name": agent_name_remote,
                    "config": config_path
                }
                
                # Add to agents config
                agents_config["agents"].append(new_agent)
                existing_agent_names.add(agent_name_remote)
                existing_agent_ids.add(agent_id)
                
                # Update lock file with environment-specific agent ID
                config_hash = utils.calculate_config_hash(agent_config)
                utils.update_agent_in_lock(lock_data, agent_name_remote, environment, agent_id, config_hash)
                
                typer.echo(f"✅ Added '{agent_name_remote}' (config: {config_path}) for environment: {environment}")
                new_agents_added += 1
                
            except Exception as e:
                typer.echo(f"❌ Error fetching agent '{agent_name_remote}': {e}")
                continue
        
        if not dry_run and new_agents_added > 0:
            # Save updated agents.json
            utils.write_agent_config(str(agents_config_path), agents_config)
            
            # Save updated lock file
            utils.save_lock_file(str(lock_file_path), lock_data)
            
            typer.echo(f"💾 Updated {AGENTS_CONFIG_FILE} and {LOCK_FILE}")
        
        if dry_run:
            typer.echo(f"[DRY RUN] Would add {len([a for a in agents_list if a['agent_id'] not in existing_agent_ids])} new agent(s) for environment: {environment}")
        else:
            typer.echo(f"✅ Successfully added {new_agents_added} new agent(s) for environment: {environment}")
            if new_agents_added > 0:
                typer.echo(f"💡 You can now edit the config files in '{output_dir}/' and run 'convai sync --env {environment}' to update")
        
    except ValueError as e:
        typer.echo(f"❌ {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error fetching agents: {e}", err=True)
        raise typer.Exit(1)

@app.command()
def widget(
    agent_name: str = typer.Argument(help="Name of the agent to generate widget for"),
    environment: str = typer.Option("prod", "--env", help="Environment to get agent ID from")
):
    """Generate HTML widget snippet for an agent."""
    
    # Load agents configuration
    agents_config_path = Path(AGENTS_CONFIG_FILE)
    if not agents_config_path.exists():
        typer.echo("❌ agents.json not found. Run 'convai init' first.", err=True)
        raise typer.Exit(1)
    
    # Load lock file to get agent ID
    lock_file_path = Path(LOCK_FILE)
    lock_data = utils.load_lock_file(str(lock_file_path))
    
    # Check if agent exists in config
    agents_config = utils.read_agent_config(str(agents_config_path))
    agent_exists = any(agent["name"] == agent_name for agent in agents_config["agents"])
    
    if not agent_exists:
        typer.echo(f"❌ Agent '{agent_name}' not found in configuration", err=True)
        raise typer.Exit(1)
    
    # Get environment-specific agent data from lock file
    locked_agent = utils.get_agent_from_lock(lock_data, agent_name, environment)
    
    if not locked_agent or not locked_agent.get("id"):
        typer.echo(f"❌ Agent '{agent_name}' not found for environment '{environment}' or not yet synced", err=True)
        typer.echo(f"💡 Run 'convai sync --agent {agent_name} --env {environment}' to create the agent first")
        raise typer.Exit(1)
    
    agent_id = locked_agent["id"]
    
    # Generate HTML widget snippet
    html_snippet = f'''<elevenlabs-convai agent-id="{agent_id}"></elevenlabs-convai>
<script src="https://unpkg.com/@elevenlabs/convai-widget-embed" async type="text/javascript"></script>'''
    
    typer.echo(f"🎯 HTML Widget for '{agent_name}' (environment: {environment}):")
    typer.echo("=" * 60)
    typer.echo(html_snippet)
    typer.echo("=" * 60)
    typer.echo(f"Agent ID: {agent_id}")

if __name__ == "__main__":
    app()