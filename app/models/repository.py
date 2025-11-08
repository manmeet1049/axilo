"""
Pydantic models for Repository-related API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class RepositorySearchRequest(BaseModel):
    """
    Request model for searching repositories.
    """
    query: str = Field(..., description="Search query string (e.g., 'web framework')")
    language: Optional[str] = Field(None, description="Programming language filter (e.g., 'python')")
    min_stars: int = Field(0, ge=0, description="Minimum number of stars")
    sort: str = Field("stars", description="Sort by 'stars', 'forks', 'updated', or 'match'")
    order: str = Field("desc", description="Sort order 'asc' or 'desc'")
    page: int = Field(1, ge=1, description="Page number for pagination")
    per_page: Optional[int] = Field(None, description="Results per page (max 100)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "web framework",
                "language": "python",
                "min_stars": 100,
                "sort": "stars",
                "order": "desc",
                "page": 1,
                "per_page": 20
            }
        }


class RepositoryInfo(BaseModel):
    """
    Repository information model.
    """
    id: int = Field(..., description="Repository ID")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/repo)")
    description: Optional[str] = Field(None, description="Repository description")
    url: str = Field(..., description="Repository URL")
    language: Optional[str] = Field(None, description="Primary programming language")
    stars: int = Field(..., alias="stargazers_count", description="Number of stars")
    forks: int = Field(..., alias="forks_count", description="Number of forks")
    open_issues: int = Field(..., alias="open_issues_count", description="Number of open issues")
    topics: List[str] = Field(default_factory=list, description="Repository topics/tags")

    class Config:
        populate_by_name = True


class RepositorySearchResponse(BaseModel):
    """
    Response model for repository search results.
    """
    total_count: int = Field(..., description="Total number of matching repositories")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Results per page")
    items: List[RepositoryInfo] = Field(..., description="List of repositories")

    class Config:
        json_schema_extra = {
            "example": {
                "total_count": 150,
                "page": 1,
                "per_page": 20,
                "items": []
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    """
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for debugging")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Failed to search repositories",
                "error_code": "GITHUB_API_ERROR"
            }
        }
