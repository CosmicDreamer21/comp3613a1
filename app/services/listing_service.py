from app.models.listing import Listing
from app.repositories.listing import ListingRepository
from app.schemas.listing import ListingCreate


class ListingService:
    def __init__(self, listing_repo: ListingRepository):
        self.listing_repo = listing_repo

    def create_listing(self, host_id: int, listing_data: ListingCreate) -> Listing:
        self._validate_dates(listing_data)
        return self.listing_repo.create(host_id, listing_data)

    def list_host_listings(self, host_id: int) -> list[Listing]:
        return self.listing_repo.list_by_host(host_id)

    def get_host_listing(self, listing_id: int, host_id: int) -> Listing:
        listing = self.listing_repo.get_owned(listing_id, host_id)
        if listing is None:
            raise LookupError("Listing not found.")
        return listing

    def resubmit_listing(
        self, listing_id: int, host_id: int, listing_data: ListingCreate
    ) -> Listing:
        self._validate_dates(listing_data)
        listing = self.get_host_listing(listing_id, host_id)
        if listing.status != "rejected":
            raise ValueError("Only rejected listings can be edited and resubmitted.")
        return self.listing_repo.resubmit(listing, listing_data)

    @staticmethod
    def _validate_dates(listing_data: ListingCreate) -> None:
        if listing_data.available_until <= listing_data.available_from:
            raise ValueError("The available-until date must be after the available-from date.")
