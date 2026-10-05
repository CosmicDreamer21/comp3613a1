from datetime import date

from sqlmodel import Session, select

from app.models.booking import Booking
from app.models.listing import Listing
from app.models.user import User


class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, booking: Booking) -> Booking:
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def list_for_host(
        self, host_id: int
    ) -> list[tuple[Booking, Listing, User]]:
        statement = (
            select(Booking, Listing, User)
            .join(Listing, Booking.listing_id == Listing.id)
            .join(User, Booking.student_id == User.id)
            .where(Listing.host_id == host_id)
            .order_by(Booking.check_in.desc())
        )
        return [
            (booking, listing, student)
            for booking, listing, student in self.db.exec(statement).all()
        ]

    def get_for_host(
        self, booking_id: int, host_id: int
    ) -> tuple[Booking, Listing] | None:
        statement = (
            select(Booking, Listing)
            .join(Listing, Booking.listing_id == Listing.id)
            .where(Booking.id == booking_id, Listing.host_id == host_id)
        )
        result = self.db.exec(statement).one_or_none()
        if result is None:
            return None
        return result

    def update_status(self, booking: Booking, new_status: str) -> Booking:
        booking.status = new_status
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def has_booking(
        self,
        student_id: int,
        listing_id: int,
        check_in: date,
        check_out: date,
    ) -> bool:
        statement = select(Booking.id).where(
            Booking.student_id == student_id,
            Booking.listing_id == listing_id,
            Booking.check_in == check_in,
            Booking.check_out == check_out,
        )
        return self.db.exec(statement).first() is not None
