"""
Base Pydantic schemas for Fluxion backend
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        use_enum_values=True,
        json_encoders={datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)},
    )


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields"""

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class BaseResponse(BaseSchema):
    """Base response schema"""

    success: bool = Field(True, description="Operation success status")
    message: str = Field(
        "Operation completed successfully", description="Response message"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class ErrorResponse(BaseSchema):
    """Error response schema"""

    success: bool = Field(False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class ValidationErrorResponse(ErrorResponse):
    """Validation error response schema"""

    validation_errors: List[Dict[str, Any]] = Field(
        ..., description="Validation error details"
    )


DataT = TypeVar("DataT")


class DataResponse(BaseModel, Generic[DataT]):
    """Generic data response schema"""

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(True, description="Operation success status")
    message: str = Field("Data retrieved successfully", description="Response message")
    data: DataT = Field(..., description="Response data")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class PaginationMeta(BaseSchema):
    """Pagination metadata schema"""

    page: int = Field(..., ge=1, description="Current page number")
    per_page: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    pages: int = Field(..., ge=0, description="Total number of pages")
    has_prev: bool = Field(..., description="Has previous page")
    has_next: bool = Field(..., description="Has next page")
    prev_page: Optional[int] = Field(None, description="Previous page number")
    next_page: Optional[int] = Field(None, description="Next page number")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated response schema"""

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(True, description="Operation success status")
    message: str = Field("Data retrieved successfully", description="Response message")
    data: List[DataT] = Field(..., description="Response data items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )


class HealthCheckResponse(BaseSchema):
    """Health check response schema"""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Health check timestamp"
    )
    version: str = Field(..., description="Application version")
    uptime: float = Field(..., description="Application uptime in seconds")
    services: Dict[str, Any] = Field(..., description="Service health status")


class MetricsResponse(BaseSchema):
    """Metrics response schema"""

    metrics: Dict[str, Any] = Field(..., description="Application metrics")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Metrics timestamp"
    )


class FilterBase(BaseSchema):
    """Base filter schema"""

    limit: int = Field(
        default=20, ge=1, le=100, description="Number of items to return"
    )
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field(
        "desc", pattern="^(asc|desc)$", description="Sort order"
    )

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ["asc", "desc"]:
            raise ValueError('sort_order must be either "asc" or "desc"')
        return v


class DateRangeFilter(BaseSchema):
    """Date range filter schema"""

    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        if v and info.data.get("start_date") and (v <= info.data["start_date"]):
            raise ValueError("end_date must be after start_date")
        return v


class SearchFilter(BaseSchema):
    """Search filter schema"""

    query: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Search query"
    )
    fields: Optional[List[str]] = Field(None, description="Fields to search in")


class StatusFilter(BaseSchema):
    """Status filter schema"""

    status: Optional[str] = Field(None, description="Status filter")
    is_active: Optional[bool] = Field(None, description="Active status filter")


class UserContextSchema(BaseSchema):
    """User context schema for requests"""

    user_id: UUID = Field(..., description="User ID")
    session_id: Optional[UUID] = Field(None, description="Session ID")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")


class AuditableSchema(BaseSchema):
    """Schema for auditable actions"""

    action: str = Field(..., description="Action being performed")
    resource_type: str = Field(..., description="Resource type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BulkOperationRequest(BaseSchema):
    """Bulk operation request schema"""

    operation: str = Field(..., description="Operation to perform")
    items: List[Dict[str, Any]] = Field(
        ..., min_length=1, max_length=100, description="Items to process"
    )
    options: Optional[Dict[str, Any]] = Field(None, description="Operation options")


class BulkOperationResponse(BaseSchema):
    """Bulk operation response schema"""

    success: bool = Field(..., description="Overall operation success")
    total_items: int = Field(..., description="Total items processed")
    successful_items: int = Field(..., description="Successfully processed items")
    failed_items: int = Field(..., description="Failed items")
    results: List[Dict[str, Any]] = Field(..., description="Individual results")
    errors: List[Dict[str, Any]] = Field(..., description="Error details")


class FileUploadResponse(BaseSchema):
    """File upload response schema"""

    file_id: UUID = Field(..., description="File ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="File content type")
    upload_url: str = Field(..., description="File access URL")
    expires_at: Optional[datetime] = Field(None, description="URL expiration time")


class NotificationSchema(BaseSchema):
    """Notification schema"""

    id: UUID = Field(..., description="Notification ID")
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    priority: str = Field(..., description="Notification priority")
    is_read: bool = Field(False, description="Read status")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WebhookPayload(BaseSchema):
    """Webhook payload schema"""

    event_type: str = Field(..., description="Event type")
    event_id: UUID = Field(..., description="Event ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    data: Dict[str, Any] = Field(..., description="Event data")
    signature: Optional[str] = Field(None, description="Payload signature")


class RateLimitInfo(BaseSchema):
    """Rate limit information schema"""

    limit: int = Field(..., description="Rate limit")
    remaining: int = Field(..., description="Remaining requests")
    reset_time: datetime = Field(..., description="Reset timestamp")
    retry_after: Optional[int] = Field(None, description="Retry after seconds")
