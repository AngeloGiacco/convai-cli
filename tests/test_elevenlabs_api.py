import pytest
import os
from unittest.mock import MagicMock, patch

# Assuming these models are correct and available. Adjust if SDK differs.
from elevenlabs import ElevenLabs, ConversationalConfig
from elevenlabs.types import (
    AgentPlatformSettingsRequestModel, 
    CreateAgentResponseModel, 
    # For update, the SDK's conversational_ai.agents.update method
    # returns the full GetAgentResponseModel, not just an ID or a simple confirmation.
    GetAgentResponseModel
)

# Import functions to test and OMIT constant
from elevenlabs_cli_tool.elevenlabs_api import (
    get_elevenlabs_client, 
    create_agent_api, 
    update_agent_api
)
# OMIT should be imported from where it's defined/re-exported in elevenlabs_api.py
# If elevenlabs_api.py uses `from elevenlabs.core import OMIT`, then that's the source.
# For tests, we can assume it's correctly handled by the module itself, or import it if needed for assertions.
from elevenlabs.core import OMIT # Assuming this is the ultimate source of OMIT used in the app code


@pytest.fixture
def mock_elevenlabs_client(mocker): # mocker is a fixture from pytest-mock
    mock_client = MagicMock(spec=ElevenLabs)
    # Mock the nested structure for conversational_ai.agents
    mock_client.conversational_ai = MagicMock()
    mock_client.conversational_ai.agents = MagicMock()
    return mock_client

# --- Tests for get_elevenlabs_client ---
def test_get_elevenlabs_client_success(mocker):
    mocker.patch('os.getenv', return_value='fake_api_key')
    client = get_elevenlabs_client()
    assert isinstance(client, ElevenLabs)
    # Check if api_key was passed to constructor (requires more advanced mock of ElevenLabs constructor if needed)
    # For now, type check is a good start.

def test_get_elevenlabs_client_no_api_key(mocker):
    mocker.patch('os.getenv', return_value=None)
    with pytest.raises(ValueError, match="ELEVENLABS_API_KEY environment variable not set."):
        get_elevenlabs_client()

# --- Tests for create_agent_api ---
def test_create_agent_api_basic_required_params(mock_elevenlabs_client):
    # Prepare mock response from the API
    # CreateAgentResponseModel is what the SDK's agents.create() method returns.
    mock_api_response = CreateAgentResponseModel(agent_id="new_agent_123", initial_status="creating", tools=[])
    mock_elevenlabs_client.conversational_ai.agents.create.return_value = mock_api_response
    
    conv_config_dict = {"model_id": "eleven_turbo_v2"} 
    agent_name = "Test Agent Basic"

    # Call the function under test
    returned_agent_id = create_agent_api(mock_elevenlabs_client, agent_name, conv_config_dict)

    assert returned_agent_id == "new_agent_123"
    
    # Verify the mocked API call
    mock_elevenlabs_client.conversational_ai.agents.create.assert_called_once()
    call_args = mock_elevenlabs_client.conversational_ai.agents.create.call_args
    
    assert call_args.kwargs['name'] == agent_name
    assert isinstance(call_args.kwargs['conversation_config'], ConversationalConfig)
    assert call_args.kwargs['conversation_config'].model_id == "eleven_turbo_v2"
    # Check that optional parameters default to OMIT
    assert call_args.kwargs['platform_settings'] == OMIT
    assert call_args.kwargs['tags'] == OMIT

def test_create_agent_api_with_all_params(mock_elevenlabs_client):
    mock_api_response = CreateAgentResponseModel(agent_id="agent_xyz_full", initial_status="ready", tools=[])
    mock_elevenlabs_client.conversational_ai.agents.create.return_value = mock_api_response

    agent_name = "Full Param Agent"
    conv_config_dict = {"max_tokens": 200, "model_id": "eleven_multilingual_v2"}
    plat_settings_dict = {"some_platform_setting": "enabled"}
    tags_list = ["customer_service", "beta"]

    returned_agent_id = create_agent_api(
        mock_elevenlabs_client,
        name=agent_name,
        conversation_config_dict=conv_config_dict,
        platform_settings_dict=plat_settings_dict,
        tags=tags_list
    )

    assert returned_agent_id == "agent_xyz_full"
    call_args = mock_elevenlabs_client.conversational_ai.agents.create.call_args
    
    assert call_args.kwargs['name'] == agent_name
    assert isinstance(call_args.kwargs['conversation_config'], ConversationalConfig)
    assert call_args.kwargs['conversation_config'].max_tokens == 200
    assert isinstance(call_args.kwargs['platform_settings'], AgentPlatformSettingsRequestModel)
    assert call_args.kwargs['platform_settings'].some_platform_setting == "enabled"
    assert call_args.kwargs['tags'] == tags_list

# --- Tests for update_agent_api ---
@pytest.fixture
def mock_update_response():
    # Helper to create a valid-looking GetAgentResponseModel for update calls
    # These fields are just examples, ensure they match SDK requirements if code uses them
    mock_conv_config = MagicMock(spec=ConversationalConfig)
    mock_plat_settings = MagicMock(spec=AgentPlatformSettingsRequestModel)
    return GetAgentResponseModel(
        agent_id="updated_agent_id", 
        name="Updated Agent Name", 
        conversation_config=mock_conv_config, 
        tools=[], 
        platform_settings=mock_plat_settings, 
        tags=[]
    )

def test_update_agent_api_only_name(mock_elevenlabs_client, mock_update_response):
    mock_elevenlabs_client.conversational_ai.agents.update.return_value = mock_update_response
    
    agent_id_to_update = "existing_agent_456"
    new_name = "Updated Agent Name Only"
    
    # The update_agent_api function in the app returns the agent_id from the response.
    returned_agent_id = update_agent_api(mock_elevenlabs_client, agent_id_to_update, name=new_name)
    
    assert returned_agent_id == mock_update_response.agent_id 
    
    mock_elevenlabs_client.conversational_ai.agents.update.assert_called_once_with(
        agent_id=agent_id_to_update,
        name=new_name,
        conversation_config=OMIT,
        platform_settings=OMIT,
        tags=OMIT
    )

def test_update_agent_api_with_all_params(mock_elevenlabs_client, mock_update_response):
    mock_elevenlabs_client.conversational_ai.agents.update.return_value = mock_update_response

    agent_id_to_update = "existing_agent_789"
    new_name = "Fully Updated Agent"
    conv_config_dict = {"temperature": 0.75, "model_id": "eleven_monolingual_v1"}
    plat_settings_dict = {"another_setting": True}
    tags_list = ["priority_support", "alpha_feature"]

    returned_agent_id = update_agent_api(
        mock_elevenlabs_client,
        agent_id=agent_id_to_update,
        name=new_name,
        conversation_config_dict=conv_config_dict,
        platform_settings_dict=plat_settings_dict,
        tags=tags_list
    )

    assert returned_agent_id == mock_update_response.agent_id
    call_args = mock_elevenlabs_client.conversational_ai.agents.update.call_args
    
    assert call_args.kwargs['agent_id'] == agent_id_to_update
    assert call_args.kwargs['name'] == new_name
    assert isinstance(call_args.kwargs['conversation_config'], ConversationalConfig)
    assert call_args.kwargs['conversation_config'].temperature == 0.75
    assert isinstance(call_args.kwargs['platform_settings'], AgentPlatformSettingsRequestModel)
    assert call_args.kwargs['platform_settings'].another_setting is True
    assert call_args.kwargs['tags'] == tags_list

def test_update_agent_api_no_optional_params(mock_elevenlabs_client, mock_update_response):
    # Test that if only agent_id is given (which is not practical for an update, but tests OMIT logic)
    # or if all optional params are explicitly None
    mock_elevenlabs_client.conversational_ai.agents.update.return_value = mock_update_response
    agent_id_to_update = "agent_id_only"

    returned_agent_id = update_agent_api(
        mock_elevenlabs_client, 
        agent_id=agent_id_to_update,
        name=None, # Explicitly None
        conversation_config_dict=None,
        platform_settings_dict=None,
        tags=None
    )
    assert returned_agent_id == mock_update_response.agent_id
    mock_elevenlabs_client.conversational_ai.agents.update.assert_called_once_with(
        agent_id=agent_id_to_update,
        name=OMIT,
        conversation_config=OMIT,
        platform_settings=OMIT,
        tags=OMIT
    )
