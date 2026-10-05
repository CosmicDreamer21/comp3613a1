from datetime import date
from sqlalchemy import or_
from sqlmodel import Session, select

from app.models.booking import Booking
from app.models.listing import Listing
from app.models.review import Review
from app.models.user import User


class StudentStayRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_approved(self, query: str = "") -> list[Listing]:
        statement = select(Listing).where(Listing.status == "approved")
        search_terms = query.replace(".", " ").replace(",", " ").split()
        searchable_fields = (
            Listing.title,
            Listing.city,
            Listing.address,
            Listing.room_type,
        )
        for term in search_terms:
            search_term = f"%{term}%"
            statement = statement.where(
                or_(*(field.ilike(search_term) for field in searchable_fields))
            )
        statement = statement.order_by(Listing.created_at.desc())
        return list(self.db.exec(statement).all())

    def get_approved_listing(self, listing_id: int) -> Listing | None:
        statement = select(Listing).where(
            Listing.id == listing_id,
            Listing.status == "approved",
        )
        return self.db.exec(statement).one_or_none()

    def get_listing(self, listing_id: int) -> Listing | None:
        return self.db.get(Listing, listing_id)

    def booking_conflicts(
        self,
        listing_id: int,
        check_in: date,
        check_out: date,
    ) -> bool:
        statement = select(Booking).where(
            Booking.listing_id == listing_id,
            Booking.status.in_(["pending", "confirmed"]),
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        )
        results = self.db.exec(statement).all()
        return len(results) > 0

    def create_booking(self, booking: Booking) -> Booking:
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def list_student_bookings(self, student_id: int) -> list[tuple[Booking, Listing]]:
        statement = (
            select(Booking, Listing)
            .join(Listing, Booking.listing_id == Listing.id)
            .where(Booking.student_id == student_id)
            .order_by(Booking.check_in.desc())
        )
        return [
            (booking, listing)
            for booking, listing in self.db.exec(statement).all()
        ]

    def get_student_booking(
        self, booking_id: int, student_id: int
    ) -> tuple[Booking, Listing] | None:
        statement = (
            select(Booking, Listing)
            .join(Listing, Booking.listing_id == Listing.id)
            .where(
                Booking.id == booking_id,
                Booking.student_id == student_id,
            )
        )
        return self.db.exec(statement).one_or_none()

    def update_booking_status(self, booking: Booking, new_status: str) -> Booking:
        booking.status = new_status
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def has_review(self, booking_id: int) -> bool:
        statement = select(Review.id).where(Review.booking_id == booking_id)
        return self.db.exec(statement).first() is not None

    def create_review(self, review: Review) -> Review:
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def list_reviews(self, listing_id: int) -> list[tuple[Review, User]]:
        statement = (
            select(Review, User)
            .join(User, Review.student_id == User.id)
            .where(Review.listing_id == listing_id)
            .order_by(Review.created_at.desc())
        )
        return [
            (review, student)
            for review, student in self.db.exec(statement).all()
        ]
