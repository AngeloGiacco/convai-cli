def get_default_agent_template(name: str) -> dict:
    """
    Returns a complete default agent configuration template with all available fields.
    
    Args:
        name: The name of the agent
        
    Returns:
        A dictionary containing the complete agent configuration template
    """
    return {
        "name": name,
        "conversation_config": {
            "asr": {
                "quality": "high",
                "provider": "elevenlabs",
                "user_input_audio_format": "pcm_16000",
                "keywords": []
            },
            "turn": {
                "turn_timeout": 7.0,
                "silence_end_call_timeout": -1.0,
                "mode": "turn"
            },
            "tts": {
                "model_id": "eleven_turbo_v2",
                "voice_id": "cjVigY5qzO86Huf0OWal",  # Default voice ID
                "supported_voices": [],
                "agent_output_audio_format": "pcm_16000",
                "optimize_streaming_latency": 3,
                "stability": 0.5,
                "speed": 1.0,
                "similarity_boost": 0.8,
                "pronunciation_dictionary_locators": []
            },
            "conversation": {
                "text_only": False,
                "max_duration_seconds": 600,
                "client_events": [
                    "audio",
                    "interruption"
                ]
            },
            "language_presets": {},
            "agent": {
                "first_message": "",
                "language": "en",
                "dynamic_variables": {
                    "dynamic_variable_placeholders": {}
                },
                "prompt": {
                    "prompt": f"You are {name}, a helpful AI assistant.",
                    "llm": "gemini-2.0-flash",
                    "temperature": 0.0,
                    "max_tokens": -1,
                    "tools": [],
                    "tool_ids": [],
                    "mcp_server_ids": [],
                    "native_mcp_server_ids": [],
                    "knowledge_base": [],
                    "ignore_default_personality": False,
                    "rag": {
                        "enabled": False,
                        "embedding_model": "e5_mistral_7b_instruct",
                        "max_vector_distance": 0.6,
                        "max_documents_length": 50000,
                        "max_retrieved_rag_chunks_count": 20
                    },
                    "custom_llm": None
                }
            }
        },
        "platform_settings": {
            "auth": {
                "enable_auth": False,
                "allowlist": [],
                "shareable_token": None
            },
            "evaluation": {
                "criteria": []
            },
            "widget": {
                "variant": "full",
                "placement": "bottom-right",
                "expandable": "never",
                "avatar": {
                    "type": "orb",
                    "color_1": "#2792dc",
                    "color_2": "#9ce6e6"
                },
                "feedback_mode": "none",
                "bg_color": "#ffffff",
                "text_color": "#000000",
                "btn_color": "#000000",
                "btn_text_color": "#ffffff",
                "border_color": "#e1e1e1",
                "focus_color": "#000000",
                "shareable_page_show_terms": True,
                "show_avatar_when_collapsed": False,
                "disable_banner": False,
                "mic_muting_enabled": False,
                "transcript_enabled": False,
                "text_input_enabled": True,
                "text_contents": {
                    "main_label": None,
                    "start_call": None,
                    "new_call": None,
                    "end_call": None,
                    "mute_microphone": None,
                    "change_language": None,
                    "collapse": None,
                    "expand": None,
                    "copied": None,
                    "accept_terms": None,
                    "dismiss_terms": None,
                    "listening_status": None,
                    "speaking_status": None,
                    "connecting_status": None,
                    "input_label": None,
                    "input_placeholder": None,
                    "user_ended_conversation": None,
                    "agent_ended_conversation": None,
                    "conversation_id": None,
                    "error_occurred": None,
                    "copy_id": None
                },
                "language_selector": False,
                "supports_text_only": True,
                "language_presets": {},
                "styles": {
                    "base": None,
                    "base_hover": None,
                    "base_active": None,
                    "base_border": None,
                    "base_subtle": None,
                    "base_primary": None,
                    "base_error": None,
                    "accent": None,
                    "accent_hover": None,
                    "accent_active": None,
                    "accent_border": None,
                    "accent_subtle": None,
                    "accent_primary": None,
                    "overlay_padding": None,
                    "button_radius": None,
                    "input_radius": None,
                    "bubble_radius": None,
                    "sheet_radius": None,
                    "compact_sheet_radius": None,
                    "dropdown_sheet_radius": None
                },
                "border_radius": None,
                "btn_radius": None,
                "action_text": None,
                "start_call_text": None,
                "end_call_text": None,
                "expand_text": None,
                "listening_text": None,
                "speaking_text": None,
                "shareable_page_text": None,
                "terms_text": None,
                "terms_html": None,
                "terms_key": None,
                "override_link": None,
                "custom_avatar_path": None
            },
            "data_collection": {},
            "overrides": {
                "conversation_config_override": {
                    "tts": {
                        "voice_id": False
                    },
                    "conversation": {
                        "text_only": True
                    },
                    "agent": {
                        "first_message": False,
                        "language": False,
                        "prompt": {
                            "prompt": False
                        }
                    }
                },
                "custom_llm_extra_body": False,
                "enable_conversation_initiation_client_data_from_webhook": False
            },
            "call_limits": {
                "agent_concurrency_limit": -1,
                "daily_limit": 100000,
                "bursting_enabled": True
            },
            "privacy": {
                "record_voice": True,
                "retention_days": -1,
                "delete_transcript_and_pii": False,
                "delete_audio": False,
                "apply_to_existing_conversations": False,
                "zero_retention_mode": False
            },
            "workspace_overrides": {
                "webhooks": {
                    "post_call_webhook_id": None
                },
                "conversation_initiation_client_data_webhook": None
            },
            "safety": {
                "is_blocked_ivc": False,
                "is_blocked_non_ivc": False,
                "ignore_safety_evaluation": False
            },
            "ban": None
        },
        "tags": []
    }


def get_minimal_agent_template(name: str) -> dict:
    """
    Returns a minimal agent configuration template with only essential fields.
    
    Args:
        name: The name of the agent
        
    Returns:
        A dictionary containing the minimal agent configuration template
    """
    return {
        "name": name,
        "conversation_config": {
            "agent": {
                "prompt": {
                    "prompt": f"You are {name}, a helpful AI assistant.",
                    "llm": "gemini-2.0-flash",
                    "temperature": 0.0
                },
                "language": "en"
            },
            "tts": {
                "model_id": "eleven_turbo_v2",
                "voice_id": "cjVigY5qzO86Huf0OWal"
            }
        },
        "platform_settings": {},
        "tags": []
    }


def get_template_options() -> dict:
    """
    Returns available template options with descriptions.
    
    Returns:
        A dictionary mapping template names to descriptions
    """
    return {
        "default": "Complete configuration with all available fields and sensible defaults",
        "minimal": "Minimal configuration with only essential fields",
        "voice-only": "Optimized for voice-only conversations",
        "text-only": "Optimized for text-only conversations",
        "customer-service": "Pre-configured for customer service scenarios",
        "assistant": "General purpose AI assistant configuration"
    }


def get_voice_only_template(name: str) -> dict:
    """
    Returns a template optimized for voice-only conversations.
    """
    template = get_default_agent_template(name)
    template["conversation_config"]["conversation"]["text_only"] = False
    template["platform_settings"]["widget"]["supports_text_only"] = False
    template["platform_settings"]["widget"]["text_input_enabled"] = False
    return template


def get_text_only_template(name: str) -> dict:
    """
    Returns a template optimized for text-only conversations.
    """
    template = get_default_agent_template(name)
    template["conversation_config"]["conversation"]["text_only"] = True
    template["platform_settings"]["widget"]["supports_text_only"] = True
    template["platform_settings"]["overrides"]["conversation_config_override"]["conversation"]["text_only"] = False
    return template


def get_customer_service_template(name: str) -> dict:
    """
    Returns a template pre-configured for customer service scenarios.
    """
    template = get_default_agent_template(name)
    template["conversation_config"]["agent"]["prompt"]["prompt"] = f"You are {name}, a helpful customer service representative. You are professional, empathetic, and focused on solving customer problems efficiently."
    template["conversation_config"]["agent"]["prompt"]["temperature"] = 0.1  # More consistent responses
    template["conversation_config"]["conversation"]["max_duration_seconds"] = 1800  # 30 minutes
    template["platform_settings"]["call_limits"]["daily_limit"] = 10000
    template["platform_settings"]["evaluation"]["criteria"] = [
        "Helpfulness",
        "Professionalism", 
        "Problem Resolution",
        "Response Time"
    ]
    template["tags"] = ["customer-service"]
    return template


def get_assistant_template(name: str) -> dict:
    """
    Returns a general purpose AI assistant template.
    """
    template = get_default_agent_template(name)
    template["conversation_config"]["agent"]["prompt"]["prompt"] = f"You are {name}, a knowledgeable and helpful AI assistant. You can help with a wide variety of tasks including answering questions, providing explanations, helping with analysis, and creative tasks."
    template["conversation_config"]["agent"]["prompt"]["temperature"] = 0.3  # Balanced creativity
    template["conversation_config"]["agent"]["prompt"]["max_tokens"] = 1000
    template["tags"] = ["assistant", "general-purpose"]
    return template


def get_template_by_name(name: str, template_type: str = "default") -> dict:
    """
    Returns a template by name and type.
    
    Args:
        name: The agent name
        template_type: The type of template to generate
        
    Returns:
        A dictionary containing the agent configuration template
        
    Raises:
        ValueError: If template_type is not recognized
    """
    template_functions = {
        "default": get_default_agent_template,
        "minimal": get_minimal_agent_template,
        "voice-only": get_voice_only_template,
        "text-only": get_text_only_template,
        "customer-service": get_customer_service_template,
        "assistant": get_assistant_template
    }
    
    if template_type not in template_functions:
        available = ", ".join(template_functions.keys())
        raise ValueError(f"Unknown template type '{template_type}'. Available: {available}")
    
    return template_functions[template_type](name) 