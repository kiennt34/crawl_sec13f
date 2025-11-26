"""
OpenAI (ChatGPT) Agent Implementation

This module provides an AI agent implementation using standard OpenAI API.
"""
import os
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI
from aiagent.base import BaseAIAgent, AIResponse


class OpenAIAgent(BaseAIAgent):
    """
    AI agent using standard OpenAI API (ChatGPT).
    """
    
    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize OpenAI agent.
        
        Args:
            model: Model name (default: "gpt-4")
            api_key: OpenAI API key (defaults to env var OPENAI_API_KEY)
            base_url: Custom base URL (for OpenAI-compatible APIs)
            **kwargs: Additional configuration
        """
        super().__init__(model=model, **kwargs)
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.api_key = api_key
        self.base_url = base_url
        
        # Initialize client
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self.client = OpenAI(**client_kwargs)
    
    def generate(
        self,
        content: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        verbose: bool = False,
        **kwargs
    ) -> AIResponse:
        """
        Generate a response using OpenAI.
        
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
        
        request_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        if max_tokens:
            request_kwargs["max_tokens"] = max_tokens
        
        response = self.client.chat.completions.create(**request_kwargs)
        
        processing_time = time.time() - start_time
        
        # Extract usage statistics
        usage = response.usage if hasattr(response, 'usage') and response.usage else None
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None
        
        if verbose:
            print(f"\n=== OpenAI Generation ===")
            print(f"  Model: {self.model}")
            if prompt_tokens:
                print(f"  Prompt Tokens: {prompt_tokens}")
                print(f"  Completion Tokens: {completion_tokens}")
                print(f"  Total Tokens: {total_tokens}")
            print(f"  Processing Time: {processing_time:.2f} seconds")
            if total_tokens:
                print(f"  Tokens/Second: {total_tokens / processing_time:.2f}")
        
        return AIResponse(
            content=response.choices[0].message.content,
            model=self.model,
            provider="openai",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            processing_time=processing_time,
            metadata={
                "base_url": self.base_url,
            }
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        verbose: bool = False,
        **kwargs
    ) -> AIResponse:
        """
        Chat with OpenAI using a list of messages.
        
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
        
        request_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        if max_tokens:
            request_kwargs["max_tokens"] = max_tokens
        
        response = self.client.chat.completions.create(**request_kwargs)
        
        processing_time = time.time() - start_time
        
        # Extract usage statistics
        usage = response.usage if hasattr(response, 'usage') and response.usage else None
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None
        
        if verbose:
            print(f"\n=== OpenAI Chat ===")
            print(f"  Model: {self.model}")
            if prompt_tokens:
                print(f"  Prompt Tokens: {prompt_tokens}")
                print(f"  Completion Tokens: {completion_tokens}")
                print(f"  Total Tokens: {total_tokens}")
            print(f"  Processing Time: {processing_time:.2f} seconds")
            if total_tokens:
                print(f"  Tokens/Second: {total_tokens / processing_time:.2f}")
        
        return AIResponse(
            content=response.choices[0].message.content,
            model=self.model,
            provider="openai",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            processing_time=processing_time,
            metadata={
                "base_url": self.base_url,
            }
        )

