import pytest
import json
import os
from pathlib import Path
# Adjust the import path based on your project structure
# This assumes tests/ is a top-level directory and your package is elevenlabs_cli_tool
from elevenlabs_cli_tool import utils 

# Helper function to create a temporary file with content
def create_temp_file(tmp_path, filename, content):
    file_path = tmp_path / filename
    file_path.write_text(content, encoding='utf-8') # Specify encoding
    return file_path

# --- Tests for calculate_config_hash ---
def test_calculate_config_hash_consistency():
    config1 = {"name": "test", "value": 1, "nested": {"key": "val"}}
    config2 = {"name": "test", "value": 1, "nested": {"key": "val"}}
    assert utils.calculate_config_hash(config1) == utils.calculate_config_hash(config2)

def test_calculate_config_hash_difference():
    config1 = {"name": "test1", "value": 1}
    config2 = {"name": "test2", "value": 2}
    assert utils.calculate_config_hash(config1) != utils.calculate_config_hash(config2)

def test_calculate_config_hash_key_order_insensitivity():
    config1 = {"name": "test", "value": 1, "setting": "abc"}
    config2 = {"setting": "abc", "name": "test", "value": 1} # Different order
    assert utils.calculate_config_hash(config1) == utils.calculate_config_hash(config2)

def test_calculate_config_hash_empty_dict():
    assert utils.calculate_config_hash({}) == utils.calculate_config_hash({})

# --- Tests for read_agent_config and write_agent_config ---
def test_write_and_read_agent_config(tmp_path):
    config_data = {"agent_name": "my_agent", "param": "value", "unicode": "你好"}
    # Construct file path within the main project directory structure if utils.py creates subdirs
    # For tmp_path, it's usually fine, but be mindful if utils.write_agent_config does os.makedirs
    # on a relative path that assumes it's in the project root.
    # For this test, tmp_path itself is the base, so 'configs/test_config.json' is fine.
    agent_config_dir = tmp_path / "configs" 
    agent_config_dir.mkdir() # Ensure directory exists, as write_agent_config might expect it for os.path.dirname
    file_path = agent_config_dir / "test_config.json"

    utils.write_agent_config(str(file_path), config_data)
    assert file_path.exists()
    
    read_data = utils.read_agent_config(str(file_path))
    assert read_data == config_data

def test_read_agent_config_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        utils.read_agent_config(str(tmp_path / "non_existent.json"))

def test_read_agent_config_invalid_json(tmp_path):
    invalid_json_file = create_temp_file(tmp_path, "invalid.json", "{'bad': json,}") # Malformed JSON
    with pytest.raises(json.JSONDecodeError):
        utils.read_agent_config(str(invalid_json_file))

# --- Tests for lock file functions ---
LOCK_FILE_TEST_NAME = "test.lock"

def test_load_lock_file_not_exists(tmp_path):
    lock_data = utils.load_lock_file(str(tmp_path / LOCK_FILE_TEST_NAME))
    assert lock_data == {utils.LOCK_FILE_AGENTS_KEY: {}}

def test_save_and_load_lock_file(tmp_path):
    lock_data_to_save = {
        utils.LOCK_FILE_AGENTS_KEY: {
            "agent1": {"dev": {"id": "id1", "hash": "hash1"}}
        }
    }
    lock_file_path = tmp_path / LOCK_FILE_TEST_NAME # Save directly in tmp_path
    
    utils.save_lock_file(str(lock_file_path), lock_data_to_save)
    assert lock_file_path.exists()
    
    loaded_data = utils.load_lock_file(str(lock_file_path))
    assert loaded_data == lock_data_to_save

def test_load_lock_file_malformed_json(tmp_path):
    # Test case from the issue: malformed JSON should return default structure
    malformed_file = create_temp_file(tmp_path, "malformed.lock", "{this_is_not_json")
    lock_data = utils.load_lock_file(str(malformed_file))
    assert lock_data == {utils.LOCK_FILE_AGENTS_KEY: {}}
    # Add another test for a file that is JSON but not the expected structure
    wrong_structure_file = create_temp_file(tmp_path, "wrong_structure.lock", '{"not_agents": {}}')
    lock_data_ws = utils.load_lock_file(str(wrong_structure_file))
    assert lock_data_ws == {utils.LOCK_FILE_AGENTS_KEY: {}}


def test_get_agent_from_lock():
    lock_data = {
        utils.LOCK_FILE_AGENTS_KEY: {
            "agent1": {
                "dev": {"id": "id_dev", "hash": "hash_dev"},
                "prod": {"id": "id_prod", "hash": "hash_prod"}
            },
            "agent2": {"staging": {"id": "id_stage", "hash": "hash_stage"}}
        }
    }
    assert utils.get_agent_from_lock(lock_data, "agent1", "dev") == {"id": "id_dev", "hash": "hash_dev"}
    assert utils.get_agent_from_lock(lock_data, "agent1", "prod") == {"id": "id_prod", "hash": "hash_prod"}
    assert utils.get_agent_from_lock(lock_data, "agent2", "staging") == {"id": "id_stage", "hash": "hash_stage"}
    assert utils.get_agent_from_lock(lock_data, "agent1", "nonexistent_tag") is None
    assert utils.get_agent_from_lock(lock_data, "nonexistent_agent", "dev") is None
    empty_lock = {utils.LOCK_FILE_AGENTS_KEY: {}}
    assert utils.get_agent_from_lock(empty_lock, "agent1", "dev") is None


def test_update_agent_in_lock():
    # Start with an empty but valid lock structure from load_lock_file
    lock_data = utils.load_lock_file("non_existent_path_for_default_struct")
    
    # Add new agent
    utils.update_agent_in_lock(lock_data, "agent1", "dev", "new_id_1", "new_hash_1")
    expected = {"id": "new_id_1", "hash": "new_hash_1"}
    assert lock_data[utils.LOCK_FILE_AGENTS_KEY]["agent1"]["dev"] == expected
    
    # Update existing agent
    utils.update_agent_in_lock(lock_data, "agent1", "dev", "updated_id_1", "updated_hash_1")
    expected_updated = {"id": "updated_id_1", "hash": "updated_hash_1"}
    assert lock_data[utils.LOCK_FILE_AGENTS_KEY]["agent1"]["dev"] == expected_updated
    
    # Add new tag to existing agent
    utils.update_agent_in_lock(lock_data, "agent1", "prod", "new_id_prod", "new_hash_prod")
    expected_prod = {"id": "new_id_prod", "hash": "new_hash_prod"}
    assert lock_data[utils.LOCK_FILE_AGENTS_KEY]["agent1"]["prod"] == expected_prod
    
    # Add completely new agent and tag
    utils.update_agent_in_lock(lock_data, "agent2", "staging", "id_agent2_stage", "hash_agent2_stage")
    expected_agent2 = {"id": "id_agent2_stage", "hash": "hash_agent2_stage"}
    assert lock_data[utils.LOCK_FILE_AGENTS_KEY]["agent2"]["staging"] == expected_agent2
    
    # Check overall structure integrity
    assert utils.LOCK_FILE_AGENTS_KEY in lock_data
    assert "agent1" in lock_data[utils.LOCK_FILE_AGENTS_KEY]
    assert "dev" in lock_data[utils.LOCK_FILE_AGENTS_KEY]["agent1"]
    assert "prod" in lock_data[utils.LOCK_FILE_AGENTS_KEY]["agent1"]
    assert "agent2" in lock_data[utils.LOCK_FILE_AGENTS_KEY]
    assert "staging" in lock_data[utils.LOCK_FILE_AGENTS_KEY]["agent2"]

# Example of how write_agent_config creates parent directory if not exists
def test_write_agent_config_creates_subdir(tmp_path):
    config_data = {"setting": "test"}
    # utils.write_agent_config is expected to create 'parent_dir' if it doesn't exist.
    file_path = tmp_path / "parent_dir" / "my_config.json" 
    
    utils.write_agent_config(str(file_path), config_data)
    assert file_path.exists()
    read_data = utils.read_agent_config(str(file_path))
    assert read_data == config_data
