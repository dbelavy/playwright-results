import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from playwright.async_api import Page, Browser, BrowserContext

@pytest.fixture
def mock_page():
    """Create a mock page with async capabilities."""
    page = MagicMock(spec=Page)
    
    # Mock common async methods
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    
    # Mock element selection methods with default async mocks
    def mock_element(**kwargs):
        element = MagicMock()
        for key, value in kwargs.items():
            setattr(element, key, AsyncMock(return_value=value))
        return element
    
    page.get_by_label = MagicMock(side_effect=lambda label: mock_element(
        click=None,
        fill=None,
        press=None
    ))
    page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: mock_element(
        click=None,
        fill=None
    ))
    page.get_by_placeholder = MagicMock(side_effect=lambda text: mock_element(
        click=None,
        fill=None
    ))
    
    return page

@pytest.fixture
def mock_context(mock_page):
    """Create a mock browser context."""
    context = MagicMock(spec=BrowserContext)
    context.new_page = AsyncMock(return_value=mock_page)
    return context

@pytest.fixture
def mock_browser(mock_context):
    """Create a mock browser."""
    browser = MagicMock(spec=Browser)
    browser.new_context = AsyncMock(return_value=mock_context)
    return browser

@pytest.fixture
def mock_playwright(mock_browser):
    """Create a mock playwright instance."""
    playwright = MagicMock()
    playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    return playwright

@pytest.fixture
def test_credentials():
    """Test credentials fixture."""
    return {
        "MaterPath": {
            "user_name": "test_user",
            "user_password": "test_pass",
            "totp_secret": "test_secret"
        },
        "Sonic": {
            "user_name": "test_user",
            "user_password": "test_pass"
        },
        "QScript": {
            "user_name": "test_user",
            "user_password": "test_pass",
            "PIN": "1234"
        },
        "Medway": {
            "user_name": "test_user",
            "user_password": "test_pass"
        },
        "IMed": {
            "user_name": "test_user",
            "user_password": "test_pass",
            "postcode": "4000",
            "suburb": "- BRISBANE CITY"
        },
        "PRODA": {
            "user_name": "test_user",
            "user_password": "test_pass",
            "PRODA_full_name": "Test User"
        },
        "Meditrust": {
            "user_name": "test_user",
            "user_password": "test_pass",
            "totp_secret": "test_secret"
        },
        "QXR": {
            "user_name": "test_user",
            "user_password": "test_pass"
        },
        "QScan": {
            "user_name": "test_user",
            "user_password": "test_pass"
        },
        "QGov": {
            "user_name": "test_user",
            "user_password": "test_pass"
        },
        "4cyte": {
            "user_name": "test_user",
            "user_password": "test_pass",
            "totp_secret": "test_secret"
        },
        "MaterLegacy": {
            "user_name": "test_user",
            "user_password": "test_pass"
        }
    }

@pytest.fixture
def test_patient():
    """Test patient data fixture."""
    return {
        "family_name": "SMITH",
        "given_name": "JOHN",
        "dob": "01011990",
        "medicare_number": "12345678901",  # 11 digits
        "sex": "M"
    }

# Custom markers
@pytest.fixture
async def initialized_session(provider_session, mock_playwright, mock_page):
    """Initialize a provider session with mocked browser objects."""
    # The mock_page fixture creates our page with mocks
    # We need to ensure this is the page returned by the initialization chain
    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    
    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    
    # Initialize with our mocked chain
    await provider_session.initialize(mock_playwright)
    
    # Return both session and page for tests to use
    return provider_session, mock_page

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test that requires credentials"
    )
    config.addinivalue_line(
        "markers",
        "playwright: mark test as requiring playwright browser"
    )
