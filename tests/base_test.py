import pytest
from unittest.mock import Mock

class BaseProviderTest:
    """Base class for provider test cases."""
    
    @pytest.fixture
    def provider_session(self, mock_page, mock_browser, test_credentials):
        """
        Create a provider session for testing.
        Must be implemented by child classes.
        """
        raise NotImplementedError("Provider tests must implement provider_session fixture")

    @pytest.mark.asyncio
    async def test_required_fields(self, provider_session):
        """Test that required fields are properly defined."""
        assert hasattr(provider_session, 'required_fields')
        assert isinstance(provider_session.required_fields, list)
        assert len(provider_session.required_fields) > 0

    @pytest.mark.asyncio
    async def test_provider_group(self, provider_session):
        """Test provider group is set."""
        assert hasattr(provider_session, 'provider_group')
        assert provider_session.provider_group in ['Pathology', 'Radiology', 'General']

    @pytest.mark.asyncio
    async def test_credentials_key(self, provider_session):
        """Test credentials key is set."""
        assert hasattr(provider_session, 'credentials_key')
        assert isinstance(provider_session.credentials_key, str)

    @pytest.mark.asyncio
    async def test_login(self, provider_session, mock_page):
        """
        Test login flow.
        Must be implemented by child classes.
        """
        raise NotImplementedError("Provider tests must implement test_login")

    @pytest.mark.asyncio
    async def test_search_patient(self, provider_session, mock_page, test_patient):
        """
        Test patient search.
        Must be implemented by child classes.
        """
        raise NotImplementedError("Provider tests must implement test_search_patient")

    @pytest.mark.asyncio
    async def test_uninitialized_error(self, provider_session):
        """Test error handling for uninitialized session."""
        provider_session.page = None
        
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await provider_session.login()
            
        with pytest.raises(RuntimeError, match="Session not initialized"):
            await provider_session.search_patient({})
