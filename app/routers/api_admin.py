from app.dependencies.auth import AdminDep
from app.dependencies.session import SessionDep
from app.repositories.listing import ListingRepository
from app.schemas.api import ListingRead, ModerationDecision
from app.services.moderation_service import ModerationService
from . import api_router
from .api_helpers import api_error


def _moderation(db) -> ModerationService:
    return ModerationService(ListingRepository(db))


@api_router.get("/admin/listings", response_model=list[ListingRead], tags=["API Admin"])
def api_admin_listings(user: AdminDep, db: SessionDep, status: str = "pending"):
    """Moderation queue (?status=pending|approved|rejected)."""
    try:
        return _moderation(db).list_by_status(status)
    except ValueError as exc:
        raise api_error(exc)


@api_router.get("/admin/listings/{listing_id}", response_model=ListingRead, tags=["API Admin"])
def api_admin_listing(listing_id: int, user: AdminDep, db: SessionDep):
    try:
        return _moderation(db).get_listing(listing_id)
    except LookupError as exc:
        raise api_error(exc)


@api_router.patch("/admin/listings/{listing_id}", response_model=ListingRead, tags=["API Admin"])
def api_admin_decide(
    listing_id: int, body: ModerationDecision, user: AdminDep, db: SessionDep
):
    """Approve, or reject with a required reason choice and details."""
    try:
        return _moderation(db).review_listing(
            listing_id=listing_id,
            admin_id=user.id,
            decision=body.status,
            rejection_reason_choice=body.rejection_reason_choice,
            rejection_reason_details=body.rejection_reason_details,
        )
    except (LookupError, ValueError) as exc:
        raise api_error(exc)
