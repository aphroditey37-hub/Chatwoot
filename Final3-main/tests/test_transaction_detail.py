"""
Test Transaction Detail Page Enhancement
Tests for /api/v1/portal/transactions/{order_id} endpoint and frontend navigation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://finplay-admin.preview.emergentagent.com')


class TestTransactionDetailAPI:
    """Tests for transaction detail API endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login and get token"""
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "testclient", "password": "test12345"}
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json().get('access_token')
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_transaction_detail_endpoint_returns_200(self):
        """Test that transaction detail endpoint returns 200 for valid order"""
        response = requests.get(
            f"{BASE_URL}/api/v1/portal/transactions/test-order-001",
            headers=self.headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_transaction_detail_returns_order_data(self):
        """Test that response contains order object with required fields"""
        response = requests.get(
            f"{BASE_URL}/api/v1/portal/transactions/test-order-001",
            headers=self.headers
        )
        data = response.json()
        
        assert "order" in data, "Response missing 'order' field"
        order = data["order"]
        
        # Check required order fields
        assert "order_id" in order, "Order missing 'order_id'"
        assert "order_type" in order, "Order missing 'order_type'"
        assert "status" in order, "Order missing 'status'"
        assert "status_label" in order, "Order missing 'status_label'"
        assert "amount" in order, "Order missing 'amount'"
        assert "created_at" in order, "Order missing 'created_at'"
        
        # Verify values
        assert order["order_id"] == "test-order-001"
        assert order["order_type"] == "deposit"
        assert order["status"] == "approved"
        assert order["amount"] == 100.0
    
    def test_transaction_detail_returns_timeline(self):
        """Test that response contains timeline array with events"""
        response = requests.get(
            f"{BASE_URL}/api/v1/portal/transactions/test-order-001",
            headers=self.headers
        )
        data = response.json()
        
        assert "timeline" in data, "Response missing 'timeline' field"
        timeline = data["timeline"]
        
        assert isinstance(timeline, list), "Timeline should be a list"
        assert len(timeline) >= 1, "Timeline should have at least 1 event"
        
        # Check first event (Order Created)
        first_event = timeline[0]
        assert "event" in first_event, "Event missing 'event' field"
        assert "title" in first_event, "Event missing 'title' field"
        assert "description" in first_event, "Event missing 'description' field"
        assert "timestamp" in first_event, "Event missing 'timestamp' field"
        
        assert first_event["event"] == "order_created"
        assert first_event["title"] == "Order Created"
    
    def test_transaction_detail_returns_summary(self):
        """Test that response contains summary object"""
        response = requests.get(
            f"{BASE_URL}/api/v1/portal/transactions/test-order-001",
            headers=self.headers
        )
        data = response.json()
        
        assert "summary" in data, "Response missing 'summary' field"
        summary = data["summary"]
        
        assert "total_events" in summary, "Summary missing 'total_events'"
        assert "current_status" in summary, "Summary missing 'current_status'"
        assert "is_final" in summary, "Summary missing 'is_final'"
        
        assert summary["total_events"] >= 1
        assert summary["current_status"] == "approved"
        assert summary["is_final"] == True
    
    def test_transaction_detail_404_for_invalid_order(self):
        """Test that endpoint returns 404 for non-existent order"""
        response = requests.get(
            f"{BASE_URL}/api/v1/portal/transactions/invalid-order-xyz",
            headers=self.headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_transaction_detail_401_without_auth(self):
        """Test that endpoint returns 401 without authentication"""
        response = requests.get(
            f"{BASE_URL}/api/v1/portal/transactions/test-order-001"
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_enhanced_transactions_endpoint(self):
        """Test enhanced transactions list endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/portal/transactions/enhanced?limit=10",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "transactions" in data
        assert "total" in data
        assert len(data["transactions"]) >= 1
        
        # Check transaction structure
        tx = data["transactions"][0]
        assert "transaction_id" in tx
        assert "type" in tx
        assert "order_type" in tx
        assert "status" in tx
        assert "amount" in tx


class TestTokenValidation:
    """Tests for token validation endpoint (fixed bug)"""
    
    def test_token_validation_works(self):
        """Test that token validation endpoint works after fix"""
        # Login first
        login_resp = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "testclient", "password": "test12345"}
        )
        token = login_resp.json().get('access_token')
        
        # Validate token
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/validate-token",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Token validation failed: {response.text}"
        data = response.json()
        assert data["valid"] == True
        assert "user_id" in data
        assert "username" in data
        assert data["username"] == "testclient"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
