"""Unit tests: each piece tested on its own, no database."""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import get_settings
from app.dependencies.auth import is_admin_dep, is_host_dep, is_student_dep
from app.models.booking import Booking
from app.models.listing import Listing
from app.models.user import User
from app.repositories.listing import ListingRepository
from app.repositories.student_stay import StudentStayRepository
from app.repositories.user import UserRepository
from app.schemas.listing import ListingCreate
from app.services.auth_service import AuthService
from app.services.errors import ConflictError, NotFoundError
from app.services.listing_service import ListingService
from app.services.moderation_service import ModerationService
from app.services.student_stay_service import StudentStayService
from app.utilities.security import create_access_token, encrypt_password, verify_password


def in_days(n):
    return date.today() + timedelta(days=n)


# ---------------------------------------------------------------- users and security

class TestUser:
    def test_new_user(self):
        user = User(username="bob", email="bob@mail.com", password="bobpass")
        assert user.username == "bob"
        assert user.email == "bob@mail.com"

    def test_hashed_password(self):
        assert encrypt_password("mypass") != "mypass"

    def test_check_password(self):
        hashed = encrypt_password("mypass")
        assert verify_password("mypass", hashed) is True
        assert verify_password("wrong", hashed) is False


def test_token_contains_user_id():
    token = create_access_token({"sub": "7"})
    claims = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    assert claims["sub"] == "7"


# ---------------------------------------------------------------- listing schema

def _listing(**overrides):
    values = dict(
        title="Cedar House", description="A bright private room.", city="St. Augustine",
        address="12 Cedar Avenue", price_per_night=Decimal("100"), room_type="Private room",
        available_from=date(2026, 1, 1), available_until=date(2026, 6, 1),
    )
    values.update(overrides)
    return ListingCreate(**values)


def test_valid_listing_schema():
    assert _listing().minimum_stay_nights == 1


@pytest.mark.parametrize("field, value", [("title", "ab"), ("price_per_night", Decimal("0")), ("minimum_stay_nights", 0)])
def test_invalid_listing_schema(field, value):
    with pytest.raises(ValidationError):
        _listing(**{field: value})


# ---------------------------------------------------------------- login service

def test_login_success_returns_token():
    repo = Mock(spec=UserRepository)
    repo.get_by_identifier.return_value = SimpleNamespace(id=7, role="student", password=encrypt_password("secret123"))
    assert AuthService(repo).authenticate_user("maya", "secret123") is not None


def test_login_wrong_password_returns_none():
    repo = Mock(spec=UserRepository)
    repo.get_by_identifier.return_value = SimpleNamespace(id=7, role="student", password=encrypt_password("secret123"))
    assert AuthService(repo).authenticate_user("maya", "nope") is None


# ---------------------------------------------------------------- booking rules (repository mocked)

def stay_service():
    """StudentStayService whose repository is a Mock that approves a $100/night listing."""
    listing = Listing(
        id=1, host_id=2, title="Cedar House", description="d", city="c", address="a",
        price_per_night=Decimal("100.00"), room_type="Studio", amenities="",
        available_from=in_days(-30), available_until=in_days(60), minimum_stay_nights=2, status="approved",
    )
    repo = Mock(spec=StudentStayRepository)
    repo.get_approved_listing.return_value = listing
    repo.booking_conflicts.return_value = False
    repo.create_booking.side_effect = lambda booking: booking
    repo.update_booking_status.side_effect = lambda booking, status: (setattr(booking, "status", status) or booking)
    repo.has_review.return_value = False
    repo.create_review.side_effect = lambda review: review
    return StudentStayService(repo), repo, listing


def make_booking(status="pending", check_in=5, check_out=8):
    return Booking(id=4, student_id=3, listing_id=1, check_in=in_days(check_in), check_out=in_days(check_out),
                   guests=1, total_price=Decimal("300"), status=status)


def test_booking_total_is_nights_times_price():
    service, repo, _ = stay_service()
    booking = service.request_booking(1, 3, in_days(5), in_days(8), 2)
    assert booking.total_price == Decimal("300.00")
    assert booking.status == "pending"


def test_booking_check_out_before_check_in_rejected():
    service, repo, _ = stay_service()
    with pytest.raises(ValueError):
        service.request_booking(1, 3, in_days(8), in_days(5), 1)
    repo.create_booking.assert_not_called()


def test_booking_below_minimum_stay_rejected():
    service, repo, _ = stay_service()
    with pytest.raises(ValueError):
        service.request_booking(1, 3, in_days(5), in_days(6), 1)  # 1 night, minimum is 2


def test_booking_in_the_past_rejected():
    service, repo, _ = stay_service()
    with pytest.raises(ValueError):
        service.request_booking(1, 3, in_days(-2), in_days(3), 1)


def test_overlapping_booking_is_a_conflict():
    service, repo, _ = stay_service()
    repo.booking_conflicts.return_value = True
    with pytest.raises(ConflictError):
        service.request_booking(1, 3, in_days(5), in_days(8), 1)
    repo.create_booking.assert_not_called()


def test_booking_unapproved_listing_not_found():
    service, repo, _ = stay_service()
    repo.get_approved_listing.return_value = None
    with pytest.raises(NotFoundError):
        service.request_booking(1, 3, in_days(5), in_days(8), 1)


def test_cancel_pending_booking():
    service, repo, listing = stay_service()
    repo.get_student_booking.return_value = (make_booking("pending"), listing)
    assert service.cancel_booking(4, 3).status == "cancelled"


def test_cannot_cancel_completed_booking():
    service, repo, listing = stay_service()
    repo.get_student_booking.return_value = (make_booking("completed", -10, -5), listing)
    with pytest.raises(ConflictError):
        service.cancel_booking(4, 3)


# ---------------------------------------------------------------- review rules

GOOD_COMMENT = "Great place, quiet and close to campus."


def review_args(**overrides):
    values = dict(booking_id=4, student_id=3, rating=5, comment=GOOD_COMMENT,
                  accurate_listing=True, safe_location=True, clean_and_tidy=False, responsive_host=True)
    values.update(overrides)
    return values


def reviewable_service(status="completed"):
    service, repo, listing = stay_service()
    repo.get_student_booking.return_value = (make_booking(status, -10, -5), listing)
    return service, repo


def test_review_saved_for_completed_stay():
    service, repo = reviewable_service()
    review = service.submit_review(**review_args())
    assert review.rating == 5
    assert review.comment == GOOD_COMMENT
    assert review.responsive_host is True


@pytest.mark.parametrize("rating", [0, 6])
def test_review_rating_must_be_one_to_five(rating):
    service, repo = reviewable_service()
    with pytest.raises(ValueError):
        service.submit_review(**review_args(rating=rating))
    repo.create_review.assert_not_called()


def test_review_comment_too_short_rejected():
    service, repo = reviewable_service()
    with pytest.raises(ValueError):
        service.submit_review(**review_args(comment="a" * 27))  # minimum is 28 characters


def test_cannot_review_twice():
    service, repo = reviewable_service()
    repo.has_review.return_value = True
    with pytest.raises(ConflictError):
        service.submit_review(**review_args())


# ---------------------------------------------------------------- moderation rules (repository mocked)

def moderation_service(status="pending"):
    repo = Mock(spec=ListingRepository)
    repo.get_by_id.return_value = Mock(status=status)
    return ModerationService(repo), repo


def test_approve_records_admin_and_status():
    service, repo = moderation_service()
    service.review_listing(1, 9, "approved")
    kwargs = repo.record_review.call_args.kwargs
    assert kwargs["status"] == "approved"
    assert kwargs["reviewed_by"] == 9


@pytest.mark.parametrize("choice, details", [("", "Some details"), ("Unsafe", ""), ("  ", "  ")])
def test_reject_requires_reason_and_details(choice, details):
    service, repo = moderation_service()
    with pytest.raises(ValueError):
        service.review_listing(1, 9, "rejected", choice, details)
    repo.record_review.assert_not_called()


def test_only_pending_listings_can_be_reviewed():
    service, repo = moderation_service("approved")
    with pytest.raises(ConflictError):
        service.review_listing(1, 9, "approved")


def test_resubmit_only_allowed_for_rejected_listing():
    repo = Mock(spec=ListingRepository)
    repo.get_owned.return_value = Mock(status="approved")
    with pytest.raises(ConflictError):
        ListingService(repo).resubmit_listing(1, 5, _listing())


# ---------------------------------------------------------------- role dependencies

@pytest.mark.parametrize(
    "dependency, allowed, denied",
    [(is_admin_dep, "admin", ["host", "student"]),
     (is_host_dep, "host", ["admin", "student"]),
     (is_student_dep, "student", ["admin", "host"])],
)
async def test_role_dependency_allows_only_its_role(dependency, allowed, denied):
    user = SimpleNamespace(role=allowed)
    assert await dependency(user) is user
    for role in denied:
        with pytest.raises(HTTPException) as caught:
            await dependency(SimpleNamespace(role=role))
        assert caught.value.status_code == 403
