"""
AI Agent Factory

This module provides a factory pattern for creating AI agents easily.
"""
from typing import Optional, Dict, Any
from aiagent.base import BaseAIAgent, AIResponse
from aiagent.azure_openai import AzureOpenAIAgent
from aiagent.ollama import OllamaAgent
from aiagent.openai_client import OpenAIAgent


class AIAgentFactory:
    """
    Factory for creating AI agents.
    """

    _providers = {
        "azure": AzureOpenAIAgent,
        "azure_openai": AzureOpenAIAgent,
        "ollama": OllamaAgent,
        "openai": OpenAIAgent,
        "chatgpt": OpenAIAgent,
    }

    @classmethod
    def create(
        cls,
        provider: str,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseAIAgent:
        """
        Create an AI agent for the specified provider.

        Args:
            provider: Provider name ("azure", "ollama", "openai", "chatgpt")
            model: Model name (optional, uses defaults if not provided)
            **kwargs: Additional provider-specific configuration

        Returns:
            BaseAIAgent instance

        Raises:
            ValueError: If provider is not supported
        """
        provider_lower = provider.lower()

        if provider_lower not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available providers: {available}"
            )

        agent_class = cls._providers[provider_lower]

        # Only pass model if provided
        if model:
            kwargs["model"] = model

        return agent_class(**kwargs)

    @classmethod
    def register_provider(cls, name: str, agent_class: type):
        """
        Register a custom provider.

        Args:
            name: Provider name
            agent_class: Agent class that inherits from BaseAIAgent
        """
        if not issubclass(agent_class, BaseAIAgent):
            raise ValueError(
                f"Agent class must inherit from BaseAIAgent, got {agent_class}"
            )
        cls._providers[name.lower()] = agent_class

    @classmethod
    def list_providers(cls) -> list:
        """List all available providers."""
        return list(cls._providers.keys())


# Convenience functions
def create_agent(provider: str, model: Optional[str] = None, **kwargs) -> BaseAIAgent:
    """Create an AI agent (convenience function)."""
    return AIAgentFactory.create(provider, model, **kwargs)


def create_azure_agent(model: Optional[str] = None, **kwargs) -> AzureOpenAIAgent:
    """Create an Azure OpenAI agent (convenience function)."""
    return AIAgentFactory.create("azure", model, **kwargs)


def create_ollama_agent(model: str = "llama3.1:8b", **kwargs) -> OllamaAgent:
    """Create an Ollama agent (convenience function)."""
    return AIAgentFactory.create("ollama", model, **kwargs)


def create_openai_agent(model: str = "gpt-4", **kwargs) -> OpenAIAgent:
    """Create an OpenAI agent (convenience function)."""
    return AIAgentFactory.create("openai", model, **kwargs)


def pretty_print_agent_response(response: AIResponse) -> None:
    """Pretty print agent response."""
    print("\n=== Agent Response Summary ===")
    print(f"Content: {response.content}")
    print(f"Model: {response.model}")
    print(f"Provider: {response.provider}")
    if response.prompt_tokens:
        print(f"Prompt Tokens: {response.prompt_tokens}")
    if response.completion_tokens:
        print(f"Completion Tokens: {response.completion_tokens}")
    if response.total_tokens:
        print(f"Total Tokens: {response.total_tokens}")
    print(f"Processing Time: {response.processing_time:.2f} seconds")
    if response.metadata:
        print(f"Metadata: {response.metadata}")
