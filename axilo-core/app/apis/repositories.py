"""
API Router for Repository Search endpoints.
Uses FastAPI dependency injection for clean, testable code.
"""

import logging
from fastapi import APIRouter, Query, Path, HTTPException, status, Depends

from app.models import (
    RepositorySearchRequest,
    RepositorySearchResponse,
    ErrorResponse,
)
from app.services import RepoSearchService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/repositories",
    tags=["repositories"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        400: {"model": ErrorResponse, "description": "Bad request"},
    },
)


# Dependency Injection
def get_repo_search_service() -> RepoSearchService:
    """
    Dependency injection function for RepoSearchService.

    Returns:
        RepoSearchService: Service instance for repository operations.
    """
    return RepoSearchService()


@router.post(
    "/search",
    response_model=RepositorySearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search repositories",
    description="Search for repositories on GitHub with flexible filters",
)
async def search_repositories(
    request: RepositorySearchRequest,
    service: RepoSearchService = Depends(get_repo_search_service),
) -> RepositorySearchResponse:
    """
    Search for repositories based on query and filters.

    **Query Parameters:**
    - `query`: Search query string (required)
    - `language`: Programming language filter (optional)
    - `min_stars`: Minimum number of stars (default: 0)
    - `sort`: Sort by 'stars', 'forks', 'updated', or 'match' (default: 'stars')
    - `order`: 'asc' or 'desc' (default: 'desc')
    - `page`: Page number for pagination (default: 1)
    - `per_page`: Results per page, max 100 (default: 20)

    **Example Request:**
    ```json
    {
        "query": "web framework",
        "language": "python",
        "min_stars": 100,
        "sort": "stars",
        "order": "desc",
        "page": 1,
        "per_page": 20
    }
    ```

    **Returns:**
    - `total_count`: Total matching repositories
    - `page`: Current page number
    - `per_page`: Results per page
    - `items`: List of repositories with details

    **Errors:**
    - 400: Bad request (invalid parameters)
    - 500: GitHub API error
    """
    try:
        result = service.search_repositories(
            query=request.query,
            language=request.language,
            min_stars=request.min_stars,
            sort=request.sort,
            order=request.order,
            page=request.page,
            per_page=request.per_page,
        )
        return result

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error searching repositories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search repositories. Please try again later.",
        )


@router.get(
    "/{owner}/{repo}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get repository details",
    description="Fetch detailed information for a specific repository",
)
async def get_repository(
    owner: str = Path(..., description="Repository owner username"),
    repo: str = Path(..., description="Repository name"),
    service: RepoSearchService = Depends(get_repo_search_service),
) -> dict:
    """
    Get detailed information for a specific repository.

    **Path Parameters:**
    - `owner`: Repository owner username
    - `repo`: Repository name

    **Example:**
    ```
    GET /api/v1/repositories/kubernetes/kubernetes
    ```

    **Returns:**
    Repository object with all available details including stars, forks, language, etc.

    **Errors:**
    - 404: Repository not found
    - 500: GitHub API error
    """
    try:
        repo_info = service.get_repository_details(owner, repo)
        return repo_info.model_dump(by_alias=True)

    except Exception as e:
        logger.error(
            f"Error fetching repository {owner}/{repo}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch repository details. Please try again later.",
        )


@router.get(
    "/users/{username}",
    response_model=list,
    status_code=status.HTTP_200_OK,
    summary="List user repositories",
    description="List all repositories for a specific GitHub user",
)
async def list_repositories(
    username: str = Path(..., description="The GitHub username"),
    sort: str = Query(
        "updated", description="Sort by: created, updated, pushed, name"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    service: RepoSearchService = Depends(get_repo_search_service),
) -> list:
    """
    List repositories for a specific user.

    **Query Parameters:**
    - `username`: GitHub username
    - `sort`: Sort by 'created', 'updated', 'pushed', or 'name'
    - `order`: 'asc' or 'desc'
    - `page`: Page number (default: 1)
    - `per_page`: Results per page (default: 20, max: 100)

    **Example:**
    ```
    GET /api/v1/repositories/users/torvalds?sort=updated&order=desc&per_page=10
    ```

    **Returns:**
    List of repository objects for the user.

    **Errors:**
    - 404: User not found
    - 500: GitHub API error
    """
    try:
        repos = service.list_user_repositories(
            username=username,
            sort=sort,
            order=order,
            page=page,
            per_page=per_page,
        )
        return [repo.model_dump(by_alias=True) for repo in repos]

    except Exception as e:
        logger.error(
            f"Error listing repositories for user {username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list user repositories. Please try again later.",
        )


@router.get(
    "/health",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Repository service health check",
)
async def repository_health_check(
    service: RepoSearchService = Depends(get_repo_search_service),
) -> dict:
    """
    Health check endpoint for the repository search service.

    **Returns:**
    - `status`: Service status (ok/error)
    - `service`: Service name
    """
    try:
        # Simple check to verify service is initialized
        if service and service.github_client:
            return {"status": "ok", "service": "repository_search"}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Repository service is not properly initialized",
            )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Repository service is unavailable",
        )
