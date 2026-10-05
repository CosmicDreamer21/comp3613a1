from datetime import date

from app.models.booking import Booking
from app.models.listing import Listing
from app.models.review import Review
from app.models.user import User
from app.repositories.student_stay import StudentStayRepository


class StudentStayService:
    def __init__(self, repository: StudentStayRepository):
        self.repository = repository

    def browse_listings(
        self, query: str = ""
    ) -> list[tuple[Listing, float | None, int]]:
        listings = self.repository.list_approved(query)
        cards = []
        for listing in listings:
            reviews = self.repository.list_reviews(listing.id)
            average = (
                sum(review[0].rating for review in reviews) / len(reviews)
                if reviews
                else None
            )
            cards.append((listing, average, len(reviews)))
        return cards

    def get_listing_details(
        self, listing_id: int
    ) -> tuple[Listing, list[tuple[Review, User]], float | None]:
        listing = self.repository.get_approved_listing(listing_id)
        if listing is None:
            raise LookupError("Approved listing not found.")
        reviews = self.repository.list_reviews(listing_id)
        average = (
            sum(review[0].rating for review in reviews) / len(reviews)
            if reviews
            else None
        )
        return listing, reviews, average

    def request_booking(
        self,
        listing_id: int,
        student_id: int,
        check_in: date,
        check_out: date,
        guests: int,
    ) -> Booking:
        if check_in < date.today():
            raise ValueError("Check-in date cannot be in the past.")
        if check_out <= check_in:
            raise ValueError("Check-out date must be after check-in date.")

        if guests < 1:
            raise ValueError("Guests must be at least 1.")

        listing = self.repository.get_approved_listing(listing_id)
        if not listing:
            raise ValueError("Listing not found or is not approved.")

        if check_in < listing.available_from:
            raise ValueError("Check-in date is before the listing's available date.")
        if check_out > listing.available_until:
            raise ValueError("Check-out date exceeds the listing's available window.")

        nights = (check_out - check_in).days
        if nights < listing.minimum_stay_nights:
            raise ValueError(f"Minimum stay required is {listing.minimum_stay_nights} night(s).")

        if self.repository.booking_conflicts(listing_id, check_in, check_out):
            raise ValueError("The selected dates overlap with an existing booking.")

        total_price = nights * listing.price_per_night

        booking = Booking(
            listing_id=listing_id,
            student_id=student_id,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            total_price=total_price,
            status="pending",
        )
        return self.repository.create_booking(booking)

    def list_student_bookings(
        self, student_id: int
    ) -> list[tuple[Booking, Listing, bool]]:
        result = []
        today = date.today()
        for booking, listing in self.repository.list_student_bookings(student_id):
            if booking.status == "confirmed" and booking.check_out < today:
                booking = self.repository.update_booking_status(
                    booking, "completed"
                )
            if booking.id is None:
                raise RuntimeError("Student booking is missing a database ID.")
            result.append(
                (booking, listing, self.repository.has_review(booking.id))
            )
        return result

    def cancel_booking(self, booking_id: int, student_id: int) -> Booking:
        result = self.repository.get_student_booking(booking_id, student_id)
        if result is None:
            raise LookupError("Booking not found.")
        booking = result[0]
        if booking.status not in {"pending", "confirmed"}:
            raise ValueError("Only pending or confirmed bookings can be cancelled.")
        if booking.check_in < date.today():
            raise ValueError("A stay that has already started cannot be cancelled.")
        return self.repository.update_booking_status(booking, "cancelled")

    def get_reviewable_booking(
        self, booking_id: int, student_id: int
    ) -> tuple[Booking, Listing]:
        result = self.repository.get_student_booking(booking_id, student_id)
        if result is None:
            raise LookupError("Booking not found.")
        booking, listing = result
        if booking.status == "confirmed" and booking.check_out < date.today():
            booking = self.repository.update_booking_status(
                booking, "completed"
            )
        if booking.status != "completed":
            raise ValueError("A review is available after the stay is completed.")
        if self.repository.has_review(booking_id):
            raise ValueError("This completed stay already has a review.")
        return booking, listing

    def submit_review(
        self,
        booking_id: int,
        student_id: int,
        rating: int,
        comment: str,
        accurate_listing: bool,
        safe_location: bool,
        clean_and_tidy: bool,
        responsive_host: bool,
    ) -> Review:
        booking, listing = self.get_reviewable_booking(booking_id, student_id)
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5 stars.")
        normalized_comment = comment.strip()
        if len(normalized_comment) < 28:
            raise ValueError("Your review must contain at least 28 characters.")
        if len(normalized_comment) > 500:
            raise ValueError("Your review must be 500 characters or fewer.")
        if booking.id is None or listing.id is None:
            raise RuntimeError("Cannot review a booking that has not been persisted.")
        return self.repository.create_review(
            Review(
                listing_id=listing.id,
                student_id=student_id,
                booking_id=booking.id,
                rating=rating,
                comment=normalized_comment,
                accurate_listing=accurate_listing,
                safe_location=safe_location,
                clean_and_tidy=clean_and_tidy,
                responsive_host=responsive_host,
            )
        )
