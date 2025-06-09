import hashlib
import json
import os # For write_agent_config to ensure directory exists
import typing

LOCK_FILE_AGENTS_KEY = "agents"

def calculate_config_hash(config: dict) -> str:
    """
    Calculates the MD5 hash of a configuration dictionary.

    Args:
        config: The configuration dictionary.

    Returns:
        The hexadecimal representation of the MD5 hash.
    """
    # Convert the dictionary to a sorted JSON string to ensure consistent hashes
    config_string = json.dumps(config, sort_keys=True, indent=None) # indent=None for more compact string
    
    # Calculate MD5 hash
    hash_object = hashlib.md5(config_string.encode('utf-8'))
    return hash_object.hexdigest()

def read_agent_config(file_path: str) -> dict:
    """
    Reads an agent configuration file.

    Args:
        file_path: The path to the JSON configuration file.

    Returns:
        A dictionary containing the agent configuration.
    
    Raises:
        FileNotFoundError: If the configuration file is not found.
        json.JSONDecodeError: If the configuration file contains invalid JSON.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Log or handle specific error cases if needed, then re-raise
        # print(f"Error: Configuration file not found at {file_path}")
        raise
    except json.JSONDecodeError:
        # Log or handle specific error cases if needed, then re-raise
        # print(f"Error: Invalid JSON in configuration file {file_path}")
        raise

def write_agent_config(file_path: str, config: dict) -> None:
    """
    Writes an agent configuration to a file.

    Args:
        file_path: The path to write the JSON configuration file.
        config: The dictionary containing the agent configuration.

    Raises:
        IOError: If there is an error writing the file.
    """
    try:
        # Ensure the directory exists before writing.
        # This is important if file_path includes directories that might not exist.
        if os.path.dirname(file_path): # Ensure there's a directory part
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except IOError:
        # Log or handle specific error cases if needed, then re-raise
        # print(f"Error: Could not write configuration file to {file_path}")
        raise

def load_lock_file(lock_file_path: str) -> dict:
    """
    Loads the lock file. If it doesn't exist or is invalid, returns a default structure.
    """
    if not os.path.exists(lock_file_path):
        return {LOCK_FILE_AGENTS_KEY: {}}
    try:
        with open(lock_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if LOCK_FILE_AGENTS_KEY not in data or not isinstance(data.get(LOCK_FILE_AGENTS_KEY), dict):
                print(f"Warning: Lock file {lock_file_path} is malformed or missing '{LOCK_FILE_AGENTS_KEY}' key. Initializing with empty agent list.")
                return {LOCK_FILE_AGENTS_KEY: {}}
            return data
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from lock file {lock_file_path}. Initializing with empty agent list.")
        return {LOCK_FILE_AGENTS_KEY: {}}
    except IOError:
        print(f"Warning: Could not read lock file {lock_file_path}. Initializing with empty agent list.")
        return {LOCK_FILE_AGENTS_KEY: {}}

def save_lock_file(lock_file_path: str, lock_data: dict) -> None:
    """
    Saves the lock data to the lock file.
    """
    try:
        # Ensure the directory exists before writing, similar to write_agent_config
        if os.path.dirname(lock_file_path) and not os.path.exists(os.path.dirname(lock_file_path)):
             os.makedirs(os.path.dirname(lock_file_path), exist_ok=True)

        with open(lock_file_path, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, indent=4, ensure_ascii=False)
    except IOError:
        # Consider how to handle this error, e.g., log and raise or just print
        print(f"Error: Could not write lock file to {lock_file_path}")
        raise # Or handle more gracefully depending on CLI requirements

def get_agent_from_lock(lock_data: dict, agent_name: str, tag: str) -> typing.Optional[dict]:
    """
    Retrieves agent ID and hash from lock data by agent name and tag.
    """
    return lock_data.get(LOCK_FILE_AGENTS_KEY, {}).get(agent_name, {}).get(tag)

def update_agent_in_lock(lock_data: dict, agent_name: str, tag: str, agent_id: str, config_hash: str) -> None:
    """
    Updates or adds an agent's ID and hash in the lock data.
    """
    if LOCK_FILE_AGENTS_KEY not in lock_data or not isinstance(lock_data.get(LOCK_FILE_AGENTS_KEY), dict):
        lock_data[LOCK_FILE_AGENTS_KEY] = {}
    
    agents = lock_data[LOCK_FILE_AGENTS_KEY]
    if agent_name not in agents:
        agents[agent_name] = {}
    
    agents[agent_name][tag] = {
        "id": agent_id,
        "hash": config_hash
    }
