import pytest
from pydantic import ValidationError
from app.models.user import UserCreate, UserRole, ResetPasswordRequest

def test_user_create_valid_password():
    # Happy path: should not raise
    UserCreate(
        email="john@example.com",
        name="John Doe",
        password="Valid@Password123",
        role=UserRole.USER
    )

def test_user_create_password_contains_name():
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="john@example.com",
            name="John",
            password="John@Password123",
            role=UserRole.USER
        )
    assert "Password must not contain your name" in str(exc_info.value)

def test_user_create_password_contains_email_prefix():
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="johnny@example.com",
            name="John Doe",
            password="Johnny@Password123",
            role=UserRole.USER
        )
    assert "Password must not contain your email prefix" in str(exc_info.value)

def test_user_create_password_missing_uppercase():
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="john@example.com",
            name="John Doe",
            password="valid@password123",
            role=UserRole.USER
        )
    assert "Password must contain at least one uppercase letter" in str(exc_info.value)

def test_user_create_password_missing_lowercase():
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="john@example.com",
            name="John Doe",
            password="VALID@PASSWORD123",
            role=UserRole.USER
        )
    assert "Password must contain at least one lowercase letter" in str(exc_info.value)

def test_user_create_password_missing_digit():
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="john@example.com",
            name="John Doe",
            password="Valid@Password",
            role=UserRole.USER
        )
    assert "Password must contain at least one digit" in str(exc_info.value)

def test_user_create_password_missing_special_char():
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="john@example.com",
            name="John Doe",
            password="ValidPassword123",
            role=UserRole.USER
        )
    assert "Password must contain at least one special character" in str(exc_info.value)

def test_user_create_password_repeated_chars():
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="john@example.com",
            name="John Doe",
            password="Valiidd@Paaaaassword123",
            role=UserRole.USER
        )
    assert "Password must not contain repeated characters" in str(exc_info.value)

def test_user_create_password_sequential_chars():
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            email="john@example.com",
            name="John Doe",
            password="Valid@Password12345",
            role=UserRole.USER
        )
    assert "Password must not contain common sequences" in str(exc_info.value)

def test_reset_password_request_validation():
    # Happy path: should not raise
    ResetPasswordRequest(
        token="some-token",
        new_password="Valid@Password123"
    )

    # Missing special char should fail
    with pytest.raises(ValidationError) as exc_info:
        ResetPasswordRequest(
            token="some-token",
            new_password="ValidPassword123"
        )
    assert "Password must contain at least one special character" in str(exc_info.value)
