from fastapi import status

from app.dependencies.auth import HostDep
from app.dependencies.session import SessionDep
from app.repositories.booking import BookingRepository
from app.repositories.listing import ListingRepository
from app.schemas.api import HostBookingRead, HostBookingUpdate, ListingRead
from app.schemas.listing import ListingCreate
from app.services.booking_service import BookingService
from app.services.listing_service import ListingService
from . import api_router
from .api_helpers import api_error


def _listings(db) -> ListingService:
    return ListingService(ListingRepository(db))


@api_router.get("/host/listings", response_model=list[ListingRead], tags=["API Host"])
def api_host_listings(user: HostDep, db: SessionDep):
    return _listings(db).list_host_listings(user.id)


@api_router.post(
    "/host/listings",
    response_model=ListingRead,
    status_code=status.HTTP_201_CREATED,
    tags=["API Host"],
)
def api_host_create_listing(body: ListingCreate, user: HostDep, db: SessionDep):
    try:
        return _listings(db).create_listing(user.id, body)
    except ValueError as exc:
        raise api_error(exc)


@api_router.get("/host/listings/{listing_id}", response_model=ListingRead, tags=["API Host"])
def api_host_listing(listing_id: int, user: HostDep, db: SessionDep):
    try:
        return _listings(db).get_host_listing(listing_id, user.id)
    except LookupError as exc:
        raise api_error(exc)


@api_router.put("/host/listings/{listing_id}", response_model=ListingRead, tags=["API Host"])
def api_host_resubmit_listing(
    listing_id: int, body: ListingCreate, user: HostDep, db: SessionDep
):
    """Replace a *rejected* listing and send it back to pending review."""
    try:
        return _listings(db).resubmit_listing(listing_id, user.id, body)
    except (LookupError, ValueError) as exc:
        raise api_error(exc)


@api_router.get("/host/bookings", response_model=list[HostBookingRead], tags=["API Host"])
def api_host_bookings(user: HostDep, db: SessionDep):
    rows = BookingService(BookingRepository(db)).list_host_bookings(user.id)
    return [
        HostBookingRead.model_validate(booking).model_copy(
            update={
                "listing_title": listing.title,
                "student_name": student.full_name or student.username,
            }
        )
        for booking, listing, student in rows
    ]


@api_router.patch("/host/bookings/{booking_id}", response_model=HostBookingRead, tags=["API Host"])
def api_host_update_booking(
    booking_id: int, body: HostBookingUpdate, user: HostDep, db: SessionDep
):
    service = BookingService(BookingRepository(db))
    try:
        booking = service.update_host_request(booking_id, user.id, body.status)
    except (LookupError, ValueError) as exc:
        raise api_error(exc)
    return HostBookingRead.model_validate(booking)
