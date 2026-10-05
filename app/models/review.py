from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Review(SQLModel, table=True):
    __tablename__ = "review"
    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_review_booking_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    booking_id: int = Field(foreign_key="booking.id", index=True)
    listing_id: int = Field(foreign_key="listing.id", index=True)
    student_id: int = Field(foreign_key="user.id", index=True)

    rating: int = Field(ge=1, le=5)
    comment: str

    accurate_listing: bool = Field(default=False)
    safe_location: bool = Field(default=False)
    clean_and_tidy: bool = Field(default=False)
    responsive_host: bool = Field(default=False)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    ) 