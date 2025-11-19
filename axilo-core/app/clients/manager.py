"""
Client Manager - Centralized initialization and management of all API clients.
This module provides a singleton-like manager that initializes and yields clients
for use throughout the application.
"""

from typing import Optional

from app.settings import settings
from app.clients.githubCl import GitHubClient


class ClientManager:
    """
    Centralized client manager for initializing and managing all API clients.

    Provides singleton access to initialized clients across the application.
    Supports lazy initialization and environment-based configuration.

    Example:
        >>> manager = ClientManager()
        >>> github_client = manager.get_github_client()
        >>> repos = github_client.search_repositories(query="python", language="python")
    """

    _instance: Optional["ClientManager"] = None
    _github_client: Optional[GitHubClient] = None

    def __new__(cls) -> "ClientManager":
        """Ensure singleton pattern - only one instance of ClientManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the client manager with configuration from environment."""
        # Only initialize once
        print("Initializing ClientManager...")
        if self._github_client is None:
            self._initialize_github_client()

    @staticmethod
    def _initialize_github_client() -> GitHubClient:
        """
        Initialize the GitHub client with token from pydantic settings.

        Uses GITHUB_TOKEN from the Settings configuration.
        Falls back to unauthenticated requests if token is not available.

        Returns:
            Initialized GitHubClient instance.
        """
        token = settings.github_token if settings.github_token else None
        per_page = 30

        client = GitHubClient(token=token, per_page=per_page)
        return client

    def get_github_client(self) -> GitHubClient:
        """
        Yield the GitHub client for use in the application.

        Returns:
            GitHubClient: Singleton instance of the GitHub client.

        Example:
            >>> manager = ClientManager()
            >>> client = manager.get_github_client()
            >>> results = client.search_repositories(query="web framework", language="python")
        """
        if self._github_client is None:
            self._github_client = self._initialize_github_client()
        return self._github_client

    def refresh_github_client(self, token: Optional[str] = None, per_page: int = 30) -> GitHubClient:
        """
        Refresh the GitHub client with new configuration.

        Useful for testing or switching authentication tokens.

        Args:
            token: GitHub personal access token (if None, reads from settings).
            per_page: Number of results per page (default: 30).

        Returns:
            New GitHubClient instance.

        Example:
            >>> manager = ClientManager()
            >>> manager.refresh_github_client(token="ghp_newtoken123")
        """
        final_token = token if token else settings.github_token
        self._github_client = GitHubClient(
            token=final_token, per_page=per_page)
        return self._github_client

    def reset(self) -> None:
        """
        Reset the client manager (useful for testing).
        Clears all initialized clients.
        """
        self._github_client = None


# Global convenience instance
_client_manager = ClientManager()


def get_client_manager() -> ClientManager:
    """
    Get the global ClientManager instance.

    Returns:
        ClientManager: Singleton instance.

    Example:
        >>> from app.clients.manager import get_client_manager
        >>> manager = get_client_manager()
        >>> github_client = manager.get_github_client()
    """
    return _client_manager
