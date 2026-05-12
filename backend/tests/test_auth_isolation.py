from fastapi.testclient import TestClient


def _admin_headers(db_session):
    from app.models.recruiter import Recruiter
    from app.services.auth import create_access_token, hash_password

    admin = Recruiter(
        id="auth-test-admin",
        email="admin@signalstack.dev",
        password=hash_password("Password@123"),
        role="admin",
        name="Admin",
    )
    db_session.merge(admin)
    db_session.flush()
    return {"Authorization": f"Bearer {create_access_token(admin)}"}


def _login(client: TestClient, email: str, password: str = "Password@123") -> tuple[dict, dict]:
    response = client.post("/recruiter/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload["recruiter"]


def _invite_and_signup(client: TestClient, admin_headers: dict, email: str) -> tuple[dict, dict]:
    invite_response = client.post("/recruiter/invites", headers=admin_headers, json={"email": email})
    assert invite_response.status_code == 200, invite_response.text
    invite = invite_response.json()
    signup_response = client.post(
        "/recruiter/signup",
        json={
            "email": email,
            "password": "Password@123",
            "invite_token": invite["token"],
        },
    )
    assert signup_response.status_code == 200, signup_response.text
    payload = signup_response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload["recruiter"]


def test_recruiters_only_see_their_own_jobs(app_with_overrides, db_session):
    app, db, _, _ = app_with_overrides

    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[db.get_db] = _get_db
    try:
        with TestClient(app) as client:
            unknown_login = client.post(
                "/recruiter/login",
                json={"email": "unknown-recruiter@signalstack.dev", "password": "Password@123"},
            )
            assert unknown_login.status_code == 401

            admin_headers = _admin_headers(db_session)
            recruiter_a_headers, recruiter_a = _invite_and_signup(
                client,
                admin_headers,
                "alpha-recruiter@signalstack.dev",
            )
            recruiter_b_headers, recruiter_b = _invite_and_signup(
                client,
                admin_headers,
                "beta-recruiter@signalstack.dev",
            )

            job_a = client.post(
                "/jobs",
                headers=recruiter_a_headers,
                json={
                    "title": "AI Engineer Intern",
                    "description": "Build applied AI systems.",
                    "company": "Alpha",
                    "location": "Remote",
                    "category": "Software Engineering",
                },
            )
            assert job_a.status_code == 200, job_a.text

            job_b = client.post(
                "/jobs",
                headers=recruiter_b_headers,
                json={
                    "title": "Backend Engineer Intern",
                    "description": "Build reliable APIs.",
                    "company": "Beta",
                    "location": "Remote",
                    "category": "Software Engineering",
                },
            )
            assert job_b.status_code == 200, job_b.text

            job_a_payload = job_a.json()
            job_b_payload = job_b.json()
            assert job_a_payload["recruiter_id"] == recruiter_a["id"]
            assert job_b_payload["recruiter_id"] == recruiter_b["id"]

            recruiter_a_jobs = client.get("/jobs?include_archived=true", headers=recruiter_a_headers)
            assert recruiter_a_jobs.status_code == 200
            assert {job["id"] for job in recruiter_a_jobs.json()} == {job_a_payload["id"]}

            blocked = client.get(f"/jobs/{job_b_payload['id']}", headers=recruiter_a_headers)
            assert blocked.status_code == 404

            admin_only = client.get("/admin/signal-weights", headers=recruiter_a_headers)
            assert admin_only.status_code == 403
    finally:
        app.dependency_overrides.clear()
