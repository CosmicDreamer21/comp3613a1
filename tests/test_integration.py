"""Integration tests: real database + real HTTP calls."""
from datetime import date, timedelta
from decimal import Decimal

from app.models.user import User
from app.repositories.listing import ListingRepository
from app.repositories.user import UserRepository
from app.schemas.listing import ListingCreate
from app.utilities.security import encrypt_password


def make_user(db, username, role="student"):
    user = User(username=username, email=f"{username}@campus.edu",
                password=encrypt_password("StudentStay123"), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def listing_data(title="Cedar House"):
    return ListingCreate(
        title=title, description="A bright private room.", city="St. Augustine",
        address="12 Cedar Avenue", price_per_night=Decimal("100"), room_type="Private room",
        available_from=date.today() - timedelta(days=5), available_until=date.today() + timedelta(days=200),
    )


def test_create_and_fetch_user(db):
    make_user(db, "bob")
    assert UserRepository(db).get_by_username("bob").email == "bob@campus.edu"


def test_new_listing_is_pending(db):
    host = make_user(db, "host1", "host")
    listing = ListingRepository(db).create(host.id, listing_data())
    assert listing.status == "pending"
    assert listing.host_id == host.id


def test_login_redirects_student_and_sets_cookie(db, client):
    make_user(db, "maya.student")
    response = client.post("/login", data={"identifier": "maya.student", "password": "StudentStay123"})
    assert response.status_code == 303
    assert "access_token" in client.cookies


def test_wrong_password_sets_no_cookie(db, client):
    make_user(db, "maya.student")
    client.post("/login", data={"identifier": "maya.student", "password": "wrong"})
    assert "access_token" not in client.cookies


def test_student_page_needs_login(client):
    # the unmodified A1 app shows its 401 "Session expired" page for anonymous visitors
    assert "Session expired" in client.get("/student/listings").text


def test_host_cannot_open_student_page(db, client):
    make_user(db, "host1", "host")
    client.post("/login", data={"identifier": "host1", "password": "StudentStay123"})
    assert client.get("/student/listings").status_code == 403


def test_student_sees_only_approved_listings(db, client):
    host = make_user(db, "host1", "host")
    make_user(db, "maya.student")
    repo = ListingRepository(db)
    repo.create(host.id, listing_data("Approved Room"), status="approved")
    repo.create(host.id, listing_data("Pending Room"))
    client.post("/login", data={"identifier": "maya.student", "password": "StudentStay123"})
    page = client.get("/student/listings").text
    assert "Approved Room" in page
    assert "Pending Room" not in page