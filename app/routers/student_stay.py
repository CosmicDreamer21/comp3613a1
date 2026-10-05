from datetime import date, timedelta
from typing import Annotated

from fastapi import Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.dependencies.auth import StudentDep
from app.dependencies.session import SessionDep
from app.repositories.student_stay import StudentStayRepository
from app.services.student_stay_service import StudentStayService
from app.utilities.flash import flash
from . import router, templates


@router.get("/student/listings", name="student_listings_view")
async def student_listings_view(
    request: Request,
    user: StudentDep,
    db: SessionDep,
    query: str = "",
):
    listings = StudentStayService(
        StudentStayRepository(db)
    ).browse_listings(query.strip())
    return templates.TemplateResponse(
        request=request,
        name="student-listings.html",
        context={"user": user, "listings": listings, "query": query},
    )


@router.get(
    "/student/listings/{listing_id}",
    name="student_listing_details_view",
)
async def student_listing_details_view(
    listing_id: int,
    request: Request,
    user: StudentDep,
    db: SessionDep,
):
    try:
        listing, reviews, average_rating = StudentStayService(
            StudentStayRepository(db)
        ).get_listing_details(listing_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="student-listing-details.html",
        context={
            "user": user,
            "listing": listing,
            "reviews": reviews,
            "average_rating": average_rating,
            "today": date.today().isoformat(),
            "minimum_check_in": max(
                date.today(), listing.available_from
            ).isoformat(),
            "minimum_check_out": (
                max(date.today(), listing.available_from)
                + timedelta(days=listing.minimum_stay_nights)
            ).isoformat(),
        },
    )


@router.post(
    "/student/listings/{listing_id}/book",
    name="student_request_booking",
)
async def student_request_booking(
    listing_id: int,
    request: Request,
    user: StudentDep,
    db: SessionDep,
    check_in: Annotated[date, Form()],
    check_out: Annotated[date, Form()],
    guests: Annotated[int, Form()],
):
    service = StudentStayService(StudentStayRepository(db))
    try:
        service.request_booking(
            listing_id=listing_id,
            student_id=user.id,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
        )
    except ValueError as err:
        flash(request, str(err), "danger")
        return RedirectResponse(
            url=request.url_for("student_listing_details_view", listing_id=listing_id),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, "Booking request sent to the host.", "success")
    return RedirectResponse(
        url=request.url_for("student_bookings_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/student/bookings", name="student_bookings_view")
async def student_bookings_view(
    request: Request,
    user: StudentDep,
    db: SessionDep,
    status_filter: str = "upcoming",
):
    bookings = StudentStayService(
        StudentStayRepository(db)
    ).list_student_bookings(user.id)
    return templates.TemplateResponse(
        request=request,
        name="student-bookings.html",
        context={
            "user": user,
            "bookings": bookings,
            "status_filter": status_filter,
            "today": date.today().isoformat(),
        },
    )


@router.post(
    "/student/bookings/{booking_id}/cancel",
    name="student_cancel_booking",
)
async def student_cancel_booking(
    booking_id: int,
    request: Request,
    user: StudentDep,
    db: SessionDep,
):
    service = StudentStayService(StudentStayRepository(db))
    try:
        service.cancel_booking(booking_id, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("student_bookings_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, "Booking cancelled.", "success")
    return RedirectResponse(
        url=request.url_for("student_bookings_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/student/bookings/{booking_id}/review",
    name="student_review_form",
)
async def student_review_form(
    booking_id: int,
    request: Request,
    user: StudentDep,
    db: SessionDep,
):
    service = StudentStayService(StudentStayRepository(db))
    try:
        booking, listing = service.get_reviewable_booking(booking_id, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("student_bookings_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        request=request,
        name="student-review.html",
        context={"user": user, "booking": booking, "listing": listing},
    )


@router.post(
    "/student/bookings/{booking_id}/review",
    name="student_submit_review",
)
async def student_submit_review(
    booking_id: int,
    request: Request,
    user: StudentDep,
    db: SessionDep,
    rating: Annotated[int, Form()],
    comment: Annotated[str, Form()],
    accurate_listing: Annotated[bool, Form()] = False,
    safe_location: Annotated[bool, Form()] = False,
    clean_and_tidy: Annotated[bool, Form()] = False,
    responsive_host: Annotated[bool, Form()] = False,
):
    service = StudentStayService(StudentStayRepository(db))
    try:
        service.submit_review(
            booking_id=booking_id,
            student_id=user.id,
            rating=rating,
            comment=comment,
            accurate_listing=accurate_listing,
            safe_location=safe_location,
            clean_and_tidy=clean_and_tidy,
            responsive_host=responsive_host,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("student_review_form", booking_id=booking_id),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, "Your review was submitted.", "success")
    return RedirectResponse(
        url=request.url_for("student_bookings_view").include_query_params(
            status_filter="past"
        ),
        status_code=status.HTTP_303_SEE_OTHER,
    )
