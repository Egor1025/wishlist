from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WishIn(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: Annotated[str | None, Field(min_length=1, max_length=50)] = None
    link: Annotated[str | None, Field(max_length=200, pattern=r"^https?://")] = None
    price_estimate: Decimal | None = None
    notes: Annotated[str | None, Field(max_length=1000)] = None

    @field_validator("price_estimate", mode="before")
    @classmethod
    def parse_price(cls, v):
        if v is None:
            return None
        try:
            dec = Decimal(str(v))
        except Exception:
            raise ValueError("price must be a decimal")
        if dec < 0:
            raise ValueError("price can't be negative")
        return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class WishOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    link: str | None
    price_estimate: Decimal | None
    updated_at: str | None
    notes: str | None
