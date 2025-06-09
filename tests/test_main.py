import pytest
import json
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock 
from pathlib import Path

# Application and constants
from elevenlabs_cli_tool.main import app, AGENTS_DIR_NAME, LOCK_FILE_NAME, MINIMAL_AGENT_CONFIG_EXAMPLE
from elevenlabs_cli_tool.utils import LOCK_FILE_AGENTS_KEY 

# SDK models for mocking API responses
from elevenlabs.types import CreateAgentResponseModel, GetAgentResponseModel, ConversationalConfig # Added ConversationalConfig for GetAgentResponseModel

runner = CliRunner()

# --- Test for init command ---
def test_init_command(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str) # Convert string path to Path object
        result = runner.invoke(app, ["init"])
        
        assert result.exit_code == 0, result.stdout
        assert f"Created agents directory: {fs / AGENTS_DIR_NAME}" in result.stdout
        assert f"Created lock file: {fs / LOCK_FILE_NAME}" in result.stdout
        
        assert (fs / AGENTS_DIR_NAME).is_dir()
        lock_file_path = fs / LOCK_FILE_NAME
        assert lock_file_path.is_file()
        with open(lock_file_path, 'r', encoding='utf-8') as f:
            lock_content = json.load(f)
            assert lock_content == {LOCK_FILE_AGENTS_KEY: {}}

        # Run init again
        result_rerun = runner.invoke(app, ["init"])
        assert result_rerun.exit_code == 0, result_rerun.stdout
        assert f"Agents directory already exists: {fs / AGENTS_DIR_NAME}" in result_rerun.stdout
        assert f"Lock file already exists: {fs / LOCK_FILE_NAME}" in result_rerun.stdout

# --- Tests for create-agent command ---
def test_create_agent_command(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"]) # Prerequisite
        
        agent_name = "test_agent_cli"
        result = runner.invoke(app, ["create-agent", agent_name])
        
        assert result.exit_code == 0, result.stdout
        expected_path = fs / AGENTS_DIR_NAME / agent_name
        assert f"Successfully created agent directory: {expected_path}" in result.stdout
        assert expected_path.is_dir()

        # Test error on existing agent
        result_rerun = runner.invoke(app, ["create-agent", agent_name])
        assert result_rerun.exit_code == 1, result_rerun.stdout
        assert f"Error: Agent directory '{expected_path.resolve()}' already exists." in result_rerun.stdout

def test_create_agent_no_init(tmp_path):
     with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        result = runner.invoke(app, ["create-agent", "some_agent_no_init"])
        assert result.exit_code == 1, result.stdout
        # Check for AGENTS_DIR_NAME within the current context (fs)
        assert f"Error: Agents directory '{AGENTS_DIR_NAME}' not found in {fs}" in result.stdout

# --- Tests for add-config command ---
def test_add_config_command(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"])
        agent_name = "my_cli_agent_for_config"
        tag = "development_tag"
        runner.invoke(app, ["create-agent", agent_name])

        result = runner.invoke(app, ["add-config", agent_name, tag])
        assert result.exit_code == 0, result.stdout
        
        config_file_path = fs / AGENTS_DIR_NAME / agent_name / f"{tag}.json"
        assert f"Successfully created configuration file: {config_file_path.resolve()}" in result.stdout
        assert config_file_path.is_file()
        
        with open(config_file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
            assert content["conversation_config"]["model_id"] == MINIMAL_AGENT_CONFIG_EXAMPLE["conversation_config"]["model_id"]
            assert content["name"] == MINIMAL_AGENT_CONFIG_EXAMPLE["name"] # Check another field

def test_add_config_no_agent_dir(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"]) # Init creates agents dir, but not specific agent dir
        agent_name = "non_existent_agent"
        tag = "dev"
        result = runner.invoke(app, ["add-config", agent_name, tag])
        assert result.exit_code == 1, result.stdout
        expected_agent_dir = fs / AGENTS_DIR_NAME / agent_name
        assert f"Error: Agent directory '{expected_agent_dir.resolve()}' not found." in result.stdout

def test_add_config_already_exists(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        runner.invoke(app, ["init"])
        agent_name = "agent_with_config"
        tag = "prod_tag"
        runner.invoke(app, ["create-agent", agent_name])
        runner.invoke(app, ["add-config", agent_name, tag]) # Create it first

        result_rerun = runner.invoke(app, ["add-config", agent_name, tag]) # Try again
        assert result_rerun.exit_code == 1, result_rerun.stdout
        config_file_path = fs / AGENTS_DIR_NAME / agent_name / f"{tag}.json"
        assert f"Error: Configuration file '{config_file_path.resolve()}' already exists." in result_rerun.stdout


# --- Mocks and Fixtures for sync command tests ---
@pytest.fixture
def mock_sync_dependencies(mocker):
    # Mock functions imported at the top level of main.py
    m_load_lock = mocker.patch('elevenlabs_cli_tool.main.load_lock_file')
    m_save_lock = mocker.patch('elevenlabs_cli_tool.main.save_lock_file')
    m_read_conf = mocker.patch('elevenlabs_cli_tool.main.read_agent_config')
    m_calc_hash = mocker.patch('elevenlabs_cli_tool.main.calculate_config_hash')
    # update_agent_in_lock is also from .utils, imported into main's namespace
    m_update_lock_util = mocker.patch('elevenlabs_cli_tool.main.update_agent_in_lock') 

    m_get_client = mocker.patch('elevenlabs_cli_tool.main.get_elevenlabs_client')
    m_create_api = mocker.patch('elevenlabs_cli_tool.main.create_agent_api')
    m_update_api = mocker.patch('elevenlabs_cli_tool.main.update_agent_api')

    mock_client_instance = MagicMock()
    m_get_client.return_value = mock_client_instance
    m_load_lock.return_value = {LOCK_FILE_AGENTS_KEY: {}} 
    m_calc_hash.return_value = "default_new_hash" 
    
    # Mock API call return values (agent_id is expected by sync logic)
    m_create_api.return_value = "created_agent_id_123" # Directly return agent_id string
    # update_agent_api also returns agent_id string
    m_update_api.return_value = "updated_agent_id_456"


    return {
        "load_lock": m_load_lock, "save_lock": m_save_lock,
        "read_config": m_read_conf, "calc_hash": m_calc_hash, 
        "update_lock_util": m_update_lock_util, # For asserting calls to the util function
        "get_client": m_get_client, "create_api": m_create_api, "update_api": m_update_api,
        "client": mock_client_instance
    }

# --- Tests for sync command ---
def test_sync_new_agent_creation(tmp_path, mock_sync_dependencies):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        # Init creates AGENTS_DIR_NAME
        (fs / AGENTS_DIR_NAME).mkdir() 

        agent_name_folder = "sync_new_agent"
        tag_file = "production"
        agent_config_dir = fs / AGENTS_DIR_NAME / agent_name_folder
        agent_config_dir.mkdir(parents=True)
        
        actual_config_data = {"name": "API Agent Name", "conversation_config": {"model_id": "gpt-4"}}
        with open(agent_config_dir / f"{tag_file}.json", 'w', encoding='utf-8') as f:
            json.dump(actual_config_data, f)

        mock_sync_dependencies["read_config"].return_value = actual_config_data
        current_hash = "newly_calculated_hash"
        mock_sync_dependencies["calc_hash"].return_value = current_hash
        # load_lock is already configured to return empty lock data

        result = runner.invoke(app, ["sync"])
        
        assert result.exit_code == 0, result.stdout
        # Check stdout for creation messages
        # The final_api_agent_name logic in sync is folder_tag if name not in json, or json name
        expected_api_name = actual_config_data["name"] # Name is in JSON
        assert f"Creating agent '{expected_api_name}' (Tag: {tag_file})" in result.stdout
        assert f"Successfully created agent '{expected_api_name}'. Agent ID: created_agent_id_123" in result.stdout
        
        mock_sync_dependencies["create_api"].assert_called_once()
        # Verify that update_agent_in_lock (the util function) was called correctly
        mock_sync_dependencies["update_lock_util"].assert_called_with(
            {LOCK_FILE_AGENTS_KEY: {}}, # Initial lock_data passed to it
            agent_name_folder, 
            tag_file, 
            "created_agent_id_123", 
            current_hash
        )
        # And then save_lock_file is called with the modified lock_data
        mock_sync_dependencies["save_lock"].assert_called_once()


def test_sync_agent_up_to_date(tmp_path, mock_sync_dependencies):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        (fs / AGENTS_DIR_NAME).mkdir()
        
        agent_name_folder = "existing_stable_agent"
        tag_file = "dev_env"
        agent_config_dir = fs / AGENTS_DIR_NAME / agent_name_folder
        agent_config_dir.mkdir(parents=True)
        
        actual_config_data = {"conversation_config": {"model_id": "stable_model"}} # Name not in JSON
        with open(agent_config_dir / f"{tag_file}.json", 'w', encoding='utf-8') as f:
            json.dump(actual_config_data, f)

        current_hash = "stable_hash_123"
        mock_sync_dependencies["read_config"].return_value = actual_config_data
        mock_sync_dependencies["calc_hash"].return_value = current_hash
        mock_sync_dependencies["load_lock"].return_value = {
            LOCK_FILE_AGENTS_KEY: {
                agent_name_folder: {tag_file: {"id": "agent_id_xyz", "hash": current_hash}}
            }
        }

        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0, result.stdout
        assert f"Agent '{agent_name_folder}' ({tag_file}) is up to date" in result.stdout
        mock_sync_dependencies["create_api"].assert_not_called()
        mock_sync_dependencies["update_api"].assert_not_called()
        mock_sync_dependencies["update_lock_util"].assert_not_called() # Should not be called if no change

def test_sync_agent_hash_changed_update(tmp_path, mock_sync_dependencies):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        (fs / AGENTS_DIR_NAME).mkdir()

        agent_name_folder = "agent_to_update"
        tag_file = "prod_env"
        agent_config_dir = fs / AGENTS_DIR_NAME / agent_name_folder
        agent_config_dir.mkdir(parents=True)

        actual_config_data = {"name": "Updated API Name", "conversation_config": {"model_id": "new_model_id"}}
        with open(agent_config_dir / f"{tag_file}.json", 'w', encoding='utf-8') as f:
            json.dump(actual_config_data, f)

        old_hash = "old_hash_abc"
        new_hash = "new_hash_def" # mock_calc_hash will return this
        agent_id_from_lock = "original_agent_id_789"

        mock_sync_dependencies["read_config"].return_value = actual_config_data
        mock_sync_dependencies["calc_hash"].return_value = new_hash
        mock_sync_dependencies["load_lock"].return_value = {
            LOCK_FILE_AGENTS_KEY: {
                agent_name_folder: {tag_file: {"id": agent_id_from_lock, "hash": old_hash}}
            }
        }
        # update_api mock returns "updated_agent_id_456"

        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0, result.stdout
        
        expected_api_name = actual_config_data["name"]
        assert f"Updating agent '{expected_api_name}' (Tag: {tag_file}), ID: {agent_id_from_lock}" in result.stdout
        assert f"Successfully updated agent '{expected_api_name}'. Agent ID: updated_agent_id_456" in result.stdout
        
        mock_sync_dependencies["update_api"].assert_called_once()
        call_args_update_api = mock_sync_dependencies["update_api"].call_args
        assert call_args_update_api.kwargs['agent_id'] == agent_id_from_lock
        
        # Check that update_agent_in_lock (the util) was called
        mock_sync_dependencies["update_lock_util"].assert_called_with(
            mock_sync_dependencies["load_lock"].return_value, # Initial lock_data
            agent_name_folder,
            tag_file,
            "updated_agent_id_456", # ID from the update_api response
            new_hash
        )
        mock_sync_dependencies["save_lock"].assert_called_once()

def test_sync_api_key_missing(tmp_path, mock_sync_dependencies):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        # Minimal setup to trigger API client attempt
        (fs / AGENTS_DIR_NAME).mkdir() 
        agent_name_folder = "any_agent"
        agent_config_dir = fs / AGENTS_DIR_NAME / agent_name_folder
        agent_config_dir.mkdir(parents=True)
        with open(agent_config_dir / "any.json", 'w', encoding='utf-8') as f:
            json.dump({"conversation_config": {"model_id":"test"}}, f)
        
        mock_sync_dependencies["get_client"].side_effect = ValueError("ELEVENLABS_API_KEY environment variable not set.")
        
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 1, result.stdout
        assert "Error initializing ElevenLabs client: ELEVENLABS_API_KEY environment variable not set." in result.stdout
        assert "Please ensure ELEVENLABS_API_KEY environment variable is set." in result.stdout

def test_sync_agents_dir_missing(tmp_path, mock_sync_dependencies):
    with runner.isolated_filesystem(temp_dir=tmp_path) as fs_str:
        fs = Path(fs_str)
        # AGENTS_DIR_NAME is NOT created
        
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 1, result.stdout
        expected_agents_dir_path = fs / AGENTS_DIR_NAME
        assert f"Agents directory '{expected_agents_dir_path.resolve()}' not found. Run 'init' first." in result.stdout
        mock_sync_dependencies["get_client"].assert_not_called() # Should exit before client init
