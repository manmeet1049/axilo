"""
GitHub REST API Client - No SDK
Provides a class-based interface to interact with GitHub repositories without using PyGithub SDK.
"""

import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin


class GitHubClient:
    """
    A class-based GitHub REST API client for fetching repository data with flexible filters.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None, per_page: int = 30):
        """
        Initialize the GitHub client.

        Args:
            token: GitHub personal access token for authenticated requests (optional).
            per_page: Number of results per page (default: 30, max: 100).
        """
        self.token = token
        self.per_page = min(per_page, 100)  
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a GET request to the GitHub API.

        Args:
            endpoint: API endpoint (e.g., '/search/repositories').
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            requests.exceptions.HTTPError: If the request fails.
        """
        url = urljoin(self.BASE_URL, endpoint)
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def search_repositories(
        self,
        query: str,
        language: Optional[str] = None,
        sort: str = "stars",
        order: str = "desc",
        min_stars: int = 0,
        per_page: Optional[int] = None,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Search for repositories based on flexible filters.

        Args:
            query: Search query string (e.g., 'python web framework').
            language: Programming language filter (e.g., 'python', 'javascript').
            sort: Sort by 'stars', 'forks', 'updated', or 'match' (default: 'stars').
            order: Sort order 'asc' or 'desc' (default: 'desc').
            min_stars: Minimum number of stars (default: 0).
            per_page: Number of results per page (uses instance default if None).
            page: Page number (default: 1).

        Returns:
            Dictionary with 'items' (list of repos) and 'total_count'.

        """
        search_query = query
        if language:
            search_query += f" language:{language}"
        search_query += f" stars:>={min_stars}"

        params = {
            "q": search_query,
            "sort": sort,
            "order": order,
            "per_page": per_page or self.per_page,
            "page": page,
        }

        return self._get("/search/repositories", params)

    def list_user_repositories(
        self,
        username: str,
        repo_type: str = "all",
        sort: str = "updated",
        order: str = "desc",
        per_page: Optional[int] = None,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        List repositories for a specific user.

        Args:
            username: GitHub username.
            repo_type: 'all', 'owner', 'member', or 'public' (default: 'all').
            sort: Sort by 'created', 'updated', 'pushed', 'name' (default: 'updated').
            order: Sort order 'asc' or 'desc' (default: 'desc').
            per_page: Number of results per page (uses instance default if None).
            page: Page number (default: 1).

        Returns:
            List of repository dictionaries.
        """
        endpoint = f"/users/{username}/repos"
        params = {
            "type": repo_type,
            "sort": sort,
            "order": order,
            "per_page": per_page or self.per_page,
            "page": page,
        }

        return self._get(endpoint, params)

    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Fetch details for a specific repository.

        Args:
            owner: Repository owner username.
            repo: Repository name.

        Returns:
            Repository data dictionary.
        """
        endpoint = f"/repos/{owner}/{repo}"
        return self._get(endpoint)

    def list_repository_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: Optional[int] = None,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        List issues for a repository.

        Args:
            owner: Repository owner username.
            repo: Repository name.
            state: Issue state 'open', 'closed', or 'all' (default: 'open').
            per_page: Number of results per page (uses instance default if None).
            page: Page number (default: 1).

        Returns:
            List of issue dictionaries.
        """
        endpoint = f"/repos/{owner}/{repo}/issues"
        params = {
            "state": state,
            "per_page": per_page or self.per_page,
            "page": page,
        }

        return self._get(endpoint, params)

    def list_repository_contributors(
        self,
        owner: str,
        repo: str,
        per_page: Optional[int] = None,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        List contributors for a repository.

        Args:
            owner: Repository owner username.
            repo: Repository name.
            per_page: Number of results per page (uses instance default if None).
            page: Page number (default: 1).

        Returns:
            List of contributor dictionaries.
        """
        endpoint = f"/repos/{owner}/{repo}/contributors"
        params = {
            "per_page": per_page or self.per_page,
            "page": page,
        }

        return self._get(endpoint, params)

    def get_user(self, username: str) -> Dict[str, Any]:
        """
        Fetch user profile information.
 
        Args:
            username: GitHub username.

        Returns:
            User data dictionary.
        """
        endpoint = f"/users/{username}"
        return self._get(endpoint)
