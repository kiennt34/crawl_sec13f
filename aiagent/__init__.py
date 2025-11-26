"""
AI Agent Module

This module provides a comprehensive framework for interacting with various AI providers,
including Azure OpenAI, Ollama, and standard OpenAI (ChatGPT).

The framework is designed to be easily extensible for different AI purposes and prompts.
"""

from aiagent.base import BaseAIAgent, AIResponse
from aiagent.azure_openai import AzureOpenAIAgent
from aiagent.ollama import OllamaAgent
from aiagent.openai_client import OpenAIAgent
from aiagent.prompt_manager import (
    PromptManager,
    get_prompt_manager,
    load_prompt,
    format_prompt,
    format_analysis_prompt,
    format_analysis_recording_prompt,
    format_analysis_webdata_prompt,
)
from aiagent.factory import (
    AIAgentFactory,
    create_agent,
    create_azure_agent,
    create_ollama_agent,
    create_openai_agent,
    pretty_print_agent_response,
)

__all__ = [
    # Base classes
    "BaseAIAgent",
    "AIResponse",
    # Agent implementations
    "AzureOpenAIAgent",
    "OllamaAgent",
    "OpenAIAgent",
    # Prompt management
    "PromptManager",
    "get_prompt_manager",
    "load_prompt",
    "format_prompt",
    "format_analysis_prompt",
    "format_analysis_recording_prompt",
    "format_analysis_webdata_prompt",
    # Factory
    "AIAgentFactory",
    "create_agent",
    "create_azure_agent",
    "create_ollama_agent",
    "create_openai_agent",
]
