"""Request/response schemas for the StudentStay REST API (/api)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# Money is always shown with two decimals ("320.00"), whatever scale the database stores.
Money = Annotated[
    Decimal,
    PlainSerializer(lambda value: f"{value:.2f}", return_type=str, when_used="json"),
]


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, description="Username or email")
    password: str = Field(min_length=1)
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    full_name: str = ""


class ListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    host_id: int
    title: str
    description: str
    city: str
    address: str
    price_per_night: Money
    room_type: str
    amenities: str
    image_url: Optional[str] = None
    available_from: date
    available_until: date
    minimum_stay_nights: int
    status: str
    rejection_reason_choice: Optional[str] = None
    rejection_reason_details: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None


class ListingSummary(ListingRead):
    verified: bool = True
    average_rating: Optional[float] = None
    review_count: int = 0


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    listing_id: int
    student_id: int
    rating: int
    comment: str
    accurate_listing: bool
    safe_location: bool
    clean_and_tidy: bool
    responsive_host: bool
    created_at: datetime


class ReviewWithAuthor(ReviewRead):
    author: str = ""


class ListingDetail(ListingSummary):
    reviews: list[ReviewWithAuthor] = []


class BookingCreate(BaseModel):
    listing_id: int
    check_in: date
    check_out: date
    guests: int


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    listing_id: int
    check_in: date
    check_out: date
    guests: int
    total_price: Money
    status: str


class StudentBookingRead(BookingRead):
    listing_title: str = ""
    has_review: bool = False


class HostBookingRead(BookingRead):
    listing_title: str = ""
    student_name: str = ""


class StudentBookingUpdate(BaseModel):
    status: Literal["cancelled"]


class HostBookingUpdate(BaseModel):
    status: Literal["confirmed", "cancelled"]


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str
    accurate_listing: bool = False
    safe_location: bool = False
    clean_and_tidy: bool = False
    responsive_host: bool = False


class ModerationDecision(BaseModel):
    status: Literal["approved", "rejected"]
    rejection_reason_choice: str = ""
    rejection_reason_details: str = ""
