"""StudentStay demo fixtures shared by the CLI and the /config initializer."""

from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session

from app.models.booking import Booking
from app.repositories.booking import BookingRepository
from app.repositories.listing import ListingRepository
from app.repositories.user import UserRepository
from app.schemas.listing import ListingCreate


def seed_host_fixtures(session: Session) -> None:
    users = UserRepository(session)
    host = users.get_by_username("rivera.host")
    student = users.get_by_username("maya.student")
    if host is None or student is None or host.id is None or student.id is None:
        raise RuntimeError("Seed host and student accounts before host fixtures.")

    if not host.full_name:
        host.full_name = "Elena Rivera"
    if not student.full_name:
        student.full_name = "Maya Chen"
    if not student.student_id:
        student.student_id = "816042731"
    session.add_all([host, student])
    session.commit()

    listing_repo = ListingRepository(session)
    listings_by_title = {
        listing.title: listing
        for listing in listing_repo.list_by_host(host.id)
    }
    today = date.today()
    availability_start = today - timedelta(days=90)
    availability_end = today + timedelta(days=300)
    fixtures = [
        (
            "Cedar House",
            "A bright private room in a quiet home close to campus.",
            "St. Augustine",
            "12 Cedar Avenue, St. Augustine",
            Decimal("285.00"),
            "Private room",
            "Wi-Fi, study desk, laundry, parking",
            "approved",
            2,
        ),
        (
            "Campus View Studio",
            "A compact studio with a dedicated study area and kitchenette.",
            "St. Augustine",
            "8 College Road, St. Augustine",
            Decimal("330.00"),
            "Studio",
            "Wi-Fi, study desk, kitchenette",
            "approved",
            3,
        ),
        (
            "Palm Court Shared Flat",
            "A furnished shared flat with easy access to transport.",
            "St. Augustine",
            "4 Palm Court, St. Augustine",
            Decimal("210.00"),
            "Shared flat",
            "Wi-Fi, laundry, parking",
            "approved",
            1,
        ),
        (
            "Garden Annex near UWI",
            "A furnished annex with a separate entrance, study desk, kitchenette, and secure parking.",
            "St. Augustine",
            "14 Gordon Street, St. Augustine",
            Decimal("320.00"),
            "Entire studio",
            "Wi-Fi, study desk, kitchenette, parking",
            "pending",
            3,
        ),
    ]
    for (
        title,
        description,
        city,
        address,
        price,
        room_type,
        amenities,
        listing_status,
        minimum_stay,
    ) in fixtures:
        if title in listings_by_title:
            continue
        listing = listing_repo.create(
            host.id,
            ListingCreate(
                title=title,
                description=description,
                city=city,
                address=address,
                price_per_night=price,
                room_type=room_type,
                amenities=amenities,
                image_url="",
                available_from=availability_start,
                available_until=availability_end,
                minimum_stay_nights=minimum_stay,
            ),
            status=listing_status,
        )
        listings_by_title[title] = listing

    booking_repo = BookingRepository(session)
    booking_fixtures = [
        ("Palm Court Shared Flat", today + timedelta(days=14), today + timedelta(days=18), "pending"),
        ("Cedar House", today + timedelta(days=7), today + timedelta(days=13), "confirmed"),
        ("Campus View Studio", today - timedelta(days=30), today - timedelta(days=25), "confirmed"),
    ]
    for title, check_in, check_out, booking_status in booking_fixtures:
        listing = listings_by_title[title]
        if listing.id is None or booking_repo.has_booking(
            student.id, listing.id, check_in, check_out
        ):
            continue
        nights = (check_out - check_in).days
        booking_repo.create(
            Booking(
                student_id=student.id,
                listing_id=listing.id,
                check_in=check_in,
                check_out=check_out,
                guests=1,
                total_price=listing.price_per_night * nights,
                status=booking_status,
            )
        )
