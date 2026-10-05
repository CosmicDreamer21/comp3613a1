from datetime import datetime, timezone

from app.models.listing import Listing
from app.repositories.listing import ListingRepository


class ModerationService:
    def __init__(self, listing_repo: ListingRepository):
        self.listing_repo = listing_repo

    def list_pending(self) -> list[Listing]:
        return self.listing_repo.list_pending()

    def get_listing(self, listing_id: int) -> Listing:
        listing = self.listing_repo.get_by_id(listing_id)
        if listing is None:
            raise LookupError("Listing not found.")
        return listing

    def review_listing(
        self,
        listing_id: int,
        admin_id: int,
        decision: str,
        rejection_reason_choice: str = "",
        rejection_reason_details: str = "",
    ) -> Listing:
        listing = self.get_listing(listing_id)
        if listing.status != "pending":
            raise ValueError("Only pending listings can be reviewed.")

        if decision == "approved":
            next_status = "approved"
            reason_choice = None
            reason_details = None
        elif decision == "rejected":
            if not rejection_reason_choice.strip() or not rejection_reason_details.strip():
                raise ValueError(
                    "Both rejection reason choice and details are required."
                )
            next_status = "rejected"
            reason_choice = rejection_reason_choice.strip()
            reason_details = rejection_reason_details.strip()
        else:
            raise ValueError("Choose either approve or reject.")

        return self.listing_repo.record_review(
            listing,
            status=next_status,
            reviewed_by=admin_id,
            reviewed_at=datetime.now(timezone.utc),
            rejection_reason_choice=reason_choice,
            rejection_reason_details=reason_details,
        ) 