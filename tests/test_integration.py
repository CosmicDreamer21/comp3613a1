import pytest

def test_user_registration_workflow(client):
    """Tests POST /register form submission and response."""
    response = client.post(
        "/register",
        data={
            "username": "integration_user",
            "email": "integration@example.com",
            "password": "Password123"
        }
    )
    assert response.status_code in [200, 201, 303]

def test_get_student_listings(client):
    """Tests GET /student/listings view returns successful response."""
    response = client.get("/student/listings")
    assert response.status_code == 200

def test_submit_booking_request(client):
    """Tests POST /student/listings/{listing_id}/book endpoint."""
    response = client.post(
        "/student/listings/1/book",
        data={
            "start_date": "2026-09-01",
            "end_date": "2027-04-30"
        }
    )
    assert response.status_code in [200, 303]