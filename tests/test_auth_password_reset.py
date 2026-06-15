"""Tests for forgot-password and reset-password endpoints."""

from tests.conftest import (
    PASSWORD_RESET_MESSAGE,
    expire_password_reset_token,
    extract_token_from_reset_link,
)


class TestForgotPassword:
    def test_forgot_password_known_email(
        self, client, registered_user, mock_password_reset_email
    ):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": registered_user["email"]},
        )
        assert response.status_code == 200
        assert response.json()["message"] == PASSWORD_RESET_MESSAGE
        assert len(mock_password_reset_email) == 1
        assert mock_password_reset_email[0]["email"] == registered_user["email"]

    def test_forgot_password_unknown_email(self, client, mock_password_reset_email):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "unknown@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == PASSWORD_RESET_MESSAGE
        assert len(mock_password_reset_email) == 0


class TestResetPassword:
    def test_reset_password_success(
        self, client, registered_user, mock_password_reset_email
    ):
        old_password = registered_user["password"]
        new_password = "New@Pass456"

        client.post(
            "/api/v1/auth/forgot-password",
            json={"email": registered_user["email"]},
        )
        token = extract_token_from_reset_link(
            mock_password_reset_email[0]["reset_link"]
        )

        validate_response = client.get(
            "/api/v1/auth/reset-password/validate",
            params={"token": token},
        )
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        reset_response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": new_password},
        )
        assert reset_response.status_code == 200
        assert reset_response.json()["message"] == "Password reset successfully"

        old_login = client.post(
            "/api/v1/auth/login",
            data={"username": registered_user["email"], "password": old_password},
        )
        assert old_login.status_code == 401

        new_login = client.post(
            "/api/v1/auth/login",
            data={"username": registered_user["email"], "password": new_password},
        )
        assert new_login.status_code == 200
        assert "access_token" in new_login.json()

    def test_reset_password_expired_token(
        self, client, registered_user, mock_password_reset_email
    ):
        client.post(
            "/api/v1/auth/forgot-password",
            json={"email": registered_user["email"]},
        )
        token = extract_token_from_reset_link(
            mock_password_reset_email[0]["reset_link"]
        )
        expire_password_reset_token(token)

        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "New@Pass456"},
        )
        assert response.status_code == 400
        assert "Invalid or expired reset token" in response.json()["detail"]

    def test_reset_password_reused_token(
        self, client, registered_user, mock_password_reset_email
    ):
        client.post(
            "/api/v1/auth/forgot-password",
            json={"email": registered_user["email"]},
        )
        token = extract_token_from_reset_link(
            mock_password_reset_email[0]["reset_link"]
        )

        first_reset = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "New@Pass456"},
        )
        assert first_reset.status_code == 200

        second_reset = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "Another@Pass789"},
        )
        assert second_reset.status_code == 400
        assert "Invalid or expired reset token" in second_reset.json()["detail"]
