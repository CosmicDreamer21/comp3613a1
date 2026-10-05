from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class Listing(SQLModel, table=True):
    __tablename__ = "listing"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="check_listing_status_valid",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign Keys & ERD Fields
    host_id: int = Field(foreign_key="user.id")
    reviewed_by: Optional[int] = Field(default=None, foreign_key="user.id")
    title: str
    description: str
    city: str
    address: str
    price_per_night: Decimal
    room_type: str
    amenities: str
    image_url: Optional[str] = None
    available_from: date
    available_until: date
    minimum_stay_nights: int = 1
    status: str = Field(default="pending")  # pending | approved | rejected
    rejection_reason_choice: Optional[str] = None
    rejection_reason_details: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    host: Optional["User"] = Relationship(
        sa_relationship_kwargs={"primaryjoin": "Listing.host_id == User.id"}
    )
    reviewer: Optional["User"] = Relationship(
        sa_relationship_kwargs={"primaryjoin": "Listing.reviewed_by == User.id"}
    )