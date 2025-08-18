"""
Setting Domain Model
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

class Setting(BaseModel):
    """Setting domain model"""
    
    key: str = Field(..., description="Setting key")
    value: Any = Field(..., description="Setting value")
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
