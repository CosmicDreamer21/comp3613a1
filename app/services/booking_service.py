from datetime import date

from app.models.booking import Booking
from app.models.listing import Listing
from app.models.user import User
from app.repositories.booking import BookingRepository


class BookingService:
    def __init__(self, booking_repo: BookingRepository):
        self.booking_repo = booking_repo

    def list_host_bookings(
        self, host_id: int
    ) -> list[tuple[Booking, Listing, User]]:
        bookings = self.booking_repo.list_for_host(host_id)
        updated = []
        for booking, listing, student in bookings:
            if booking.status == "confirmed" and booking.check_out < date.today():
                booking = self.booking_repo.update_status(booking, "completed")
            if booking.status not in {"completed", "cancelled"}:
                updated.append((booking, listing, student))
        return updated

    def update_host_request(
        self, booking_id: int, host_id: int, new_status: str
    ) -> Booking:
        if new_status not in {"confirmed", "cancelled"}:
            raise ValueError("A booking request can only be confirmed or cancelled.")
        result = self.booking_repo.get_for_host(booking_id, host_id)
        if result is None:
            raise LookupError("Booking request not found.")
        booking, _ = result
        if booking.status != "pending":
            raise ValueError("Only pending booking requests can be updated.")
        return self.booking_repo.update_status(booking, new_status)
