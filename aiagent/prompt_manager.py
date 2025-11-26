"""
Prompt Manager

This module provides functionality to load and manage prompts from files and MongoDB.
"""
import os
import logging
from typing import Optional, Dict
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manager for loading and caching prompts from files and MongoDB.
    """
    
    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Initialize prompt manager.
        
        Args:
            prompts_dir: Directory containing prompt files. 
                        Defaults to aiagent/prompts/ relative to this file.
        """
        if prompts_dir is None:
            # Default to prompts directory relative to this file
            current_dir = Path(__file__).parent
            prompts_dir = str(current_dir / "prompts")
        
        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}
        self._output_format_cache: Optional[str] = None
        self._use_db_for_format = os.getenv("ANALYSIS_FORMAT_FROM_DB", "").lower() in ("true", "1", "yes")
        
        # Initialize MongoDB connection if needed
        self._mongodb_client = None
        self._mongodb_db = None
        if self._use_db_for_format:
            self._init_mongodb_connection()
    
    def load_prompt(self, filename: str, use_cache: bool = True) -> str:
        """
        Load a prompt from a file.
        
        Args:
            filename: Name of the prompt file (e.g., "analyze_recording_prompt.txt")
            use_cache: Whether to use cached version if available
        
        Returns:
            Prompt content as string
        
        Raises:
            FileNotFoundError: If the prompt file doesn't exist
        """
        # Check cache first
        if use_cache and filename in self._cache:
            return self._cache[filename]
        
        # Load from file
        prompt_path = self.prompts_dir / filename
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_path}. "
                f"Prompts directory: {self.prompts_dir}"
            )
        
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Cache it
        if use_cache:
            self._cache[filename] = content
        
        return content
    
    def format_prompt(self, filename: str, **kwargs) -> str:
        """
        Load a prompt and format it with provided variables.
        
        Args:
            filename: Name of the prompt file
            **kwargs: Variables to format into the prompt
        
        Returns:
            Formatted prompt string
        """
        prompt = self.load_prompt(filename)
        return prompt.format(**kwargs)
    
    def clear_cache(self):
        """Clear the prompt cache."""
        self._cache.clear()
    
    def list_prompts(self) -> list:
        """
        List all available prompt files.
        
        Returns:
            List of prompt filenames
        """
        if not self.prompts_dir.exists():
            return []
        
        return [
            f.name for f in self.prompts_dir.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]
    
    def _init_mongodb_connection(self):
        """Initialize MongoDB connection for loading output format."""
        try:
            connection_string = os.getenv("MONGODB_CONNECTION_STRING")
            if not connection_string:
                # Build from individual components
                host = os.getenv("MONGODB_HOST", "localhost")
                port = int(os.getenv("MONGODB_PORT", 27017))
                username = os.getenv("MONGODB_USERNAME")
                password = os.getenv("MONGODB_PASSWORD")
                auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")
                
                if username and password:
                    connection_string = f"mongodb://{username}:{password}@{host}:{port}/?authSource={auth_source}"
                else:
                    connection_string = f"mongodb://{host}:{port}/"
            
            # Load TLS settings
            tls_kwargs = {}
            tls_ca_file = os.path.expanduser(os.getenv("MONGODB_TLS_CA_FILE", ""))
            if tls_ca_file:
                tls_kwargs["tls"] = True
                tls_kwargs["tlsCAFile"] = tls_ca_file
            else:
                tls_enabled = os.getenv("MONGODB_TLS_ENABLED", "").lower() in ("true", "1", "yes")
                if tls_enabled:
                    tls_kwargs["tls"] = True
            
            tls_allow_invalid_certs = os.getenv("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", "").lower() in ("true", "1", "yes")
            if tls_allow_invalid_certs:
                tls_kwargs["tlsAllowInvalidCertificates"] = True
            
            tls_allow_invalid_hostnames = os.getenv("MONGODB_TLS_ALLOW_INVALID_HOSTNAMES", "").lower() in ("true", "1", "yes")
            if tls_allow_invalid_hostnames:
                tls_kwargs["tlsAllowInvalidHostnames"] = True
            
            self._mongodb_client = MongoClient(connection_string, **tls_kwargs)
            self._mongodb_client.admin.command('ping')
            self._mongodb_db = self._mongodb_client["computing_nodes"]
            logger.info("MongoDB connection initialized for output format loading (database: computing_nodes, collection: analysis_config)")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection for output format: {e}")
            self._mongodb_client = None
            self._mongodb_db = None
    
    def load_output_format(self, analysis_type: str = "recording", reload: bool = False, custom_config_name: Optional[str] = None) -> str:
        """
        Load output format from file or MongoDB for a specific analysis type.
        
        Args:
            analysis_type: Type of analysis (e.g., "recording", "webdata", "email")
            reload: If True, reload from source even if cached
            custom_config_name: Optional custom config name to use instead of default "{analysis_type}_analysis_format"
                              Allows overwriting for further analysis customization.
        
        Returns:
            Output format content as string
        """
        # Build cache key
        cache_key = f"{analysis_type}_{custom_config_name or 'default'}"
        
        # Check cache first (unless reload requested)
        if not reload and cache_key in self._cache:
            return self._cache[cache_key]
        
        if self._use_db_for_format:
            # Load from MongoDB
            default_config_name = f"{analysis_type}_analysis_format"
            config_name = custom_config_name or default_config_name
            output_format = self._load_output_format_from_db(custom_name=config_name)
            if output_format:
                # Cache it
                self._cache[cache_key] = output_format
                return output_format
            else:
                logger.warning(f"Failed to load output format from DB for {analysis_type}, falling back to file")
        
        # Fallback to file
        output_format = self._load_output_format_from_file(analysis_type=analysis_type)
        # Cache it
        self._cache[cache_key] = output_format
        return output_format
    
    def _load_output_format_from_db(self, custom_name: Optional[str] = None) -> Optional[str]:
        """
        Load output format from MongoDB analysis_config collection.
        
        Args:
            custom_name: Optional custom config name to use instead of default "recording_analysis_format"
                        Allows overwriting for further analysis customization.
        
        Returns:
            Output format content as string, or None if not found
        """
        if not self._mongodb_db:
            self._init_mongodb_connection()
            if not self._mongodb_db:
                return None
        
        try:
            analysis_config = self._mongodb_db.analysis_config
            
            # Use custom name if provided, otherwise use default
            config_name = custom_name or "recording_analysis_format"
            
            # Find config by name
            config = analysis_config.find_one({"name": config_name})
            
            if config and "value" in config:
                logger.info(f"Loaded output format from MongoDB analysis_config (name: {config_name})")
                return str(config["value"])
            else:
                logger.warning(f"No output format found in MongoDB analysis_config with name: {config_name}")
                return None
        except Exception as e:
            logger.error(f"Error loading output format from MongoDB: {e}")
            return None
    
    def _load_output_format_from_file(self, analysis_type: str = "recording") -> str:
        """
        Load output format from file for a specific analysis type.
        
        Args:
            analysis_type: Type of analysis (e.g., "recording", "webdata", "email")
        
        Returns:
            Output format content as string
        """
        output_format_path = self.prompts_dir / f"analyze_{analysis_type}_output.txt"
        if not output_format_path.exists():
            raise FileNotFoundError(
                f"Output format file not found: {output_format_path}. "
                f"Prompts directory: {self.prompts_dir}"
            )
        
        with open(output_format_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def format_analysis_prompt(
        self,
        analysis_type: str,
        content_data: Optional[str] = None,
        content_placeholder: str = "{transcript}",
        reload_format: bool = False,
        custom_config_name: Optional[str] = None,
        include_content: bool = True
    ) -> str:
        """
        Generic method to format analysis prompt for any analysis type.
        
        Args:
            analysis_type: Type of analysis (e.g., "recording", "webdata", "email")
            content_data: The content data to include (e.g., transcript, web content, email body)
            content_placeholder: Placeholder name in template (default: "{transcript}")
            reload_format: If True, reload output format from source before formatting
            custom_config_name: Optional custom config name to use instead of default "{analysis_type}_analysis_format"
            include_content: If True, include content_data in the prompt. If False, exclude it.
        
        Returns:
            Formatted prompt string with output format and optionally content
        """
        # Load prompt template
        prompt_template = self.load_prompt(f"analyze_{analysis_type}_prompt.txt")
        
        # Load output format (from DB or file)
        output_format = self.load_output_format(
            analysis_type=analysis_type,
            reload=reload_format,
            custom_config_name=custom_config_name
        )
        
        # Format the prompt using string formatting
        # First, handle output_format (it may contain double braces, so we use replace for safety)
        formatted = prompt_template.replace("{output_format}", output_format)
        
        # Then handle content placeholder
        if include_content and content_data:
            # Replace content placeholder with actual content
            formatted = formatted.replace(content_placeholder, content_data)
            return formatted
        else:
            # Remove the content section from the template
            # Try to find and remove content section (e.g., "Transcript:\n{transcript}\n")
            content_label = content_placeholder.replace("{", "").replace("}", "").title()
            
            # Try different patterns to remove content section
            patterns_to_remove = [
                f"{content_label}:\n{content_placeholder}",
                f"{content_label}:\n{content_placeholder}\n",
                f"\n{content_label}:\n{content_placeholder}",
                f"\n{content_label}:\n{content_placeholder}\n",
            ]
            
            for pattern in patterns_to_remove:
                if pattern in formatted:
                    formatted = formatted.replace(pattern, "").rstrip()
                    break
            else:
                # Fallback: remove just the placeholder and clean up label line
                if content_placeholder in formatted:
                    formatted = formatted.replace(content_placeholder, "").rstrip()
                    # Remove label line if it exists
                    lines = formatted.split('\n')
                    formatted = '\n'.join([
                        line for line in lines 
                        if line.strip() != f"{content_label}:"
                    ]).rstrip()
            
            return formatted + '\n'
    
    def format_analysis_recording_prompt(
        self,
        transcript: Optional[str] = None,
        reload_format: bool = False,
        custom_config_name: Optional[str] = None,
        include_transcript: bool = True
    ) -> str:
        """
        Format analysis prompt for recording/transcript analysis.
        
        Args:
            transcript: The transcript text to include (if include_transcript is True)
            reload_format: If True, reload output format from source before formatting
            custom_config_name: Optional custom config name to use instead of default "recording_analysis_format"
            include_transcript: If True, include transcript in the prompt. If False, exclude it.
        
        Returns:
            Formatted prompt string with output format and optionally transcript
        """
        return self.format_analysis_prompt(
            analysis_type="recording",
            content_data=transcript,
            content_placeholder="{transcript}",
            reload_format=reload_format,
            custom_config_name=custom_config_name,
            include_content=include_transcript
        )
    
    def format_analysis_webdata_prompt(
        self,
        web_content: Optional[str] = None,
        reload_format: bool = False,
        custom_config_name: Optional[str] = None,
        include_content: bool = True
    ) -> str:
        """
        Format analysis prompt for web data analysis.
        
        Args:
            web_content: The web content to analyze (if include_content is True)
            reload_format: If True, reload output format from source before formatting
            custom_config_name: Optional custom config name to use instead of default "webdata_analysis_format"
            include_content: If True, include web_content in the prompt. If False, exclude it.
        
        Returns:
            Formatted prompt string with output format and optionally web content
        """
        return self.format_analysis_prompt(
            analysis_type="webdata",
            content_data=web_content,
            content_placeholder="{content}",
            reload_format=reload_format,
            custom_config_name=custom_config_name,
            include_content=include_content
        )
    
    def clear_output_format_cache(self):
        """Clear the output format cache to force reload on next access."""
        # Clear all cached output formats (they're now in _cache with keys)
        # Remove cache entries that look like output format keys
        keys_to_remove = [k for k in self._cache.keys() if '_analysis_format' in k or k.endswith('_default')]
        for key in keys_to_remove:
            del self._cache[key]


# Global prompt manager instance
_default_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance."""
    global _default_prompt_manager
    if _default_prompt_manager is None:
        _default_prompt_manager = PromptManager()
    return _default_prompt_manager


def load_prompt(filename: str) -> str:
    """Convenience function to load a prompt."""
    return get_prompt_manager().load_prompt(filename)


def format_prompt(filename: str, **kwargs) -> str:
    """Convenience function to load and format a prompt."""
    return get_prompt_manager().format_prompt(filename, **kwargs)


def format_analysis_prompt(
    analysis_type: Optional[str] = None,
    content_data: Optional[str] = None,
    content_placeholder: str = "{transcript}",
    reload_format: bool = False,
    custom_config_name: Optional[str] = None,
    include_content: bool = True,
    # Backward compatibility: support old signature with transcript parameter
    transcript: Optional[str] = None,
    include_transcript: Optional[bool] = None
) -> str:
    """
    Generic convenience function to format analysis prompt for any analysis type.
    
    Supports both new signature (with analysis_type) and old signature (with transcript for backward compatibility).
    
    Args:
        analysis_type: Type of analysis (e.g., "recording", "webdata", "email"). 
                      If None and transcript is provided, defaults to "recording" for backward compatibility.
        content_data: The content data to include (e.g., transcript, web content, email body)
        content_placeholder: Placeholder name in template (default: "{transcript}")
        reload_format: If True, reload output format from source before formatting
        custom_config_name: Optional custom config name to use instead of default "{analysis_type}_analysis_format"
        include_content: If True, include content_data in the prompt. If False, exclude it.
        transcript: (Backward compatibility) The transcript text. If provided and analysis_type is None, 
                   defaults to "recording" analysis type.
        include_transcript: (Backward compatibility) If True, include transcript in the prompt. 
                           Overrides include_content if provided.
    
    Returns:
        Formatted prompt string
    """
    # Backward compatibility: handle old signature
    if transcript is not None and analysis_type is None:
        # Old signature detected - use recording analysis
        analysis_type = "recording"
        content_data = transcript
        if include_transcript is not None:
            include_content = include_transcript
    
    if analysis_type is None:
        raise ValueError("analysis_type must be provided (or use transcript for backward compatibility)")
    
    return get_prompt_manager().format_analysis_prompt(
        analysis_type=analysis_type,
        content_data=content_data,
        content_placeholder=content_placeholder,
        reload_format=reload_format,
        custom_config_name=custom_config_name,
        include_content=include_content
    )


def format_analysis_recording_prompt(
    transcript: Optional[str] = None,
    reload_format: bool = False,
    custom_config_name: Optional[str] = None,
    include_transcript: bool = True
) -> str:
    """
    Convenience function to format analysis prompt for recording/transcript analysis.
    
    Args:
        transcript: The transcript text to include (if include_transcript is True)
        reload_format: If True, reload output format from source before formatting
        custom_config_name: Optional custom config name to use instead of default "recording_analysis_format"
        include_transcript: If True, include transcript in the prompt. If False, exclude it.
    
    Returns:
        Formatted prompt string
    """
    return get_prompt_manager().format_analysis_recording_prompt(
        transcript=transcript,
        reload_format=reload_format,
        custom_config_name=custom_config_name,
        include_transcript=include_transcript
    )


def format_analysis_webdata_prompt(
    web_content: Optional[str] = None,
    reload_format: bool = False,
    custom_config_name: Optional[str] = None,
    include_content: bool = True
) -> str:
    """
    Convenience function to format analysis prompt for web data analysis.
    
    Args:
        web_content: The web content to analyze (if include_content is True)
        reload_format: If True, reload output format from source before formatting
        custom_config_name: Optional custom config name to use instead of default "webdata_analysis_format"
        include_content: If True, include web_content in the prompt. If False, exclude it.
    
    Returns:
        Formatted prompt string
    """
    return get_prompt_manager().format_analysis_webdata_prompt(
        web_content=web_content,
        reload_format=reload_format,
        custom_config_name=custom_config_name,
        include_content=include_content
    )

