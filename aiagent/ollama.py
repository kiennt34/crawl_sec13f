"""
Ollama Agent Implementation

This module provides an AI agent implementation using local Ollama.
"""
import os
import time
import requests
from typing import Optional, Dict, Any, List
from aiagent.base import BaseAIAgent, AIResponse


class OllamaAgent(BaseAIAgent):
    """
    AI agent using local Ollama service.
    """
    
    def __init__(
        self,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        **kwargs
    ):
        """
        Initialize Ollama agent.
        
        Args:
            model: Ollama model name (default: "llama3.1:8b")
            base_url: Ollama API base URL (default: "http://localhost:11434")
            **kwargs: Additional configuration
        """
        super().__init__(model=model, **kwargs)
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def generate(
        self,
        content: str,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        timeout: int = 300,
        verbose: bool = False,
        **kwargs
    ) -> AIResponse:
        """
        Generate a response using Ollama.
        
        Args:
            content: User content
            system_prompt: System prompt (optional, Ollama uses prompt directly)
            stream: Whether to stream the response
            timeout: Request timeout in seconds
            verbose: Whether to print processing info
            **kwargs: Additional parameters (temperature, etc.)
        
        Returns:
            AIResponse object
        """
        start_time = time.time()
        
        # Combine system prompt and content if provided
        if system_prompt:
            prompt = f"{system_prompt}\n\n{content}"
        else:
            prompt = content
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }
        
        response = requests.post(
            self.api_url,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        
        processing_time = time.time() - start_time
        
        if verbose:
            print(f"\n=== Ollama Generation ===")
            print(f"  Model: {self.model}")
            print(f"  Processing Time: {processing_time:.2f} seconds")
        
        return AIResponse(
            content=data.get("response", ""),
            model=self.model,
            provider="ollama",
            processing_time=processing_time,
            metadata={
                "base_url": self.base_url,
                "done": data.get("done", False),
                "context": data.get("context"),
            }
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        timeout: int = 300,
        verbose: bool = False,
        **kwargs
    ) -> AIResponse:
        """
        Chat with Ollama using a list of messages.
        Note: Ollama's generate API doesn't support chat format directly,
        so we convert messages to a prompt format.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            timeout: Request timeout in seconds
            verbose: Whether to print processing info
            **kwargs: Additional parameters
        
        Returns:
            AIResponse object
        """
        start_time = time.time()
        
        # Convert messages to prompt format
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            **kwargs
        }
        
        response = requests.post(
            self.api_url,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        
        processing_time = time.time() - start_time
        
        if verbose:
            print(f"\n=== Ollama Chat ===")
            print(f"  Model: {self.model}")
            print(f"  Processing Time: {processing_time:.2f} seconds")
        
        return AIResponse(
            content=data.get("response", ""),
            model=self.model,
            provider="ollama",
            processing_time=processing_time,
            metadata={
                "base_url": self.base_url,
                "done": data.get("done", False),
                "context": data.get("context"),
            }
        )

