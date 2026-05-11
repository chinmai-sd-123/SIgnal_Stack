"""
Secrets Manager.

Provides secure access to sensitive configuration:
- API keys (GitHub, OpenAI)
- Database credentials
- Redis connection strings
- JWT secrets

Features:
- Environment variable loading
- Validation of required secrets
- Masking in logs
- Optional secrets file support
"""

import json
import logging
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class SecretConfig:
    """Configuration for a secret."""
    name: str
    env_var: str
    required: bool = True
    default: Optional[str] = None
    masked: bool = True
    description: str = ""


# Define all secrets used by the application
SECRET_DEFINITIONS: List[SecretConfig] = [
    SecretConfig(
        name="github_token",
        env_var="GITHUB_TOKEN",
        required=True,
        description="GitHub Personal Access Token for API access"
    ),
    SecretConfig(
        name="openai_api_key",
        env_var="OPENAI_API_KEY",
        required=False,
        description="OpenAI API key for LLM summarization"
    ),
    SecretConfig(
        name="openai_model",
        env_var="OPENAI_MODEL",
        required=False,
        default="gpt-5.4-mini",
        masked=False,
        description="OpenAI model used for LLM summarization and evaluation"
    ),
    SecretConfig(
        name="database_url",
        env_var="DATABASE_URL",
        required=False,
        default="sqlite:///./signalstack.db",
        description="Database connection URL"
    ),
    SecretConfig(
        name="redis_url",
        env_var="REDIS_URL",
        required=False,
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching"
    ),
    SecretConfig(
        name="jwt_secret",
        env_var="JWT_SECRET",
        required=False,
        default="dev-secret-change-in-production",
        description="Secret key for JWT token signing"
    ),
    SecretConfig(
        name="api_key",
        env_var="SIGNALSTACK_API_KEY",
        required=False,
        description="API key for external plugin authentication"
    ),
]


class SecretsManager:
    """
    Manage application secrets with validation and secure access.
    """
    
    def __init__(self, env_file: str = None):
        self._secrets: Dict[str, str] = {}
        self._loaded = False
        self.env_file = env_file
        
    def load(self, env_file: str = None) -> "SecretsManager":
        """
        Load secrets from environment variables and optional .env file.
        """
        # Load from .env file if specified
        env_path = env_file or self.env_file
        if env_path:
            self._load_env_file(env_path)
        
        # Load secrets from environment
        for config in SECRET_DEFINITIONS:
            value = os.environ.get(config.env_var)
            
            if value:
                self._secrets[config.name] = value
            elif config.default:
                self._secrets[config.name] = config.default
        
        self._loaded = True
        return self
    
    def _load_env_file(self, path: str):
        """Load variables from a .env file."""
        env_path = Path(path)
        if not env_path.exists():
            logger.warning(".env file not found at %s", path)
            return
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
    
    def get(self, name: str, default: str = None) -> Optional[str]:
        """Get a secret value by name."""
        if not self._loaded:
            self.load()
        
        return self._secrets.get(name, default)
    
    def require(self, name: str) -> str:
        """Get a required secret, raising error if not found."""
        value = self.get(name)
        if value is None:
            config = next((c for c in SECRET_DEFINITIONS if c.name == name), None)
            env_var = config.env_var if config else name.upper()
            raise ValueError(f"Required secret '{name}' not found. Set {env_var} environment variable.")
        return value
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate all required secrets are present.
        
        Returns dict with validation status.
        """
        if not self._loaded:
            self.load()
        
        missing = []
        present = []
        
        for config in SECRET_DEFINITIONS:
            if config.name in self._secrets:
                present.append(config.name)
            elif config.required:
                missing.append({
                    "name": config.name,
                    "env_var": config.env_var,
                    "description": config.description
                })
        
        return {
            "valid": len(missing) == 0,
            "present": present,
            "missing": missing
        }
    
    def mask(self, value: str, visible_chars: int = 4) -> str:
        """Mask a secret value for logging."""
        if not value or len(value) <= visible_chars:
            return "***"
        return value[:visible_chars] + "*" * (len(value) - visible_chars)
    
    def get_masked(self, name: str) -> str:
        """Get a masked version of a secret for logging."""
        value = self.get(name)
        if value:
            return self.mask(value)
        return "(not set)"
    
    def summary(self) -> str:
        """Get a summary of secrets status (for startup logging)."""
        if not self._loaded:
            self.load()
        
        lines = ["Secrets Status:"]
        for config in SECRET_DEFINITIONS:
            status = "[OK]" if config.name in self._secrets else "[X]"
            masked = self.get_masked(config.name)
            lines.append(f"  {status} {config.name}: {masked}")
        
        return "\n".join(lines)
    
    # Convenience properties for common secrets
    
    @property
    def github_token(self) -> Optional[str]:
        return self.get("github_token")
    
    @property
    def openai_api_key(self) -> Optional[str]:
        return self.get("openai_api_key")

    @property
    def openai_model(self) -> str:
        return self.get("openai_model", "gpt-5.4-mini")
    
    @property
    def database_url(self) -> str:
        return self.get("database_url", "sqlite:///./signalstack.db")
    
    @property
    def redis_url(self) -> str:
        return self.get("redis_url", "redis://localhost:6379/0")
    
    @property
    def jwt_secret(self) -> str:
        return self.get("jwt_secret", "dev-secret-change-in-production")


# Global secrets instance
secrets = SecretsManager()


def init_secrets(env_file: str = None) -> SecretsManager:
    """Initialize secrets from environment (call from main.py startup)."""
    secrets.load(env_file)
    logger.info(secrets.summary())
    
    validation = secrets.validate()
    if not validation["valid"]:
        logger.warning("Missing required secrets:")
        for m in validation["missing"]:
            logger.warning("Set %s: %s", m["env_var"], m["description"])
    
    return secrets
