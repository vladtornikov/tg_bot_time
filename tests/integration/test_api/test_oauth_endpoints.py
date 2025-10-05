"""Integration tests for OAuth endpoints."""

import pytest
from httpx import AsyncClient


class TestOAuthEndpoints:
    """Test OAuth API endpoints."""
    
    @pytest.mark.asyncio
    async def test_oauth_google_start_success(self, test_client: AsyncClient):
        """Test starting OAuth flow successfully."""
        response = await test_client.get("/oauth/google/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "oauth_url" in data
        assert "state" in data
        assert "state" in data["oauth_url"]
    
    @pytest.mark.asyncio
    async def test_oauth_google_callback_success(self, test_client: AsyncClient):
        """Test OAuth callback successfully."""
        # First, start OAuth flow to get state
        start_response = await test_client.get("/oauth/google/start")
        start_data = start_response.json()
        state = start_data["state"]
        
        # Mock successful callback
        response = await test_client.get(
            f"/oauth/google/callback?code=test_code&state={state}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_callback_invalid_state(self, test_client: AsyncClient):
        """Test OAuth callback with invalid state."""
        response = await test_client.get(
            "/oauth/google/callback?code=test_code&state=invalid_state"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_callback_missing_code(self, test_client: AsyncClient):
        """Test OAuth callback with missing code."""
        # First, start OAuth flow to get state
        start_response = await test_client.get("/oauth/google/start")
        start_data = start_response.json()
        state = start_data["state"]
        
        response = await test_client.get(f"/oauth/google/callback?state={state}")
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_callback_missing_state(self, test_client: AsyncClient):
        """Test OAuth callback with missing state."""
        response = await test_client.get("/oauth/google/callback?code=test_code")
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_refresh_success(self, test_client: AsyncClient, test_oauth_token):
        """Test refreshing OAuth token successfully."""
        response = await test_client.post(
            "/oauth/google/refresh",
            json={"user_id": test_oauth_token.user_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_refresh_user_not_found(self, test_client: AsyncClient):
        """Test refreshing OAuth token for non-existent user."""
        response = await test_client.post(
            "/oauth/google/refresh",
            json={"user_id": 99999}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_refresh_no_token(self, test_client: AsyncClient, test_user):
        """Test refreshing OAuth token when user has no token."""
        response = await test_client.post(
            "/oauth/google/refresh",
            json={"user_id": test_user.id}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_status_success(self, test_client: AsyncClient, test_oauth_token):
        """Test getting OAuth status successfully."""
        response = await test_client.get(f"/oauth/google/status?user_id={test_oauth_token.user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data
        assert "expires_at" in data
        assert "provider" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_status_user_not_found(self, test_client: AsyncClient):
        """Test getting OAuth status for non-existent user."""
        response = await test_client.get("/oauth/google/status?user_id=99999")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_status_no_token(self, test_client: AsyncClient, test_user):
        """Test getting OAuth status when user has no token."""
        response = await test_client.get(f"/oauth/google/status?user_id={test_user.id}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_disconnect_success(self, test_client: AsyncClient, test_oauth_token):
        """Test disconnecting OAuth successfully."""
        response = await test_client.delete(
            "/oauth/google/disconnect",
            params={"user_id": test_oauth_token.user_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_disconnect_user_not_found(self, test_client: AsyncClient):
        """Test disconnecting OAuth for non-existent user."""
        response = await test_client.delete(
            "/oauth/google/disconnect",
            params={"user_id": 99999}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_disconnect_no_token(self, test_client: AsyncClient, test_user):
        """Test disconnecting OAuth when user has no token."""
        response = await test_client.delete(
            "/oauth/google/disconnect",
            params={"user_id": test_user.id}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_refresh_missing_user_id(self, test_client: AsyncClient):
        """Test refreshing OAuth token with missing user_id."""
        response = await test_client.post("/oauth/google/refresh", json={})
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_status_missing_user_id(self, test_client: AsyncClient):
        """Test getting OAuth status with missing user_id."""
        response = await test_client.get("/oauth/google/status")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_disconnect_missing_user_id(self, test_client: AsyncClient):
        """Test disconnecting OAuth with missing user_id."""
        response = await test_client.delete("/oauth/google/disconnect")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_oauth_google_callback_error_response(self, test_client: AsyncClient):
        """Test OAuth callback with error response."""
        # First, start OAuth flow to get state
        start_response = await test_client.get("/oauth/google/start")
        start_data = start_response.json()
        state = start_data["state"]
        
        response = await test_client.get(
            f"/oauth/google/callback?error=access_denied&state={state}"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "access_denied" in data["error"]
    
    @pytest.mark.asyncio
    async def test_oauth_google_callback_expired_state(self, test_client: AsyncClient):
        """Test OAuth callback with expired state."""
        # Use an old state that would be expired
        old_state = "expired_state_12345"
        
        response = await test_client.get(
            f"/oauth/google/callback?code=test_code&state={old_state}"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "error" in data
