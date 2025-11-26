"""
Base AI Agent Interface

This module defines the abstract base class for all AI agents,
ensuring a consistent interface across different AI providers.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import time


@dataclass
class AIResponse:
    """
    Standardized response from AI agents.
    Designed for easy database insertion and consistent handling.
    """
    content: str
    model: str
    provider: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "processing_time": self.processing_time,
            "metadata": self.metadata,
        }


class BaseAIAgent(ABC):
    """
    Abstract base class for all AI agents.
    All AI implementations should inherit from this class.
    """
    
    def __init__(self, model: str, **kwargs):
        """
        Initialize the AI agent.
        
        Args:
            model: Model name/identifier
            **kwargs: Additional provider-specific configuration
        """
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    def generate(
        self,
        content: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        Generate a response from the AI.
        
        Args:
            content: User content/message
            system_prompt: Optional system prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            AIResponse object with the generated content and metadata
        """
        pass
    
    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AIResponse:
        """
        Chat with the AI using a list of messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            **kwargs: Additional parameters
        
        Returns:
            AIResponse object with the generated content and metadata
        """
        pass
    
    def process(
        self,
        content: str,
        prompt_template: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """
        Process content with optional prompt template.
        Convenience method that combines prompt template with content.
        
        Args:
            content: Content to process
            prompt_template: Optional template string with {content} placeholder
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
        
        Returns:
            AIResponse object
        """
        if prompt_template:
            user_content = prompt_template.format(content=content)
        else:
            user_content = content
        
        return self.generate(
            content=user_content,
            system_prompt=system_prompt,
            **kwargs
        )

