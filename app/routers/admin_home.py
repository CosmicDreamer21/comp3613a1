from typing import Annotated

from fastapi import Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.dependencies.auth import AdminDep
from app.dependencies.session import SessionDep
from app.repositories.listing import ListingRepository
from app.services.moderation_service import ModerationService
from app.utilities.flash import flash
from . import router, templates


@router.get("/admin", name="admin_home_view")
async def admin_home_view(request: Request, user: AdminDep, db: SessionDep):
    moderation = ModerationService(ListingRepository(db))
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"user": user, "pending_listings": moderation.list_pending()},
    )


@router.get(
    "/admin/listings/{listing_id}",
    name="admin_listing_review_view",
)
async def admin_listing_review_view(
    listing_id: int,
    request: Request,
    user: AdminDep,
    db: SessionDep,
):
    moderation = ModerationService(ListingRepository(db))
    try:
        listing = moderation.get_listing(listing_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request=request,
        name="admin-listing-review.html",
        context={"user": user, "listing": listing},
    )


@router.post(
    "/admin/listings/{listing_id}/decision",
    name="admin_listing_decision",
)
async def admin_listing_decision(
    listing_id: int,
    request: Request,
    user: AdminDep,
    db: SessionDep,
    decision: Annotated[str, Form()],
    rejection_reason_choice: Annotated[str, Form()] = "",
    rejection_reason_details: Annotated[str, Form()] = "",
):
    moderation = ModerationService(ListingRepository(db))
    try:
        result = moderation.review_listing(
            listing_id=listing_id,
            admin_id=user.id,
            decision=decision,
            rejection_reason_choice=rejection_reason_choice,
            rejection_reason_details=rejection_reason_details,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as err:
        flash(request, str(err), "danger")
        return RedirectResponse(
            url=request.url_for("admin_listing_review_view", listing_id=listing_id),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, f"Listing {result.status}.", "success")
    return RedirectResponse(
        url=request.url_for("admin_listing_review_view", listing_id=listing_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )
