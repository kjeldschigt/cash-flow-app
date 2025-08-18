"""
Base models and utilities for Pydantic v2.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, TypeVar, Generic, Type
from pydantic import BaseModel as PydanticBaseModel, Field, field_validator, ConfigDict, EmailStr, constr
from pydantic.fields import FieldInfo
from bson import ObjectId
from enum import Enum
import json

# Type variable for generic model type
ModelType = TypeVar("ModelType", bound="BaseModel")

class BaseModel(PydanticBaseModel):
    """Base model with common configuration and methods."""
    
    # Pydantic v2 config
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        use_enum_values=True,
        str_strip_whitespace=True,
        extra="ignore"
    )
    
    # Common fields with Pydantic v2 Field
    id: Optional[str] = Field(
        default=None,
        alias="_id",
        description="Unique identifier for the document",
        json_schema_extra={"example": "507f1f77bcf86cd799439011"}
    )
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the document was created"
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the document was last updated"
    )

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Override model_dump to handle MongoDB ObjectId and other custom types."""
        data = super().model_dump(**kwargs)
        
        # Convert _id to id if present
        if "_id" in data and "id" not in data:
            data["id"] = data.pop("_id")
            
        # Convert datetime objects to ISO format
        for field, value in data.items():
            if isinstance(value, datetime):
                data[field] = value.isoformat()
                
        return data
    
    @classmethod
    def from_mongo(cls: Type[ModelType], data: dict) -> ModelType:
        """Convert MongoDB document to model instance."""
        if not data:
            return None
            
        # Convert _id to id if present
        if "_id" in data and "id" not in data:
            data["id"] = str(data["_id"])
            
        return cls(**data)
    
    def to_mongo(self) -> dict:
        """Convert model to MongoDB document."""
        data = self.model_dump(exclude_none=True, by_alias=True)
        
        # Remove None values and convert id to _id
        if "id" in data:
            data["_id"] = data.pop("id")
            
        return data


class ResponseModel(BaseModel):
    """Base response model for API responses."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = "Operation successful") -> 'ResponseModel':
        """Create a success response."""
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_response(cls, message: str, data: Any = None) -> 'ResponseModel':
        """Create an error response."""
        return cls(success=False, message=message, data=data)


class PaginatedResponse(ResponseModel):
    """Paginated response model."""
    total: int = 0
    page: int = 1
    limit: int = 10
    total_pages: int = 1
    
    @classmethod
    def from_pagination(
        cls, 
        items: list, 
        total: int, 
        page: int, 
        limit: int
    ) -> 'PaginatedResponse':
        """Create a paginated response from query results."""
        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        return cls(
            success=True,
            message=f"Retrieved {len(items)} of {total} items",
            data=items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )


# Custom types for financial calculations
class PositiveDecimal(Decimal):
    """A positive decimal number."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, str):
            v = Decimal(v)
        if not isinstance(v, Decimal):
            raise TypeError('Decimal required')
        if v < 0:
            raise ValueError('Must be a positive number')
        return v


class CurrencyCode(str):
    """ISO 4217 currency code (e.g., 'USD', 'EUR')."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise TypeError('String required')
        if len(v) != 3 or not v.isalpha() or not v.isupper():
            raise ValueError('Must be a 3-letter uppercase currency code (e.g., USD, EUR)')
        return cls(v)


class Amount(Decimal):
    """A monetary amount that can be positive or negative."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, str):
            v = Decimal(v)
        if not isinstance(v, Decimal):
            raise TypeError('Decimal required')
        return v


class PositiveAmount(PositiveDecimal):
    """A positive monetary amount."""
    pass


# Common field configurations
class FieldConfig:
    """Common field configurations for models."""
    
    @staticmethod
    def email(**kwargs) -> Any:
        """Email field configuration."""
        return Field(
            ...,
            pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            description="A valid email address",
            json_schema_extra={"example": "user@example.com"},
            **kwargs
        )
    
    @staticmethod
    def password(**kwargs) -> Any:
        """Password field configuration."""
        return Field(
            ...,
            min_length=8,
            max_length=100,
            description="A strong password (min 8 characters)",
            json_schema_extra={"example": "Str0ngP@ssw0rd!"},
            **kwargs
        )
    
    @staticmethod
    def currency_code(**kwargs) -> Any:
        """Currency code field configuration (ISO 4217)."""
        return Field(
            default="USD",
            pattern=r"^[A-Z]{3}$",
            description="3-letter ISO 4217 currency code",
            json_schema_extra={"example": "USD"},
            **kwargs
        )


# Custom types for MongoDB
class PyObjectId(str):
    """Custom type for MongoDB ObjectId."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return str(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema: dict) -> None:
        field_schema.update(type="string", format="objectid")
