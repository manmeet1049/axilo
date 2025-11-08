"""
Repository Search Service - Business logic for searching and managing repositories.
"""

import logging
from typing import Dict, List, Any
import requests

from app.clients import get_client_manager
from app.models import RepositoryInfo, RepositorySearchResponse

logger = logging.getLogger(__name__)


class RepoSearchService:
    """
    Service for searching repositories via GitHub API.
    Handles business logic, error handling, and response formatting.
    """

    def __init__(self):
        """Initialize the service with the GitHub client."""
        self.client_manager = get_client_manager()
        self.github_client = self.client_manager.get_github_client()

    def search_repositories(
        self,
        query: str,
        language: str | None = None,
        min_stars: int = 0,
        sort: str = "stars",
        order: str = "desc",
        page: int = 1,
        per_page: int | None = None,
    ) -> RepositorySearchResponse:
        """
        Search for repositories based on filters.

        Args:
            query: Search query string.
            language: Programming language filter (optional).
            min_stars: Minimum number of stars.
            sort: Sort field ('stars', 'forks', 'updated', 'match').
            order: Sort order ('asc', 'desc').
            page: Page number for pagination.
            per_page: Results per page (max 100).

        Returns:
            RepositorySearchResponse with formatted results.

        Raises:
            ValueError: If query is empty or parameters are invalid.
            Exception: If GitHub API call fails.
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                raise ValueError("Search query cannot be empty")

            per_page = per_page or 20
            if per_page > 100:
                per_page = 100
            if per_page < 1:
                per_page = 1

            if page < 1:
                page = 1

            logger.info(
                f"Searching repositories: query='{query}', language={language}, "
                f"min_stars={min_stars}, sort={sort}, page={page}"
            )

            raw_results = self.github_client.search_repositories(
                query=query,
                language=language,
                sort=sort,
                order=order,
                min_stars=min_stars,
                per_page=per_page,
                page=page,
            )

            items = [
                self._transform_repo(repo) for repo in raw_results.get("items", [])
            ]

            response = RepositorySearchResponse(
                total_count=raw_results.get("total_count", 0),
                page=page,
                per_page=per_page,
                items=items,
            )

            logger.info(
                f"Search completed: found {response.total_count} repositories")
            return response

        except ValueError as e:
            logger.warning(f"Validation error in search: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            raise Exception(f"Failed to search repositories: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error in search_repositories: {e}", exc_info=True)
            raise

    def get_repository_details(self, owner: str, repo: str) -> RepositoryInfo:
        """
        Get detailed information for a specific repository.

        Args:
            owner: Repository owner username.
            repo: Repository name.

        Returns:
            RepositoryInfo with detailed information.

        Raises:
            Exception: If GitHub API call fails.
        """
        try:
            logger.info(f"Fetching repository details: {owner}/{repo}")

            raw_repo = self.github_client.get_repository(owner, repo)
            repo_info = self._transform_repo(raw_repo)

            logger.info(f"Successfully fetched repository: {owner}/{repo}")
            return repo_info

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            raise Exception(f"Failed to fetch repository details: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error in get_repository_details: {e}", exc_info=True
            )
            raise

    def list_user_repositories(
        self,
        username: str,
        sort: str = "updated",
        order: str = "desc",
        page: int = 1,
        per_page: int | None = None,
    ) -> List[RepositoryInfo]:
        """
        List repositories for a specific user.

        Args:
            username: GitHub username.
            sort: Sort field ('created', 'updated', 'pushed', 'name').
            order: Sort order ('asc', 'desc').
            page: Page number for pagination.
            per_page: Results per page.

        Returns:
            List of RepositoryInfo objects.

        Raises:
            Exception: If GitHub API call fails.
        """
        try:
            per_page = per_page or 20
            if per_page > 100:
                per_page = 100

            logger.info(f"Fetching repositories for user: {username}")

            raw_repos = self.github_client.list_user_repositories(
                username=username,
                sort=sort,
                order=order,
                page=page,
                per_page=per_page,
            )

            repos = [self._transform_repo(repo) for repo in raw_repos]

            logger.info(
                f"Successfully fetched {len(repos)} repositories for {username}")
            return repos

        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API error: {e}")
            raise Exception(f"Failed to list user repositories: {str(e)}")
        except Exception as e:
            logger.error(
                f"Unexpected error in list_user_repositories: {e}", exc_info=True)
            raise

    @staticmethod
    def _transform_repo(raw_repo: Dict[str, Any]) -> RepositoryInfo:
        """
        Transform raw GitHub API response to RepositoryInfo model.

        Args:
            raw_repo: Raw repository data from GitHub API.

        Returns:
            RepositoryInfo object.
        """
        return RepositoryInfo(
            id=raw_repo.get("id"),
            name=raw_repo.get("name"),
            full_name=raw_repo.get("full_name"),
            description=raw_repo.get("description"),
            url=raw_repo.get("html_url"),
            language=raw_repo.get("language"),
            stargazers_count=raw_repo.get("stargazers_count", 0),
            forks_count=raw_repo.get("forks_count", 0),
            open_issues_count=raw_repo.get("open_issues_count", 0),
            topics=raw_repo.get("topics", []),
        )
