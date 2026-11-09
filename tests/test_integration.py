"""Integration tests: real database + real HTTP calls."""
from datetime import date, timedelta
from decimal import Decimal

from app.models.booking import Booking
from app.models.user import User
from app.repositories.listing import ListingRepository
from app.repositories.user import UserRepository
from app.schemas.listing import ListingCreate
from app.utilities.security import encrypt_password

PASSWORD = "StudentStay123"
HASH = encrypt_password(PASSWORD)  # hash once, hashing is deliberately slow


def in_days(n):
    return date.today() + timedelta(days=n)


def make_user(db, username, role="student"):
    user = User(username=username, email=f"{username}@campus.edu", password=HASH, role=role, full_name=username.title())
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


def listing_json(title="Garden Annex"):
    """Body for POST /api/host/listings."""
    return {
        "title": title, "description": "A furnished annex with a study desk.", "city": "St. Augustine",
        "address": "14 Gordon Street", "price_per_night": "100.00", "room_type": "Studio", "amenities": "Wi-Fi",
        "image_url": "", "available_from": in_days(-1).isoformat(), "available_until": in_days(120).isoformat(),
        "minimum_stay_nights": 1,
    }


def make_booking(db, student, listing, check_in, check_out, status="pending"):
    booking = Booking(student_id=student.id, listing_id=listing.id, check_in=check_in, check_out=check_out,
                      guests=1, total_price=Decimal("100.00") * (check_out - check_in).days, status=status)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def api_login(client, username):
    """Log in through the API and return the Authorization header."""
    response = client.post("/api/auth/login", json={"identifier": username, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def book(client, headers, listing_id, check_in=5, check_out=8):
    return client.post("/api/bookings", headers=headers, json={
        "listing_id": listing_id, "check_in": in_days(check_in).isoformat(),
        "check_out": in_days(check_out).isoformat(), "guests": 1})


# ---------------------------------------------------------------- repositories and web pages

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
    response = client.post("/login", data={"identifier": "maya.student", "password": PASSWORD})
    assert response.status_code == 303
    assert "access_token" in client.cookies


def test_wrong_password_sets_no_cookie(db, client):
    make_user(db, "maya.student")
    client.post("/login", data={"identifier": "maya.student", "password": "wrong"})
    assert "access_token" not in client.cookies


def test_student_page_needs_login(client):
    response = client.get("/student/listings")
    assert response.status_code == 401
    assert "Session expired" in response.text


def test_host_cannot_open_student_page(db, client):
    make_user(db, "host1", "host")
    client.post("/login", data={"identifier": "host1", "password": PASSWORD})
    assert client.get("/student/listings").status_code == 403


def test_student_sees_only_approved_listings(db, client):
    host = make_user(db, "host1", "host")
    make_user(db, "maya.student")
    repo = ListingRepository(db)
    repo.create(host.id, listing_data("Approved Room"), status="approved")
    repo.create(host.id, listing_data("Pending Room"))
    client.post("/login", data={"identifier": "maya.student", "password": PASSWORD})
    page = client.get("/student/listings").text
    assert "Approved Room" in page
    assert "Pending Room" not in page


# ---------------------------------------------------------------- API: login and roles

def test_api_login_returns_bearer_token_and_role(db, client):
    make_user(db, "rivera.host", "host")
    response = client.post("/api/auth/login", json={"identifier": "rivera.host", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["role"] == "host"


def test_api_wrong_password_returns_401(db, client):
    make_user(db, "maya.student")
    response = client.post("/api/auth/login", json={"identifier": "maya.student", "password": "wrong"})
    assert response.status_code == 401


def test_api_needs_a_token(client):
    assert client.get("/api/listings").status_code == 401


def test_api_endpoints_reject_the_wrong_role(db, client):
    make_user(db, "maya.student")
    make_user(db, "rivera.host", "host")
    student, host = api_login(client, "maya.student"), api_login(client, "rivera.host")
    assert client.post("/api/host/listings", headers=student, json=listing_json()).status_code == 403
    assert client.get("/api/admin/listings", headers=host).status_code == 403
    assert client.get("/api/listings", headers=host).status_code == 403


# ---------------------------------------------------------------- API: list and moderate accommodation

def test_host_creates_listing_which_starts_pending(db, client):
    make_user(db, "rivera.host", "host")
    response = client.post("/api/host/listings", headers=api_login(client, "rivera.host"), json=listing_json())
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_invalid_listing_returns_422(db, client):
    make_user(db, "rivera.host", "host")
    body = listing_json()
    body["price_per_night"] = "0"
    assert client.post("/api/host/listings", headers=api_login(client, "rivera.host"), json=body).status_code == 422


def test_admin_approval_makes_listing_visible_to_students(db, client):
    make_user(db, "rivera.host", "host")
    make_user(db, "admin01", "admin")
    make_user(db, "maya.student")
    host, admin, student = (api_login(client, n) for n in ("rivera.host", "admin01", "maya.student"))
    listing = client.post("/api/host/listings", headers=host, json=listing_json("Garden Annex")).json()
    assert client.get("/api/listings", headers=student).json() == []  # hidden until approved
    approved = client.patch(f"/api/admin/listings/{listing['id']}", headers=admin, json={"status": "approved"})
    assert approved.status_code == 200
    assert [l["title"] for l in client.get("/api/listings", headers=student).json()] == ["Garden Annex"]


def test_admin_rejection_needs_a_reason(db, client):
    host = make_user(db, "rivera.host", "host")
    make_user(db, "admin01", "admin")
    listing = ListingRepository(db).create(host.id, listing_data())
    admin = api_login(client, "admin01")
    no_reason = client.patch(f"/api/admin/listings/{listing.id}", headers=admin, json={"status": "rejected"})
    assert no_reason.status_code == 422
    with_reason = client.patch(f"/api/admin/listings/{listing.id}", headers=admin, json={
        "status": "rejected", "rejection_reason_choice": "Photos", "rejection_reason_details": "Add a photo"})
    assert with_reason.status_code == 200
    assert with_reason.json()["status"] == "rejected"


# ---------------------------------------------------------------- API: book accommodation

def test_student_books_listing_with_correct_total(db, client):
    host, _ = make_user(db, "rivera.host", "host"), make_user(db, "maya.student")
    listing = ListingRepository(db).create(host.id, listing_data(), status="approved")
    response = book(client, api_login(client, "maya.student"), listing.id, 5, 8)
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert Decimal(response.json()["total_price"]) == Decimal("300.00")


def test_overlapping_booking_returns_409(db, client):
    host = make_user(db, "rivera.host", "host")
    make_user(db, "maya.student")
    make_user(db, "omar.student")
    listing = ListingRepository(db).create(host.id, listing_data(), status="approved")
    assert book(client, api_login(client, "maya.student"), listing.id, 5, 10).status_code == 201
    assert book(client, api_login(client, "omar.student"), listing.id, 7, 12).status_code == 409


def test_host_cannot_book(db, client):
    host = make_user(db, "rivera.host", "host")
    listing = ListingRepository(db).create(host.id, listing_data(), status="approved")
    assert book(client, api_login(client, "rivera.host"), listing.id).status_code == 403


def test_student_cannot_open_or_book_an_unapproved_listing(db, client):
    host = make_user(db, "rivera.host", "host")
    make_user(db, "maya.student")
    pending = ListingRepository(db).create(host.id, listing_data("Pending Room"))
    headers = api_login(client, "maya.student")
    assert client.get(f"/api/listings/{pending.id}", headers=headers).status_code == 404
    assert book(client, headers, pending.id).status_code == 404


def test_host_confirms_booking_request(db, client):
    host, student = make_user(db, "rivera.host", "host"), make_user(db, "maya.student")
    listing = ListingRepository(db).create(host.id, listing_data(), status="approved")
    booking = make_booking(db, student, listing, in_days(5), in_days(8))
    headers = api_login(client, "rivera.host")
    assert [b["id"] for b in client.get("/api/host/bookings", headers=headers).json()] == [booking.id]
    confirmed = client.patch(f"/api/host/bookings/{booking.id}", headers=headers, json={"status": "confirmed"})
    assert confirmed.json()["status"] == "confirmed"
    assert client.patch(f"/api/host/bookings/{booking.id}", headers=headers, json={"status": "confirmed"}).status_code == 409


def test_student_cancels_booking_only_once(db, client):
    host, student = make_user(db, "rivera.host", "host"), make_user(db, "maya.student")
    listing = ListingRepository(db).create(host.id, listing_data(), status="approved")
    booking = make_booking(db, student, listing, in_days(5), in_days(8))
    headers = api_login(client, "maya.student")
    first = client.patch(f"/api/bookings/{booking.id}", headers=headers, json={"status": "cancelled"})
    assert first.json()["status"] == "cancelled"
    assert client.patch(f"/api/bookings/{booking.id}", headers=headers, json={"status": "cancelled"}).status_code == 409


def test_student_cannot_cancel_someone_elses_booking(db, client):
    host, owner = make_user(db, "rivera.host", "host"), make_user(db, "maya.student")
    make_user(db, "omar.student")
    listing = ListingRepository(db).create(host.id, listing_data(), status="approved")
    booking = make_booking(db, owner, listing, in_days(5), in_days(8))
    response = client.patch(f"/api/bookings/{booking.id}", headers=api_login(client, "omar.student"), json={"status": "cancelled"})
    assert response.status_code == 404


# ---------------------------------------------------------------- API: reviews

def test_student_reviews_completed_stay_once(db, client):
    host, student = make_user(db, "rivera.host", "host"), make_user(db, "maya.student")
    listing = ListingRepository(db).create(host.id, listing_data(), status="approved")
    booking = make_booking(db, student, listing, in_days(-10), in_days(-5), "completed")
    headers = api_login(client, "maya.student")
    body = {"rating": 4, "comment": "Great place, quiet and close to campus.", "accurate_listing": True}
    first = client.post(f"/api/bookings/{booking.id}/review", headers=headers, json=body)
    assert first.status_code == 201
    assert first.json()["rating"] == 4
    assert client.post(f"/api/bookings/{booking.id}/review", headers=headers, json=body).status_code == 409
    detail = client.get(f"/api/listings/{listing.id}", headers=headers).json()
    assert (detail["average_rating"], detail["review_count"]) == (4.0, 1)


def test_review_needs_a_completed_stay_and_valid_input(db, client):
    host, student = make_user(db, "rivera.host", "host"), make_user(db, "maya.student")
    listing = ListingRepository(db).create(host.id, listing_data(), status="approved")
    upcoming = make_booking(db, student, listing, in_days(5), in_days(8))
    done = make_booking(db, student, listing, in_days(-10), in_days(-5), "completed")
    headers = api_login(client, "maya.student")
    good = {"rating": 5, "comment": "Great place, quiet and close to campus."}
    assert client.post(f"/api/bookings/{upcoming.id}/review", headers=headers, json=good).status_code == 409
    assert client.post(f"/api/bookings/{done.id}/review", headers=headers, json={**good, "rating": 6}).status_code == 422
    assert client.post(f"/api/bookings/{done.id}/review", headers=headers, json={**good, "comment": "Nice"}).status_code == 422


# ---------------------------------------------------------------- end to end

def test_full_journey_host_admin_student(db, client):
    make_user(db, "rivera.host", "host")
    make_user(db, "admin01", "admin")
    make_user(db, "maya.student")
    host, admin, student = (api_login(client, n) for n in ("rivera.host", "admin01", "maya.student"))
    listing = client.post("/api/host/listings", headers=host, json=listing_json("Journey House")).json()
    client.patch(f"/api/admin/listings/{listing['id']}", headers=admin, json={"status": "approved"})
    found = client.get("/api/listings", params={"query": "journey"}, headers=student).json()
    assert [l["id"] for l in found] == [listing["id"]]
    booking = book(client, student, listing["id"], 5, 7).json()
    client.patch(f"/api/host/bookings/{booking['id']}", headers=host, json={"status": "confirmed"})
    mine = client.get("/api/bookings", headers=student).json()
    assert [(b["id"], b["status"]) for b in mine] == [(booking["id"], "confirmed")]
