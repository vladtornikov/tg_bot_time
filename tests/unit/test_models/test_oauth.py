"""Unit tests for OAuth model."""

import pytest
from datetime import datetime, timedelta

from src.models.oauth import OAuthToken


class TestOAuthToken:
    """Test OAuthToken model."""
    
    @pytest.mark.asyncio
    async def test_create_oauth_token(self, test_session, test_user):
        """Test creating an OAuth token."""
        token = OAuthToken(
            user_id=test_user.id,
            provider="google",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope="https://www.googleapis.com/auth/calendar",
        )
        
        test_session.add(token)
        await test_session.commit()
        await test_session.refresh(token)
        
        assert token.id is not None
        assert token.user_id == test_user.id
        assert token.provider == "google"
        assert token.access_token == "test_access_token"
        assert token.refresh_token == "test_refresh_token"
        assert token.scope == "https://www.googleapis.com/auth/calendar"
        assert token.created_at is not None
        assert token.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_oauth_token_str_representation(self, test_oauth_token):
        """Test OAuth token string representation."""
        assert str(test_oauth_token) == "google OAuth token for testuser"
    
    @pytest.mark.asyncio
    async def test_oauth_token_provider_validation(self, test_session, test_user):
        """Test OAuth token provider validation."""
        # Valid providers
        valid_providers = ["google", "microsoft", "outlook", "apple"]
        
        for provider in valid_providers:
            token = OAuthToken(
                user_id=test_user.id,
                provider=provider,
                access_token="test_access_token",
                refresh_token="test_refresh_token",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                scope="test_scope",
            )
            
            test_session.add(token)
            await test_session.commit()
            await test_session.refresh(token)
            assert token.provider == provider
            await test_session.delete(token)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_oauth_token_is_valid(self, test_session, test_user):
        """Test OAuth token validation."""
        # Valid token (not expired)
        valid_token = OAuthToken(
            user_id=test_user.id,
            provider="google",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope="test_scope",
        )
        
        test_session.add(valid_token)
        await test_session.commit()
        await test_session.refresh(valid_token)
        
        assert valid_token.is_valid() is True
        
        # Expired token
        expired_token = OAuthToken(
            user_id=test_user.id,
            provider="google",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() - timedelta(hours=1),
            scope="test_scope",
        )
        
        test_session.add(expired_token)
        await test_session.commit()
        await test_session.refresh(expired_token)
        
        assert expired_token.is_valid() is False
    
    @pytest.mark.asyncio
    async def test_oauth_token_is_expired(self, test_session, test_user):
        """Test OAuth token expiration check."""
        # Valid token (not expired)
        valid_token = OAuthToken(
            user_id=test_user.id,
            provider="google",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope="test_scope",
        )
        
        test_session.add(valid_token)
        await test_session.commit()
        await test_session.refresh(valid_token)
        
        assert valid_token.is_expired() is False
        
        # Expired token
        expired_token = OAuthToken(
            user_id=test_user.id,
            provider="google",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() - timedelta(hours=1),
            scope="test_scope",
        )
        
        test_session.add(expired_token)
        await test_session.commit()
        await test_session.refresh(expired_token)
        
        assert expired_token.is_expired() is True
    
    @pytest.mark.asyncio
    async def test_oauth_token_is_expiring_soon(self, test_session, test_user):
        """Test OAuth token expiring soon check."""
        # Token expiring in 5 minutes (should be considered expiring soon)
        expiring_soon_token = OAuthToken(
            user_id=test_user.id,
            provider="google",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            scope="test_scope",
        )
        
        test_session.add(expiring_soon_token)
        await test_session.commit()
        await test_session.refresh(expiring_soon_token)
        
        assert expiring_soon_token.is_expiring_soon() is True
        
        # Token expiring in 1 hour (should not be considered expiring soon)
        not_expiring_soon_token = OAuthToken(
            user_id=test_user.id,
            provider="google",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope="test_scope",
        )
        
        test_session.add(not_expiring_soon_token)
        await test_session.commit()
        await test_session.refresh(not_expiring_soon_token)
        
        assert not_expiring_soon_token.is_expiring_soon() is False
    
    @pytest.mark.asyncio
    async def test_oauth_token_relationships(self, test_session, test_oauth_token):
        """Test OAuth token relationships."""
        await test_session.refresh(test_oauth_token, ["user"])
        
        assert test_oauth_token.user is not None
        assert test_oauth_token.user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_oauth_token_soft_delete(self, test_session, test_oauth_token):
        """Test OAuth token soft delete."""
        token_id = test_oauth_token.id
        
        # Soft delete the token
        test_oauth_token.deleted_at = datetime.utcnow()
        await test_session.commit()
        
        # Verify token is soft deleted
        assert test_oauth_token.deleted_at is not None
        assert test_oauth_token.is_deleted is True
    
    @pytest.mark.asyncio
    async def test_oauth_token_refresh(self, test_session, test_oauth_token):
        """Test OAuth token refresh."""
        original_expires_at = test_oauth_token.expires_at
        new_expires_at = datetime.utcnow() + timedelta(hours=2)
        
        # Refresh the token
        test_oauth_token.refresh_token = "new_refresh_token"
        test_oauth_token.access_token = "new_access_token"
        test_oauth_token.expires_at = new_expires_at
        
        await test_session.commit()
        await test_session.refresh(test_oauth_token)
        
        assert test_oauth_token.refresh_token == "new_refresh_token"
        assert test_oauth_token.access_token == "new_access_token"
        assert test_oauth_token.expires_at == new_expires_at
        assert test_oauth_token.updated_at > test_oauth_token.created_at
    
    @pytest.mark.asyncio
    async def test_oauth_token_scope_validation(self, test_session, test_user):
        """Test OAuth token scope validation."""
        # Valid scopes
        valid_scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
            "openid profile email",
        ]
        
        for scope in valid_scopes:
            token = OAuthToken(
                user_id=test_user.id,
                provider="google",
                access_token="test_access_token",
                refresh_token="test_refresh_token",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                scope=scope,
            )
            
            test_session.add(token)
            await test_session.commit()
            await test_session.refresh(token)
            assert token.scope == scope
            await test_session.delete(token)
            await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_user_oauth_tokens_relationship(self, test_session, test_user):
        """Test user-OAuth tokens relationship."""
        # Create additional OAuth tokens
        token1 = OAuthToken(
            user_id=test_user.id,
            provider="microsoft",
            access_token="test_access_token_1",
            refresh_token="test_refresh_token_1",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope="test_scope_1",
        )
        token2 = OAuthToken(
            user_id=test_user.id,
            provider="outlook",
            access_token="test_access_token_2",
            refresh_token="test_refresh_token_2",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope="test_scope_2",
        )
        
        test_session.add_all([token1, token2])
        await test_session.commit()
        
        # Refresh user with OAuth tokens
        await test_session.refresh(test_user, ["oauth_tokens"])
        
        assert len(test_user.oauth_tokens) == 3  # Including the one from fixture
        providers = [token.provider for token in test_user.oauth_tokens]
        assert "google" in providers
        assert "microsoft" in providers
        assert "outlook" in providers
