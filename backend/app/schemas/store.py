from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StoreCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=160)

    @field_validator("code", "name", "location")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, value: str) -> str:
        return value.upper()


class StoreUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=32)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    location: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class StoreRead(BaseModel):
    id: int
    code: str
    name: str
    location: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StorePage(BaseModel):
    items: list[StoreRead]
    skip: int
    limit: int
    total: int
