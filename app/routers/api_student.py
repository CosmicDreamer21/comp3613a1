from typing import Optional

from fastapi import HTTPException, status

from app.dependencies.auth import StudentDep
from app.dependencies.session import SessionDep
from app.repositories.student_stay import StudentStayRepository
from app.schemas.api import (
    BookingCreate,
    BookingRead,
    ListingDetail,
    ListingSummary,
    ReviewCreate,
    ReviewRead,
    ReviewWithAuthor,
    StudentBookingRead,
    StudentBookingUpdate,
)
from app.services.student_stay_service import StudentStayService
from . import api_router
from .api_helpers import api_error


def _service(db) -> StudentStayService:
    return StudentStayService(StudentStayRepository(db))


@api_router.get("/listings", response_model=list[ListingSummary], tags=["API Student"])
def api_browse_listings(user: StudentDep, db: SessionDep, query: str = ""):
    """Approved listings, optionally filtered by area / room type / title words."""
    cards = _service(db).browse_listings(query.strip())
    return [
        ListingSummary.model_validate(listing).model_copy(
            update={"average_rating": avg, "review_count": count}
        )
        for listing, avg, count in cards
    ]


@api_router.get("/listings/{listing_id}", response_model=ListingDetail, tags=["API Student"])
def api_listing_detail(listing_id: int, user: StudentDep, db: SessionDep):
    try:
        listing, reviews, average = _service(db).get_listing_details(listing_id)
    except LookupError as exc:
        raise api_error(exc)
    detail = ListingDetail.model_validate(listing)
    detail.average_rating = average
    detail.review_count = len(reviews)
    detail.reviews = [
        ReviewWithAuthor.model_validate(review).model_copy(
            update={"author": author.full_name or author.username}
        )
        for review, author in reviews
    ]
    return detail


@api_router.post(
    "/bookings",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    tags=["API Student"],
)
def api_create_booking(body: BookingCreate, user: StudentDep, db: SessionDep):
    try:
        return _service(db).request_booking(
            listing_id=body.listing_id,
            student_id=user.id,
            check_in=body.check_in,
            check_out=body.check_out,
            guests=body.guests,
        )
    except ValueError as exc:
        raise api_error(exc)


@api_router.get("/bookings", response_model=list[StudentBookingRead], tags=["API Student"])
def api_list_bookings(user: StudentDep, db: SessionDep, status_filter: Optional[str] = None):
    """The signed-in student's bookings (optionally ?status_filter=pending|confirmed|completed|cancelled)."""
    rows = _service(db).list_student_bookings(user.id)
    result = []
    for booking, listing, has_review in rows:
        if status_filter and booking.status != status_filter:
            continue
        result.append(
            StudentBookingRead.model_validate(booking).model_copy(
                update={"listing_title": listing.title, "has_review": has_review}
            )
        )
    return result


@api_router.patch("/bookings/{booking_id}", response_model=BookingRead, tags=["API Student"])
def api_cancel_booking(
    booking_id: int, body: StudentBookingUpdate, user: StudentDep, db: SessionDep
):
    """Students may only move a booking to ``cancelled``."""
    try:
        return _service(db).cancel_booking(booking_id, user.id)
    except (LookupError, ValueError) as exc:
        raise api_error(exc)


@api_router.post(
    "/bookings/{booking_id}/review",
    response_model=ReviewRead,
    status_code=status.HTTP_201_CREATED,
    tags=["API Student"],
)
def api_submit_review(
    booking_id: int, body: ReviewCreate, user: StudentDep, db: SessionDep
):
    try:
        return _service(db).submit_review(
            booking_id=booking_id,
            student_id=user.id,
            rating=body.rating,
            comment=body.comment,
            accurate_listing=body.accurate_listing,
            safe_location=body.safe_location,
            clean_and_tidy=body.clean_and_tidy,
            responsive_host=body.responsive_host,
        )
    except (LookupError, ValueError) as exc:
        raise api_error(exc)
