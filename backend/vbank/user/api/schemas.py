from typing import Literal

from pydantic import BaseModel, Field


class ChangeUserStatusRequest(BaseModel):
    status: Literal["Active", "Blocked"]
    reason_code: str = Field(min_length=1, max_length=64)


class ChangeUserRoleRequest(BaseModel):
    role: Literal["Client", "Operator", "Admin"]
