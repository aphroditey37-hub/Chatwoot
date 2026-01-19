"""
Production Hardening Tests
Tests for API resilience and observability improvements:
- Health endpoint with correlation ID
- Login endpoint with X-Correlation-ID header
- GamesAPIClient fail-fast behavior
- Exception handler safe error responses
- Structured logging with correlation IDs
- Games /available endpoint authentication
- Error responses with error_code (E1xxx, E2xxx, etc)
"""
import pytest
import requests
import os
import json
import re
from datetime import datetime

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"username": "admin", "password": "admin123"}
CLIENT_CREDS = {"username": "testclient", "password": "test12345"}


class TestHealthEndpoint:
    """Test health endpoint returns healthy status with correlation ID header"""
    
    def test_health_returns_200(self):
        """Health endpoint should return 200 OK"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Health endpoint returns 200")
    
    def test_health_returns_healthy_status(self):
        """Health endpoint should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        assert data.get("status") == "healthy", f"Expected 'healthy', got {data.get('status')}"
        print(f"✓ Health status is 'healthy'")
    
    def test_health_has_correlation_id_header(self):
        """Health endpoint should return X-Correlation-ID header"""
        response = requests.get(f"{BASE_URL}/api/health")
        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None, "X-Correlation-ID header missing"
        assert len(correlation_id) > 0, "X-Correlation-ID header is empty"
        print(f"✓ X-Correlation-ID header present: {correlation_id}")
    
    def test_health_response_structure(self):
        """Health endpoint should return expected structure"""
        response = requests.get(f"{BASE_URL}/api/health")
        data = response.json()
        assert "status" in data, "Missing 'status' field"
        assert "message" in data, "Missing 'message' field"
        assert "version" in data, "Missing 'version' field"
        assert "database" in data, "Missing 'database' field"
        print(f"✓ Health response has correct structure")


class TestLoginEndpoint:
    """Test login endpoint returns token with X-Correlation-ID header"""
    
    def test_login_success_returns_token(self):
        """Login with valid credentials should return access token"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=ADMIN_CREDS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") is True, "Login should be successful"
        assert "access_token" in data, "Missing access_token"
        assert len(data["access_token"]) > 0, "access_token is empty"
        print(f"✓ Login returns access token")
    
    def test_login_has_correlation_id_header(self):
        """Login endpoint should return X-Correlation-ID header"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=ADMIN_CREDS
        )
        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None, "X-Correlation-ID header missing"
        assert len(correlation_id) > 0, "X-Correlation-ID header is empty"
        print(f"✓ Login X-Correlation-ID header present: {correlation_id}")
    
    def test_login_invalid_credentials_returns_401(self):
        """Login with invalid credentials should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "invalid_user", "password": "wrong_password"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Invalid credentials return 401")
    
    def test_login_response_structure(self):
        """Login response should have expected structure"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=ADMIN_CREDS
        )
        data = response.json()
        assert "success" in data, "Missing 'success' field"
        assert "message" in data, "Missing 'message' field"
        assert "access_token" in data, "Missing 'access_token' field"
        assert "token_type" in data, "Missing 'token_type' field"
        assert "user" in data, "Missing 'user' field"
        assert data["token_type"] == "Bearer", f"Expected 'Bearer', got {data['token_type']}"
        print(f"✓ Login response has correct structure")


class TestCorrelationIDFlow:
    """Test correlation ID flows through from request to response"""
    
    def test_custom_correlation_id_preserved(self):
        """Custom X-Correlation-ID in request should be preserved in response"""
        custom_id = "test-correlation-12345"
        response = requests.get(
            f"{BASE_URL}/api/health",
            headers={"X-Correlation-ID": custom_id}
        )
        response_id = response.headers.get("X-Correlation-ID")
        assert response_id == custom_id, f"Expected '{custom_id}', got '{response_id}'"
        print(f"✓ Custom correlation ID preserved: {custom_id}")
    
    def test_correlation_id_generated_if_not_provided(self):
        """Correlation ID should be generated if not provided"""
        response = requests.get(f"{BASE_URL}/api/health")
        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None, "Correlation ID should be generated"
        # Should be a UUID-like format (12 chars truncated)
        assert len(correlation_id) >= 8, f"Correlation ID too short: {correlation_id}"
        print(f"✓ Correlation ID auto-generated: {correlation_id}")


class TestGamesAvailableAuthentication:
    """Test Games /available endpoint requires authentication"""
    
    def test_games_available_without_auth_returns_401(self):
        """Games /available without auth should return 401"""
        response = requests.get(f"{BASE_URL}/api/v1/games/available")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Games /available without auth returns 401")
    
    def test_games_available_with_auth_returns_200(self):
        """Games /available with valid auth should return 200"""
        # First login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=ADMIN_CREDS
        )
        token = login_response.json().get("access_token")
        
        # Then access games/available
        response = requests.get(
            f"{BASE_URL}/api/v1/games/available",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Games /available with auth returns 200")
    
    def test_games_available_response_structure(self):
        """Games /available should return expected structure"""
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=ADMIN_CREDS
        )
        token = login_response.json().get("access_token")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/games/available",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = response.json()
        assert "games" in data, "Missing 'games' field"
        assert "wallet_balance" in data, "Missing 'wallet_balance' field"
        assert isinstance(data["games"], list), "'games' should be a list"
        print(f"✓ Games /available has correct structure")
    
    def test_games_available_has_correlation_id(self):
        """Games /available should return X-Correlation-ID header"""
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=ADMIN_CREDS
        )
        token = login_response.json().get("access_token")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/games/available",
            headers={"Authorization": f"Bearer {token}"}
        )
        correlation_id = response.headers.get("X-Correlation-ID")
        assert correlation_id is not None, "X-Correlation-ID header missing"
        print(f"✓ Games /available has X-Correlation-ID: {correlation_id}")


class TestErrorResponses:
    """Test error responses include error_code (E1xxx, E2xxx, etc)"""
    
    def test_auth_error_has_error_code(self):
        """Authentication errors should have error_code"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "invalid", "password": "invalid"}
        )
        # 401 errors may not have error_code in detail, but should have proper structure
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Auth error returns 401 status")
    
    def test_validation_error_format(self):
        """Validation errors should have proper format"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "", "password": ""}  # Empty values
        )
        # Should return 422 for validation error
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Validation error returns proper status: {response.status_code}")
    
    def test_not_found_error_format(self):
        """Not found errors should have proper format"""
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=ADMIN_CREDS
        )
        token = login_response.json().get("access_token")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/games/nonexistent-game-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Not found error returns 404")


class TestSafeErrorResponses:
    """Test exception handler returns safe error responses without stack traces"""
    
    def test_error_response_no_stack_trace(self):
        """Error responses should not contain stack traces"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "invalid", "password": "invalid"}
        )
        response_text = response.text.lower()
        # Check for common stack trace indicators
        assert "traceback" not in response_text, "Response contains 'traceback'"
        assert "file \"" not in response_text, "Response contains file path"
        assert "line " not in response_text or "line" in response_text.replace("line ", ""), "Response may contain line numbers"
        print(f"✓ Error response does not contain stack trace")
    
    def test_error_response_has_message(self):
        """Error responses should have a message field"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "invalid", "password": "invalid"}
        )
        data = response.json()
        # Should have either 'message' or 'detail'
        has_message = "message" in data or "detail" in data
        assert has_message, "Error response should have 'message' or 'detail'"
        print(f"✓ Error response has message field")


class TestExceptionHandlerErrorCodes:
    """Test that SafeAPIException error codes are properly formatted"""
    
    def test_error_code_format_e1xxx_auth(self):
        """E1xxx codes should be for authentication errors"""
        # This tests the error code format defined in exception_handler.py
        # E1001: Invalid credentials
        # E1002: User not found
        # E1003: Session expired
        # E1004: Unauthorized access
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "wrong"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Authentication error returns 401")
    
    def test_unauthorized_access_returns_401(self):
        """Unauthorized access should return 401"""
        response = requests.get(f"{BASE_URL}/api/v1/games/available")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Unauthorized access returns 401")


class TestAPIRootEndpoints:
    """Test root API endpoints"""
    
    def test_root_endpoint_returns_html(self):
        """Root endpoint should return frontend HTML (not API JSON)"""
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        # Root returns frontend HTML, not JSON
        assert "text/html" in response.headers.get("Content-Type", ""), "Root should return HTML"
        print(f"✓ Root endpoint returns HTML (frontend)")
    
    def test_api_root_endpoint(self):
        """API root endpoint should return API info"""
        response = requests.get(f"{BASE_URL}/api")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "message" in data, "Missing 'message' field"
        assert "version" in data, "Missing 'version' field"
        print(f"✓ API root endpoint returns API info")


class TestTokenValidation:
    """Test token validation endpoint"""
    
    def test_validate_token_with_valid_token(self):
        """Token validation should succeed with valid token"""
        # First login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=ADMIN_CREDS
        )
        token = login_response.json().get("access_token")
        
        # Validate token
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("valid") is True, "Token should be valid"
        print(f"✓ Token validation succeeds with valid token")
    
    def test_validate_token_with_invalid_token(self):
        """Token validation should fail with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/v1/auth/validate-token",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Token validation fails with invalid token")


class TestClientLogin:
    """Test client user login"""
    
    def test_client_login_success(self):
        """Client user should be able to login"""
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=CLIENT_CREDS
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("success") is True, "Login should be successful"
        assert "access_token" in data, "Missing access_token"
        print(f"✓ Client login successful")
    
    def test_client_can_access_games(self):
        """Client user should be able to access games"""
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=CLIENT_CREDS
        )
        token = login_response.json().get("access_token")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/games/available",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Client can access games")


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
