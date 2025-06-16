import os
import typing
from elevenlabs import ElevenLabs, ConversationalConfig
from elevenlabs.types import AgentPlatformSettingsRequestModel
from elevenlabs.client import OMIT


def get_elevenlabs_client() -> ElevenLabs:
    """
    Retrieves the ElevenLabs API key from environment variables and returns an API client.

    Raises:
        ValueError: If the ELEVENLABS_API_KEY environment variable is not set.

    Returns:
        An instance of the ElevenLabs client.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set.")
    return ElevenLabs(api_key=api_key)

def create_agent_api(
    client: ElevenLabs,
    name: str,
    conversation_config_dict: dict,
    platform_settings_dict: typing.Optional[dict] = None,
    tags: typing.Optional[typing.List[str]] = None
) -> str:
    """
    Creates a new agent using the ElevenLabs API.

    Args:
        client: An initialized ElevenLabs client.
        name: The name of the agent.
        conversation_config_dict: A dictionary for ConversationalConfig.
        platform_settings_dict: An optional dictionary for AgentPlatformSettingsRequestModel.
        tags: An optional list of tags.

    Returns:
        The agent_id of the newly created agent.
    """
    conv_config = ConversationalConfig(**conversation_config_dict)
    plat_settings_arg = OMIT
    if platform_settings_dict is not None:
        plat_settings_arg = AgentPlatformSettingsRequestModel(**platform_settings_dict)

    tags_arg = OMIT
    if tags is not None:
        tags_arg = tags
    
    response = client.conversational_ai.agents.create(
        name=name,
        conversation_config=conv_config,
        platform_settings=plat_settings_arg,
        tags=tags_arg
    )
    return response.agent_id

def update_agent_api(
    client: ElevenLabs,
    agent_id: str,
    name: typing.Optional[str] = None,
    conversation_config_dict: typing.Optional[dict] = None,
    platform_settings_dict: typing.Optional[dict] = None,
    tags: typing.Optional[typing.List[str]] = None
) -> str:
    """
    Updates an existing agent using the ElevenLabs API.

    Args:
        client: An initialized ElevenLabs client.
        agent_id: The ID of the agent to update.
        name: Optional new name for the agent.
        conversation_config_dict: Optional new dictionary for ConversationalConfig.
        platform_settings_dict: Optional new dictionary for AgentPlatformSettingsRequestModel.
        tags: Optional new list of tags.

    Returns:
        The agent_id of the updated agent.
    """
    name_arg = OMIT
    if name is not None:
        name_arg = name

    conv_config_arg = OMIT
    if conversation_config_dict is not None:
        conv_config_arg = ConversationalConfig(**conversation_config_dict)

    plat_settings_arg = OMIT
    if platform_settings_dict is not None:
        plat_settings_arg = AgentPlatformSettingsRequestModel(**platform_settings_dict)

    tags_arg = OMIT
    if tags is not None:
        tags_arg = tags

    response = client.conversational_ai.agents.update(
        agent_id=agent_id,
        name=name_arg,
        conversation_config=conv_config_arg,
        platform_settings=plat_settings_arg,
        tags=tags_arg
    )
    return response.agent_id

def list_agents_api(
    client: ElevenLabs,
    page_size: int = 30,
    search: typing.Optional[str] = None
) -> typing.List[dict]:
    """
    Lists all agents from the ElevenLabs API.

    Args:
        client: An initialized ElevenLabs client.
        page_size: Maximum number of agents to return per page (default: 30, max: 100).
        search: Optional search string to filter agents by name.

    Returns:
        A list of agent metadata dictionaries.
    """
    all_agents = []
    cursor = None
    
    while True:
        # Build request parameters
        kwargs: typing.Dict[str, typing.Any] = {"page_size": min(page_size, 100)}
        if cursor:
            kwargs["cursor"] = cursor
        if search:
            kwargs["search"] = search
            
        response = client.conversational_ai.agents.list(**kwargs)
        
        all_agents.extend(response.agents)
        
        if not response.has_more:
            break
            
        cursor = response.next_cursor
    
    return [agent.dict() for agent in all_agents]

def get_agent_api(client: ElevenLabs, agent_id: str) -> dict:
    """
    Gets detailed configuration for a specific agent from the ElevenLabs API.

    Args:
        client: An initialized ElevenLabs client.
        agent_id: The ID of the agent to retrieve.

    Returns:
        A dictionary containing the full agent configuration.
    """
    response = client.conversational_ai.agents.get(agent_id=agent_id)
    return response.dict()
