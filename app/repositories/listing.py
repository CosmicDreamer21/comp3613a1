from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.listing import Listing
from app.schemas.listing import ListingCreate


class ListingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        host_id: int,
        listing_data: ListingCreate,
        *,
        status: str = "pending",
    ) -> Listing:
        listing = Listing(
            host_id=host_id,
            status=status,
            **listing_data.model_dump(exclude={"image_url"}),
            image_url=listing_data.image_url or None,
        )
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def list_by_host(self, host_id: int) -> list[Listing]:
        statement = (
            select(Listing)
            .where(Listing.host_id == host_id)
            .order_by(Listing.created_at.desc())
        )
        return list(self.db.exec(statement).all())

    def list_pending(self) -> list[Listing]:
        statement = (
            select(Listing)
            .where(Listing.status == "pending")
            .order_by(Listing.created_at.asc())
        )
        return list(self.db.exec(statement).all())

    def get_by_id(self, listing_id: int) -> Listing | None:
        return self.db.get(Listing, listing_id)

    def record_review(
        self,
        listing: Listing,
        *,
        status: str,
        reviewed_by: int,
        reviewed_at: datetime,
        rejection_reason_choice: str | None = None,
        rejection_reason_details: str | None = None,
    ) -> Listing:
        listing.status = status
        listing.reviewed_by = reviewed_by
        listing.reviewed_at = reviewed_at
        listing.rejection_reason_choice = rejection_reason_choice
        listing.rejection_reason_details = rejection_reason_details

        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def get_owned(self, listing_id: int, host_id: int) -> Listing | None:
        statement = select(Listing).where(
            Listing.id == listing_id,
            Listing.host_id == host_id,
        )
        return self.db.exec(statement).one_or_none()

    def resubmit(
        self, listing: Listing, listing_data: ListingCreate
    ) -> Listing:
        for field_name, value in listing_data.model_dump().items():
            setattr(
                listing,
                field_name,
                value or None if field_name == "image_url" else value,
            )
        listing.status = "pending"
        listing.rejection_reason_choice = None
        listing.rejection_reason_details = None
        listing.reviewed_by = None
        listing.reviewed_at = None
        listing.updated_at = datetime.now(timezone.utc)
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing 