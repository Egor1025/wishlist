from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class WishIn(BaseModel):
    title: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    link: str | None = None
    price_estimate: Decimal | int | float | str | None = None
    notes: str | None = None


class WishOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    link: str | None
    price_estimate: Decimal | None
    updated_at: str | None
    notes: str | None
