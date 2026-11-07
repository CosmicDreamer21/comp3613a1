"""Unit tests: each piece tested on its own, no database."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.listing import ListingCreate
from app.services.auth_service import AuthService
from app.utilities.security import create_access_token, encrypt_password, verify_password


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


def test_login_success_returns_token():
    repo = Mock(spec=UserRepository)
    repo.get_by_identifier.return_value = SimpleNamespace(id=7, role="student", password=encrypt_password("secret123"))
    assert AuthService(repo).authenticate_user("maya", "secret123") is not None


def test_login_wrong_password_returns_none():
    repo = Mock(spec=UserRepository)
    repo.get_by_identifier.return_value = SimpleNamespace(id=7, role="student", password=encrypt_password("secret123"))
    assert AuthService(repo).authenticate_user("maya", "nope") is None