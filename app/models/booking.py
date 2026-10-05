from datetime import date, datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel


class Booking(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="user.id")
    listing_id: int = Field(foreign_key="listing.id")
    check_in: date
    check_out: date
    guests: int
    total_price: Decimal
    status: str = "pending"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
