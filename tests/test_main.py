import pytest
import json
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock 
from pathlib import Path

# Application and constants
from elevenlabs_cli_tool.main import app, AGENTS_CONFIG_FILE, LOCK_FILE
from elevenlabs_cli_tool.utils import LOCK_FILE_AGENTS_KEY 

runner = CliRunner()

# --- Test for init command ---
def test_init_command(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        result = runner.invoke(app, ["init"])
        
        assert result.exit_code == 0, result.stdout
        assert f"Created {AGENTS_CONFIG_FILE}" in result.stdout
        assert f"Created {LOCK_FILE}" in result.stdout
        
        agents_dir = fs / "agents"
        assert agents_dir.is_dir()
        
        agents_config_path = fs / AGENTS_CONFIG_FILE
        assert agents_config_path.is_file()
        with open(agents_config_path, 'r', encoding='utf-8') as f:
            config_content = json.load(f)
            assert config_content == {"agents": []}
        
        lock_file_path = fs / LOCK_FILE
        assert lock_file_path.is_file()
        with open(lock_file_path, 'r', encoding='utf-8') as f:
            lock_content = json.load(f)
            assert lock_content == {LOCK_FILE_AGENTS_KEY: {}}

        # Run init again to test existing files
        result_rerun = runner.invoke(app, ["init"])
        assert result_rerun.exit_code == 0, result_rerun.stdout


# --- Test for add command (without API calls) ---
def test_add_command_no_init(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        result = runner.invoke(app, ["add", "test_agent"])
        assert result.exit_code == 1, result.stdout
        assert "agents.json not found" in result.stdout


# --- Test for status command ---
def test_status_command_no_init(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1, result.stdout
        assert "agents.json not found" in result.stdout


def test_status_command_empty_agents(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0, result.stdout
        assert "No agents configured" in result.stdout


# --- Test for list-agents command ---
def test_list_agents_command_no_init(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        result = runner.invoke(app, ["list-agents"])
        assert result.exit_code == 1, result.stdout
        assert "agents.json not found" in result.stdout


def test_list_agents_command_empty_agents(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, ["list-agents"])
        assert result.exit_code == 0, result.stdout
        assert "No agents configured" in result.stdout


# --- Test for sync command ---
def test_sync_command_no_init(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 1, result.stdout
        assert "agents.json not found" in result.stdout


def test_sync_command_empty_agents(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"])
        
        # Sync with empty agents should initialize client but do nothing
        with patch('elevenlabs_cli_tool.elevenlabsapi.get_elevenlabs_client') as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            result = runner.invoke(app, ["sync"])
            assert result.exit_code == 0, result.stdout
            # Client is initialized but no API calls should be made since no agents exist
            mock_get_client.assert_called_once()


# --- Mock tests for add command with API ---
@pytest.fixture
def mock_elevenlabs_client():
    with patch('elevenlabs_cli_tool.elevenlabsapi.get_elevenlabs_client') as mock_get_client, \
         patch('elevenlabs_cli_tool.elevenlabsapi.create_agent_api') as mock_create:
        
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_create.return_value = "test_agent_id_123"
        
        yield {
            'get_client': mock_get_client,
            'create_agent': mock_create,
            'client': mock_client
        }


def test_add_command_success(tmp_path, mock_elevenlabs_client):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"])
        
        result = runner.invoke(app, ["add", "test_agent"])
        assert result.exit_code == 0, result.stdout
        assert "Created config file" in result.stdout
        assert "Created agent in ElevenLabs with ID: test_agent_id_123" in result.stdout
        assert "Added agent 'test_agent' to agents.json" in result.stdout
        
        # Check that agent config was created
        config_path = fs / "agent_configs" / "test_agent.json"
        assert config_path.exists()
        
        # Check agents.json was updated
        agents_config_path = fs / AGENTS_CONFIG_FILE
        with open(agents_config_path, 'r') as f:
            config = json.load(f)
            assert len(config["agents"]) == 1
            assert config["agents"][0]["name"] == "test_agent"
            assert config["agents"][0]["id"] == "test_agent_id_123"


def test_add_command_duplicate_agent(tmp_path, mock_elevenlabs_client):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"])
        runner.invoke(app, ["add", "test_agent"])  # Add first time
        
        result = runner.invoke(app, ["add", "test_agent"])  # Try to add again
        assert result.exit_code == 1, result.stdout
        assert "Agent 'test_agent' already exists" in result.stdout


def test_add_command_api_error(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"])
        
        with patch('elevenlabs_cli_tool.elevenlabsapi.get_elevenlabs_client') as mock_get_client:
            mock_get_client.side_effect = Exception("API connection failed")
            
            result = runner.invoke(app, ["add", "test_agent"])
            assert result.exit_code == 1, result.stdout
            assert "Error creating agent in ElevenLabs" in result.stdout