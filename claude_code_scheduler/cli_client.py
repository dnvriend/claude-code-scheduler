"""HTTP client for the Claude Code Scheduler REST API.

This module provides a synchronous HTTP client for communicating with the
scheduler's debug HTTP server and REST API endpoints.

Key Components:
    - SchedulerClient: HTTP client with GET, POST, PUT, DELETE operations
    - SchedulerAPIError: Exception for API error responses
    - api_url_option: Click option decorator for API URL parameter

Dependencies:
    - httpx: HTTP client library
    - click: CLI option decorator

Related Modules:
    - cli: CLI entry point that creates SchedulerClient instances
    - cli_tasks, cli_runs, cli_jobs, cli_profiles: Use SchedulerClient
    - services.debug_server: REST API server this client communicates with

Called By:
    - cli_tasks: Task management commands
    - cli_runs: Run management commands
    - cli_jobs: Job management commands
    - cli_profiles: Profile management commands
    - cli_state: State and health commands

Example:
    >>> with SchedulerClient("http://127.0.0.1:5679") as client:
    ...     tasks = client.get("/api/tasks")
    ...     client.post("/api/tasks/123/run")

Note:
    This code was generated with assistance from AI coding tools
    and has been reviewed and tested by a human.
"""

import types
from typing import Any, Self, cast

import click
import httpx


class SchedulerAPIError(Exception):
    """Exception raised when the API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class SchedulerClient:
    """HTTP client for the Claude Code Scheduler REST API."""

    def __init__(self, base_url: str = "http://127.0.0.1:5679", timeout: float = 30.0):
        """
        Initialize the API client.

        Args:
            base_url: Base URL of the API server (default: http://127.0.0.1:5679)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """
        Handle HTTP response and parse JSON.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON response data

        Raises:
            SchedulerAPIError: If response indicates an error
        """
        try:
            response_data = response.json()
            # Cast to expected type since mypy can't infer this
            typed_response_data = cast(dict[str, Any], response_data)
        except Exception:
            if response.is_success:
                # Successful response but not JSON - return empty dict
                return {}
            else:
                # Error response and can't parse JSON
                raise SchedulerAPIError(
                    f"HTTP {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

        if response.is_success:
            return typed_response_data
        else:
            # Extract error message from response if available
            error_message = response_data.get("error", response_data.get("message", response.text))
            raise SchedulerAPIError(
                f"HTTP {response.status_code}: {error_message}",
                status_code=response.status_code,
                response_data=response_data,
            )

    def get(self, path: str) -> dict[str, Any]:
        """
        Send GET request to the API.

        Args:
            path: API endpoint path (e.g., '/api/tasks')

        Returns:
            Parsed JSON response data

        Raises:
            SchedulerAPIError: If request fails
        """
        try:
            response = self.client.get(path)
            return self._handle_response(response)
        except httpx.RequestError as e:
            raise SchedulerAPIError(f"Request failed: {e}")

    def post(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Send POST request to the API.

        Args:
            path: API endpoint path (e.g., '/api/tasks')
            data: JSON data to send in request body

        Returns:
            Parsed JSON response data

        Raises:
            SchedulerAPIError: If request fails
        """
        try:
            response = self.client.post(path, json=data)
            return self._handle_response(response)
        except httpx.RequestError as e:
            raise SchedulerAPIError(f"Request failed: {e}")

    def put(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Send PUT request to the API.

        Args:
            path: API endpoint path (e.g., '/api/tasks/123')
            data: JSON data to send in request body

        Returns:
            Parsed JSON response data

        Raises:
            SchedulerAPIError: If request fails
        """
        try:
            response = self.client.put(path, json=data)
            return self._handle_response(response)
        except httpx.RequestError as e:
            raise SchedulerAPIError(f"Request failed: {e}")

    def delete(self, path: str) -> dict[str, Any]:
        """
        Send DELETE request to the API.

        Args:
            path: API endpoint path (e.g., '/api/tasks/123')

        Returns:
            Parsed JSON response data

        Raises:
            SchedulerAPIError: If request fails
        """
        try:
            response = self.client.delete(path)
            return self._handle_response(response)
        except httpx.RequestError as e:
            raise SchedulerAPIError(f"Request failed: {e}")

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()


# Click option for API URL
api_url_option = click.option(
    "--api-url",
    default="http://127.0.0.1:5679",
    help="Base URL of the Claude Code Scheduler API (default: http://127.0.0.1:5679)",
)
