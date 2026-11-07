import pytest
from app.models import UserCreate, ListingCreate

def test_user_create_schema_validation():
    """Validates that user creation data parses correctly."""
    user_data = {
        "username": "student_bob",
        "email": "bob@example.com",
        "password": "SecurePassword123"
    }
    user = UserCreate(**user_data)
    assert user.username == "student_bob"
    assert user.email == "bob@example.com"
    assert user.password == "SecurePassword123"

def test_listing_schema_defaults():
    """Validates default schema fields for student housing listings."""
    listing_data = {
        "title": "Cozy Studio near Campus",
        "price_per_month": 500.0,
        "address": "123 University Ave"
    }
    listing = ListingCreate(**listing_data)
    assert listing.title == "Cozy Studio near Campus"
    assert listing.price_per_month == 500.0