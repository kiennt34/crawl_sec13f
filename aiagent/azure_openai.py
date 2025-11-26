"""
Azure OpenAI Agent Implementation

This module provides an AI agent implementation using Azure OpenAI.
"""
import os
import time
from typing import Optional, Dict, Any, List
from openai import AzureOpenAI
from aiagent.base import BaseAIAgent, AIResponse


class AzureOpenAIAgent(BaseAIAgent):
    """
    AI agent using Azure OpenAI service.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        api_version: str = "2024-12-01-preview",
        deployment: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Azure OpenAI agent.

        Args:
            model: Model name (defaults to deployment name or env var)
            api_key: Azure OpenAI API key (defaults to env var)
            azure_endpoint: Azure endpoint URL (defaults to env var)
            api_version: API version (default: "2024-12-01-preview")
            deployment: Deployment name (defaults to env var)
            **kwargs: Additional configuration
        """
        # Get from environment if not provided
        api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        model = model or deployment or os.getenv("AZURE_OPENAI_MODEL")

        if not api_key:
            raise ValueError("Azure OpenAI API key is required")
        if not azure_endpoint:
            raise ValueError("Azure OpenAI endpoint is required")
        if not model:
            raise ValueError("Model/deployment name is required")

        super().__init__(model=model, **kwargs)
        self.api_key = api_key
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version
        self.deployment = deployment or model

        # Initialize client
        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            api_key=api_key,
        )

    def generate(
        self,
        content: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 16384,
        temperature: float = 0.7,
        verbose: bool = False,
        json_output: bool = True,
        **kwargs
    ) -> AIResponse:
        """
        Generate a response using Azure OpenAI.

        Args:
            content: User content
            system_prompt: System prompt (optional)
            max_tokens: Maximum tokens for completion
            temperature: Temperature for generation
            verbose: Whether to print processing info
            **kwargs: Additional parameters

        Returns:
            AIResponse object
        """
        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        response = self.client.chat.completions.create(
            messages=messages,
            max_completion_tokens=max_tokens,
            model=self.deployment,
            # temperature=temperature, # Azure OpenAI may not support temperature in all models
            **kwargs
        )

        processing_time = time.time() - start_time

        # Extract usage statistics
        usage = response.usage if hasattr(
            response, 'usage') and response.usage else None
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None

        if verbose:
            print(f"\n=== Azure OpenAI Generation ===")
            if prompt_tokens:
                print(f"  Prompt Tokens: {prompt_tokens}")
                print(f"  Completion Tokens: {completion_tokens}")
                print(f"  Total Tokens: {total_tokens}")
            print(f"  Processing Time: {processing_time:.2f} seconds")
            if total_tokens:
                print(f"  Tokens/Second: {total_tokens / processing_time:.2f}")

        if json_output:
            response.choices[0].message.content = self.format_json_output(
                response.choices[0].message.content)

        return AIResponse(
            content=response.choices[0].message.content,
            model=self.model,
            provider="azure_openai",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            processing_time=processing_time,
            metadata={
                "deployment": self.deployment,
                "api_version": self.api_version,
            }
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 16384,
        # temperature: float = 0.7, # TEMPORARILY DISABLED DUE TO SOME AZURE OPENAI MODELS UNSUPPORTED, DEFAULT (1)
        verbose: bool = False,
        json_output: bool = True,
        **kwargs
    ) -> AIResponse:
        """
        Chat with Azure OpenAI using a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens for completion
            temperature: Temperature for generation
            verbose: Whether to print processing info
            **kwargs: Additional parameters

        Returns:
            AIResponse object
        """
        start_time = time.time()

        response = self.client.chat.completions.create(
            messages=messages,
            max_completion_tokens=max_tokens,
            model=self.deployment,
            # temperature=temperature, # TEMPORARILY DISABLED DUE TO SOME AZURE OPENAI MODELS UNSUPPORTED, DEFAULT (1)
            **kwargs
        )

        processing_time = time.time() - start_time

        # Extract usage statistics
        usage = response.usage if hasattr(
            response, 'usage') and response.usage else None
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None

        if verbose:
            print(f"\n=== Azure OpenAI Chat ===")
            if prompt_tokens:
                print(f"  Prompt Tokens: {prompt_tokens}")
                print(f"  Completion Tokens: {completion_tokens}")
                print(f"  Total Tokens: {total_tokens}")
            print(f"  Processing Time: {processing_time:.2f} seconds")
            if total_tokens:
                print(f"  Tokens/Second: {total_tokens / processing_time:.2f}")

        if json_output:
            response.choices[0].message.content = self.format_json_output(
                response.choices[0].message.content)

        return AIResponse(
            content=response.choices[0].message.content,
            model=self.model,
            provider="azure_openai",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            processing_time=processing_time,
            metadata={
                "deployment": self.deployment,
                "api_version": self.api_version,
            }
        )

    def format_json_output(self, content: str) -> str:
        """
        Format JSON output.
        """
        # Strip redundant text from content like "Here is the JSON analysis of the call transcript:"
        if content.startswith('```json'):
            content = content.split('```json')[1].split('```')[0].strip()
        elif content.startswith('```'):
            content = content.split('```')[1].split('```')[0].strip()
        if not content.startswith('{'):
            start_index = content.find('{')
            if start_index != -1:
                content = content[start_index:]
        return content
