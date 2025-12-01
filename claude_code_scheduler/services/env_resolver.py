"""Environment Variable Resolver for Claude Code Scheduler.

This module resolves environment variables from various sources including
static values, existing env vars, macOS Keychain, AWS Secrets Manager,
AWS SSM Parameter Store, and shell commands.

Key Components:
    - EnvVarResolver: Main class for resolving environment variables

Dependencies:
    - subprocess: Shell command execution
    - boto3: AWS SDK (lazy loaded for SSM/Secrets Manager)
    - models.profile: Profile and EnvVar data models
    - models.enums: EnvVarSource enum

Related Modules:
    - models.profile: EnvVar and Profile definitions
    - services.executor: Uses resolved env vars for task execution

Calls:
    - subprocess.run: Execute shell commands
    - security CLI: macOS Keychain lookups
    - boto3.client: AWS SSM and Secrets Manager

Called By:
    - TaskExecutor.execute: Resolve profile env vars before execution

Example:
    >>> from claude_code_scheduler.services.env_resolver import EnvVarResolver
    >>> resolver = EnvVarResolver()
    >>> env_dict = resolver.resolve_profile(profile)

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import os
import subprocess  # nosec B404 - required for command execution
from typing import Any

from claude_code_scheduler.logging_config import get_logger
from claude_code_scheduler.models.enums import EnvVarSource
from claude_code_scheduler.models.profile import EnvVar, Profile

logger = get_logger(__name__)


class EnvVarResolver:
    """Resolves environment variables from various sources."""

    def resolve_profile(self, profile: Profile) -> dict[str, str]:
        """Resolve all environment variables in a profile.

        Args:
            profile: The profile containing env vars to resolve.

        Returns:
            Dictionary of resolved environment variable name to value.
        """
        resolved: dict[str, str] = {}

        for env_var in profile.env_vars:
            try:
                value = self.resolve_env_var(env_var)
                if value is not None:
                    resolved[env_var.name] = value
                else:
                    logger.warning(
                        "Could not resolve env var %s from %s",
                        env_var.name,
                        env_var.source.value,
                    )
            except Exception as e:
                logger.error("Failed to resolve env var %s: %s", env_var.name, e)

        return resolved

    # Sentinel value to indicate an env var should be unset/deleted
    UNSET_SENTINEL = "__UNSET__"

    def resolve_env_var(self, env_var: EnvVar) -> str | None:
        """Resolve a single environment variable.

        Args:
            env_var: The environment variable to resolve.

        Returns:
            Resolved value, UNSET_SENTINEL for unset vars, or None if resolution failed.
        """
        source = env_var.source

        if source == EnvVarSource.STATIC:
            return env_var.value

        elif source == EnvVarSource.ENVIRONMENT:
            return self._resolve_from_environment(env_var.value)

        elif source == EnvVarSource.KEYCHAIN:
            return self._resolve_from_keychain(env_var.value, env_var.config)

        elif source == EnvVarSource.AWS_SECRETS_MANAGER:
            return self._resolve_from_aws_secrets(env_var.value, env_var.config)

        elif source == EnvVarSource.AWS_SSM:
            return self._resolve_from_aws_ssm(env_var.value, env_var.config)

        elif source == EnvVarSource.COMMAND:
            return self._resolve_from_command(env_var.value)

        elif source == EnvVarSource.UNSET:
            return self.UNSET_SENTINEL

        else:
            logger.warning("Unknown env var source: %s", source)
            return None

    def _resolve_from_environment(self, var_name: str) -> str | None:
        """Get value from existing environment variable.

        Args:
            var_name: Name of the environment variable to read.

        Returns:
            Environment variable value or None if not set.
        """
        return os.environ.get(var_name)

    def _resolve_from_keychain(
        self, service_account: str, config: dict[str, Any] | None
    ) -> str | None:
        """Get value from macOS Keychain.

        Args:
            service_account: Format "service/account" or just "service".
            config: Optional config (unused currently).

        Returns:
            Password from keychain or None if not found.
        """
        parts = service_account.split("/", 1)
        service = parts[0]
        account = parts[1] if len(parts) > 1 else service

        try:
            result = subprocess.run(  # nosec B603, B607 - security command
                [
                    "security",
                    "find-generic-password",
                    "-s",
                    service,
                    "-a",
                    account,
                    "-w",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning("Keychain lookup failed for %s/%s", service, account)
                return None

        except subprocess.TimeoutExpired:
            logger.error("Keychain lookup timed out")
            return None
        except FileNotFoundError:
            logger.error("security command not found (not on macOS?)")
            return None

    def _resolve_from_aws_secrets(
        self, secret_name: str, config: dict[str, Any] | None
    ) -> str | None:
        """Get value from AWS Secrets Manager.

        Args:
            secret_name: Name or ARN of the secret.
            config: Optional config with region, profile.

        Returns:
            Secret value or None if not found.
        """
        config = config or {}
        region = config.get("region", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        profile = config.get("profile")

        cmd = [
            "aws",
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            secret_name,
            "--region",
            region,
            "--query",
            "SecretString",
            "--output",
            "text",
        ]

        if profile:
            cmd.extend(["--profile", profile])

        try:
            result = subprocess.run(  # nosec B603, B607 - aws cli
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning("AWS Secrets Manager lookup failed: %s", result.stderr)
                return None

        except subprocess.TimeoutExpired:
            logger.error("AWS Secrets Manager lookup timed out")
            return None
        except FileNotFoundError:
            logger.error("aws CLI not found")
            return None

    def _resolve_from_aws_ssm(
        self, parameter_path: str, config: dict[str, Any] | None
    ) -> str | None:
        """Get value from AWS Systems Manager Parameter Store.

        Args:
            parameter_path: Parameter path (e.g., /prod/api/key).
            config: Optional config with region, profile, decrypt.

        Returns:
            Parameter value or None if not found.
        """
        config = config or {}
        region = config.get("region", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        profile = config.get("profile")
        decrypt = config.get("decrypt", True)

        cmd = [
            "aws",
            "ssm",
            "get-parameter",
            "--name",
            parameter_path,
            "--region",
            region,
            "--query",
            "Parameter.Value",
            "--output",
            "text",
        ]

        if decrypt:
            cmd.append("--with-decryption")

        if profile:
            cmd.extend(["--profile", profile])

        try:
            result = subprocess.run(  # nosec B603, B607 - aws cli
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning("AWS SSM lookup failed: %s", result.stderr)
                return None

        except subprocess.TimeoutExpired:
            logger.error("AWS SSM lookup timed out")
            return None
        except FileNotFoundError:
            logger.error("aws CLI not found")
            return None

    def _resolve_from_command(self, command: str) -> str | None:
        """Get value by executing a shell command.

        Args:
            command: Shell command to execute.

        Returns:
            Command stdout or None if failed.
        """
        try:
            result = subprocess.run(  # nosec B602 - shell command from user config
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning("Command failed: %s -> %s", command, result.stderr)
                return None

        except subprocess.TimeoutExpired:
            logger.error("Command timed out: %s", command)
            return None
