from datetime import date
from decimal import Decimal

from sqlmodel import Field, SQLModel


class ListingCreate(SQLModel):
    title: str = Field(min_length=3, max_length=80)
    description: str = Field(min_length=10, max_length=2000)
    city: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=3, max_length=200)
    price_per_night: Decimal = Field(gt=0)
    room_type: str = Field(min_length=2, max_length=80)
    amenities: str = Field(default="", max_length=500)
    image_url: str = ""
    available_from: date
    available_until: date
    minimum_stay_nights: int = Field(default=1, ge=1)
