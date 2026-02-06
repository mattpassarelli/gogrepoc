"""Pydantic models for API request and response validation.

This module defines all the request and response schemas used by the FastAPI endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# Authentication schemas
class LoginRequest(BaseModel):
    """Request model for login endpoint."""
    
    username: str = Field(..., min_length=1, description="GOG username or email")
    password: str = Field(..., min_length=1, description="GOG password")
    two_factor_code: Optional[str] = Field(None, description="Two-factor authentication code")


class LoginResponse(BaseModel):
    """Response model for login endpoint."""
    
    success: bool = Field(..., description="Whether login was successful")
    message: str = Field(..., description="Status message")
    authenticated: bool = Field(..., description="Whether user is now authenticated")


class AuthStatusResponse(BaseModel):
    """Response model for authentication status check."""
    
    authenticated: bool = Field(..., description="Whether user is authenticated")
    user_id: Optional[str] = Field(None, description="GOG user ID if authenticated")


# Manifest schemas
class DownloadSchema(BaseModel):
    """Schema for a downloadable file."""
    
    name: str
    href: str
    size: int
    md5: Optional[str]
    os_type: str
    lang: str
    version: Optional[str]
    desc: str
    updated: Optional[datetime]
    verified: bool = False


class ExtraSchema(BaseModel):
    """Schema for an extra file."""
    
    name: str
    href: str
    size: int
    desc: str
    updated: Optional[datetime]


class GameSchema(BaseModel):
    """Schema for a game with all its content."""
    
    id: int
    title: str
    folder_name: str
    long_title: str
    downloads: list[DownloadSchema] = Field(default_factory=list)
    galaxy_downloads: list[DownloadSchema] = Field(default_factory=list)
    shared_downloads: list[DownloadSchema] = Field(default_factory=list)
    extras: list[ExtraSchema] = Field(default_factory=list)
    serials: dict[str, str] = Field(default_factory=dict)
    changelog: Optional[str] = None
    image_url: str = ""
    bg_url: str = ""
    store_url: str = ""
    has_updates: bool = False


class ManifestResponse(BaseModel):
    """Response model for manifest endpoint."""
    
    games: list[GameSchema] = Field(..., description="List of games in manifest")
    total_count: int = Field(..., description="Total number of games")


# Update schemas
class UpdateRequest(BaseModel):
    """Request model for update endpoint."""
    
    os_types: list[str] = Field(
        default_factory=lambda: ["windows", "linux", "mac"],
        description="Operating systems to include"
    )
    languages: list[str] = Field(
        default_factory=lambda: ["en"],
        description="Languages to include"
    )
    game_ids: Optional[list[int]] = Field(
        None,
        description="Specific game IDs to update (None for all games)"
    )
    
    @field_validator("os_types")
    @classmethod
    def validate_os_types(cls, v: list[str]) -> list[str]:
        """Validate OS types."""
        valid_os = {"windows", "linux", "mac"}
        for os_type in v:
            if os_type not in valid_os:
                raise ValueError(f"Invalid OS type: {os_type}. Must be one of {valid_os}")
        return v


class UpdateResponse(BaseModel):
    """Response model for update endpoint."""
    
    success: bool = Field(..., description="Whether update was successful")
    message: str = Field(..., description="Status message")
    games_updated: int = Field(..., description="Number of games updated")
    games_added: int = Field(..., description="Number of new games added")


# Download schemas
class DownloadRequest(BaseModel):
    """Request model for download endpoint."""
    
    game_ids: list[int] = Field(..., min_length=1, description="Game IDs to download")
    save_dir: str = Field(..., min_length=1, description="Directory to save downloads")
    os_types: list[str] = Field(
        default_factory=lambda: ["windows"],
        description="Operating systems to download"
    )
    languages: list[str] = Field(
        default_factory=lambda: ["en"],
        description="Languages to download"
    )
    download_extras: bool = Field(True, description="Whether to download extras")
    
    @field_validator("os_types")
    @classmethod
    def validate_os_types(cls, v: list[str]) -> list[str]:
        """Validate OS types."""
        valid_os = {"windows", "linux", "mac"}
        for os_type in v:
            if os_type not in valid_os:
                raise ValueError(f"Invalid OS type: {os_type}. Must be one of {valid_os}")
        return v


class DownloadResponse(BaseModel):
    """Response model for download endpoint."""
    
    success: bool = Field(..., description="Whether download was initiated")
    message: str = Field(..., description="Status message")
    task_id: str = Field(..., description="Task ID for progress tracking")


class DownloadProgress(BaseModel):
    """Progress update for a download task."""
    
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Status: 'running', 'completed', 'failed'")
    current_game: Optional[str] = Field(None, description="Currently downloading game")
    current_file: Optional[str] = Field(None, description="Currently downloading file")
    bytes_downloaded: int = Field(0, description="Total bytes downloaded")
    bytes_total: int = Field(0, description="Total bytes to download")
    progress_percent: float = Field(0.0, description="Overall progress percentage")
    download_speed: float = Field(0.0, description="Download speed in bytes/second")
    eta_seconds: Optional[float] = Field(None, description="Estimated time remaining in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")


# Add without download schema
class AddWithoutDownloadRequest(BaseModel):
    """Request model for adding games without downloading."""
    
    game_ids: list[int] = Field(..., min_length=1, description="Game IDs to add to manifest")


class AddWithoutDownloadResponse(BaseModel):
    """Response model for add without download endpoint."""
    
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Status message")
    games_added: int = Field(..., description="Number of games added")


# Error schema
class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(..., description="Error type")
    detail: str = Field(..., description="Detailed error message")
