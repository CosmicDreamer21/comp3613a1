from fastapi import Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.dependencies.session import SessionDep
from app.dependencies.auth import HostDep, StudentDep
from . import router, templates


@router.get("/app", response_class=HTMLResponse)
async def user_home_view(
    request: Request,
    user: StudentDep,
):
    return RedirectResponse(
        url=request.url_for("student_listings_view"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/host", response_class=HTMLResponse, name="host_home_view")
async def host_home_view(request: Request, user: HostDep, db: SessionDep):
    from app.repositories.booking import BookingRepository
    from app.repositories.listing import ListingRepository
    from app.services.booking_service import BookingService
    from app.services.listing_service import ListingService

    listings = ListingService(ListingRepository(db)).list_host_listings(user.id)
    bookings = BookingService(BookingRepository(db)).list_host_bookings(user.id)
    return templates.TemplateResponse(
        request=request,
        name="host-dashboard.html",
        context={
            "user": user,
            "listings": listings,
            "bookings": bookings,
            "approved_count": sum(
                listing.status == "approved" for listing in listings
            ),
            "pending_count": sum(
                booking.status == "pending"
                for booking, _listing, _student in bookings
            ),
        },
    )