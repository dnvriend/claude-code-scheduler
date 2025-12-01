"""Profile data model for Claude Code Scheduler.

This module contains the Profile and EnvVar dataclasses for environment
variable configuration and management.

Key Components:
    - Profile: Named collection of environment variables
    - EnvVar: Environment variable with configurable source

Dependencies:
    - dataclasses: Python dataclass decorators
    - datetime: Timestamp tracking
    - uuid: UUID generation
    - models.enums: EnvVarSource enum

Related Modules:
    - models.task: Tasks reference profiles for environment
    - models.job: Jobs can override task profiles
    - services.env_resolver: Resolves EnvVar values from sources
    - storage.config_storage: Persists profiles to JSON
    - ui.dialogs.profile_editor_dialog: Profile editing UI

Collaborators:
    - EnvVarResolver: Resolves EnvVar values based on source type
    - Task: Tasks reference profiles by ID
    - Job: Jobs can specify a profile override

Example:
    >>> from claude_code_scheduler.models.profile import Profile, EnvVar
    >>> from claude_code_scheduler.models.enums import EnvVarSource
    >>> env = EnvVar(name="AWS_REGION", source=EnvVarSource.STATIC, value="eu-central-1")
    >>> profile = Profile(name="Production", env_vars=[env])

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from claude_code_scheduler.models.enums import EnvVarSource


@dataclass
class EnvVar:
    """An environment variable with configurable source."""

    name: str  # e.g., "AWS_REGION"
    source: EnvVarSource  # How to resolve the value
    value: str  # Source-specific reference string
    config: dict[str, Any] | None = None  # Additional config (e.g., AWS region, profile)

    # Examples:
    # - Static: value="eu-central-1"
    # - Environment: value="HOME"
    # - Keychain: value="GLM_AUTH_TOKEN/production" (service/account)
    # - AWS Secrets Manager: value="prod/api/claude-key",
    #   config={"region": "eu-central-1", "profile": "prod"}
    # - AWS SSM: value="/prod/claude/api-key",
    #   config={"region": "eu-central-1", "profile": "prod", "decrypt": true}
    # - Command: value="aws configure get region"

    def to_dict(self) -> dict[str, Any]:
        """Convert env var to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "source": self.source.value,
            "value": self.value,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnvVar:
        """Create env var from dictionary."""
        return cls(
            name=data["name"],
            source=EnvVarSource(data["source"]),
            value=data["value"],
            config=data.get("config"),
        )


@dataclass
class Profile:
    """A named profile with environment variable configuration."""

    id: UUID = field(default_factory=uuid4)
    name: str = "Untitled Profile"
    description: str = ""
    env_vars: list[EnvVar] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "env_vars": [ev.to_dict() for ev in self.env_vars],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        """Create profile from dictionary."""
        return cls(
            id=UUID(data["id"]),
            name=data.get("name", "Untitled Profile"),
            description=data.get("description", ""),
            env_vars=[EnvVar.from_dict(ev) for ev in data.get("env_vars", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
