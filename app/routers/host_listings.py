from typing import Annotated

from fastapi import Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.auth import HostDep
from app.dependencies.session import SessionDep
from app.repositories.listing import ListingRepository
from app.schemas.listing import ListingCreate
from app.services.listing_service import ListingService
from app.repositories.booking import BookingRepository
from app.services.booking_service import BookingService
from app.utilities.flash import flash
from . import router, templates


def _listing_service(db: SessionDep) -> ListingService:
    return ListingService(ListingRepository(db))


@router.get("/host/listings", response_class=HTMLResponse, name="host_listings_view")
def host_listings_view(request: Request, user: HostDep, db: SessionDep):
    listings = _listing_service(db).list_host_listings(user.id)
    return templates.TemplateResponse(
        request=request,
        name="host-listings.html",
        context={"user": user, "listings": listings},
    )


@router.get(
    "/host/listings/new",
    response_class=HTMLResponse,
    name="host_create_listing_form",
)
def host_create_listing_form(request: Request, user: HostDep):
    return templates.TemplateResponse(
        request=request,
        name="host-listing-form.html",
        context={
            "user": user,
            "listing": None,
            "is_resubmission": False,
        },
    )


@router.post("/host/listings/new", name="host_create_listing")
def create_listing(
    request: Request,
    user: HostDep,
    db: SessionDep,
    listing_data: Annotated[ListingCreate, Form()],
):
    try:
        _listing_service(db).create_listing(host_id=user.id, listing_data=listing_data)
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("host_create_listing_form"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, "Listing submitted for review.", "success")
    return RedirectResponse(
        url=request.url_for("host_listings_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/host/listings/{listing_id}/edit",
    response_class=HTMLResponse,
    name="host_edit_listing_form",
)
def host_edit_listing_form(
    listing_id: int, request: Request, user: HostDep, db: SessionDep
):
    try:
        listing = _listing_service(db).get_host_listing(listing_id, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if listing.status != "rejected":
        flash(request, "Only rejected listings can be edited and resubmitted.", "warning")
        return RedirectResponse(
            url=request.url_for("host_listings_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        request=request,
        name="host-listing-form.html",
        context={
            "user": user,
            "listing": listing,
            "is_resubmission": True,
        },
    )


@router.post(
    "/host/listings/{listing_id}/resubmit",
    name="host_resubmit_listing",
)
def host_resubmit_listing(
    listing_id: int,
    request: Request,
    user: HostDep,
    db: SessionDep,
    listing_data: Annotated[ListingCreate, Form()],
):
    try:
        _listing_service(db).resubmit_listing(
            listing_id, user.id, listing_data
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for(
                "host_edit_listing_form", listing_id=listing_id
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, "Listing resubmitted for review.", "success")
    return RedirectResponse(
        url=request.url_for("host_listings_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post(
    "/host/bookings/{booking_id}/status",
    name="host_update_booking_status",
)
def host_update_booking_status(
    booking_id: int,
    request: Request,
    user: HostDep,
    db: SessionDep,
    new_status: str = Form(),
):
    service = BookingService(BookingRepository(db))
    try:
        service.update_host_request(booking_id, user.id, new_status)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        flash(request, str(exc), "danger")
        return RedirectResponse(
            url=request.url_for("host_home_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, f"Booking {new_status}.", "success")
    return RedirectResponse(
        url=request.url_for("host_home_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )