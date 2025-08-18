"""
Setting Domain Model
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_serializer


class Setting(BaseModel):
    """Setting domain model"""

    key: str = Field(..., description="Setting key")
    value: Any = Field(..., description="Setting value")
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={"example": {"key": "setting_key", "value": "setting_value"}}
    )
    
    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat() if dt else None
