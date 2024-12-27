import pytest
from datetime import datetime, timedelta
import jwt

from src.api_service.core.security import (
    create_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    ALGORITHM
)
from src.config import settings

class TestPasswordHashing:
    def test_password_hash_creation(self):
        """Test that password hashing creates different hashes for same password"""
        password = "mysecretpassword123"
        hash1 = create_password_hash(password)
        hash2 = create_password_hash(password)

        # Same password should create different hashes
        assert hash1 != hash2
        # Hashes should be strings
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)
        # Hashes should be of substantial length
        assert len(hash1) > 20

    def test_password_verification(self):
        """Test password verification against known hashes"""
        password = "mysecretpassword123"
        wrong_password = "wrongpassword123"
        hashed = create_password_hash(password)

        # Correct password should verify
        assert verify_password(password, hashed) is True
        # Wrong password should not verify
        assert verify_password(wrong_password, hashed) is False

    def test_empty_password_handling(self):
        """Test handling of empty passwords"""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            create_password_hash("")

    def test_password_minimum_length(self):
        """Test handling of very short passwords"""
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            create_password_hash("short")

    def test_password_whitespace_handling(self):
        """Test handling of passwords with only whitespace"""
        with pytest.raises(ValueError, match="Password cannot be only whitespace"):
            create_password_hash("   \n\t   ")

class TestJWTTokens:
    def test_access_token_creation(self):
        """Test creation of access tokens"""
        user_id = 123
        token = create_access_token(subject=user_id)

        # Token should be a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify token contents
        decoded = decode_token(token)
        assert str(user_id) == decoded["sub"]
        assert decoded["type"] == "access"
        assert "exp" in decoded

    def test_token_expiration(self):
        """Test token expiration handling"""
        # Create a token that expires in 1 second
        token = create_access_token(
            subject="test",
            expires_delta=timedelta(seconds=1)
        )

        # Token should be valid immediately
        decoded = decode_token(token)
        assert decoded["sub"] == "test"

        # Wait for token to expire
        import time
        time.sleep(2)

        # Token should be expired now
        with pytest.raises(jwt.PyJWTError):
            decode_token(token)

    def test_custom_expiration(self):
        """Test custom expiration times"""
        expires_in = timedelta(minutes=30)
        token = create_access_token(
            subject="test",
            expires_delta=expires_in
        )

        decoded = decode_token(token)
        created_at = datetime.utcfromtimestamp(decoded["exp"]) - expires_in

        # Check if expiration time is approximately correct
        # (allowing 5 seconds tolerance for test execution time)
        assert abs((datetime.utcnow() - created_at).total_seconds()) < 5

    def test_invalid_token_handling(self):
        """Test handling of invalid tokens"""
        # Test with malformed token
        with pytest.raises(jwt.PyJWTError):
            decode_token("invalid.token.format")

        # Test with token signed with different key
        wrong_token = jwt.encode(
            {"sub": "test"},
            "wrong_secret_key",
            algorithm=ALGORITHM
        )
        with pytest.raises(jwt.PyJWTError):
            decode_token(wrong_token)

    def test_token_verification_options(self):
        """Test token verification options"""
        # Create an expired token
        token = create_access_token(
            subject="test",
            expires_delta=timedelta(seconds=-1)
        )

        # Should raise error with expiration verification
        with pytest.raises(jwt.PyJWTError):
            decode_token(token, verify_exp=True)

        # Should not raise error when skipping expiration verification
        decoded = decode_token(token, verify_exp=False)
        assert decoded["sub"] == "test"

    def test_token_subject_validation(self):
        """Test validation of token subjects"""
        # Test various subject types
        subjects = [123, "user@example.com", "username-123"]
        for subject in subjects:
            token = create_access_token(subject=subject)
            decoded = decode_token(token)
            assert str(subject) == decoded["sub"]

    def test_token_tampering(self):
        """Test detection of tampered tokens"""
        token = create_access_token(subject="test")
        # Modify the middle (payload) section of the token
        parts = token.split('.')
        parts[1] = parts[1][:-4] + "XXXX"  # Tamper with the payload
        tampered_token = '.'.join(parts)

        with pytest.raises(jwt.InvalidTokenError):
            decode_token(tampered_token)

@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to modify settings for tests"""
    monkeypatch.setattr(settings, "SECRET_KEY", "test_secret_key")
    monkeypatch.setattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    return settings

class TestSecurityHeaders:
    def test_password_hash_timing(self):
        """Test that password hashing has consistent timing"""
        import time
        password = "test_password123"

        # Measure multiple hash operations to ensure consistent timing
        timings = []
        for _ in range(10):
            start = time.perf_counter()
            create_password_hash(password)
            end = time.perf_counter()
            timings.append(end - start)

        # Check timing consistency (within reasonable bounds)
        avg_time = sum(timings) / len(timings)
        for timing in timings:
            assert abs(timing - avg_time) < 0.1  # 100ms variance allowed

def test_settings_integration(mock_settings):
    """Test integration with application settings"""
    token = create_access_token(subject="test")
    decoded = decode_token(token)

    # Verify token was created with test settings
    assert decoded["sub"] == "test"

    # Verify expiration time matches settings
    # Convert exp timestamp to UTC datetime for consistent comparison
    exp_time = datetime.utcfromtimestamp(decoded["exp"])
    expected_exp = datetime.utcnow() + timedelta(minutes=mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Allow 5 seconds tolerance
    assert abs((exp_time - expected_exp).total_seconds()) < 5
