from unittest.mock import MagicMock, AsyncMock

class PlaywrightTestCase:
    """Base class for testing Playwright-based providers."""
    
    def get_mock_element(self, **kwargs):
        """Helper to create a mock element with async methods."""
        element = MagicMock()
        for key, value in kwargs.items():
            setattr(element, key, AsyncMock(return_value=value))
        return element
        
    def setup_page_elements(self, page, label_elements=None, role_elements=None):
        """
        Set up page elements with specific mocks.
        
        Args:
            page: The mock page to set up
            label_elements: Dict mapping labels to mock elements
            role_elements: Dict mapping (role, name) tuples to mock elements
        """
        if label_elements:
            page.get_by_label.side_effect = lambda label: label_elements.get(
                label,
                self.get_mock_element(click=None, fill=None, press=None)
            )
            
        if role_elements:
            page.get_by_role.side_effect = lambda role, **kwargs: role_elements.get(
                (role, kwargs.get('name')),
                self.get_mock_element(click=None, fill=None)
            )
