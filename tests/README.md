# Testing Guide for Playwright Pathology

## Overview

The test suite is organized into several categories:
- Unit tests for provider implementations
- Integration tests for provider authentication
- Meta tests to ensure test coverage

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures and configuration
├── test_providers.py    # Provider-specific test cases
└── README.md           # This documentation
```

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest -m "unit"
```

### Integration Tests
```bash
pytest -m "integration"
```

### Single Provider
```bash
pytest tests/test_providers.py -k "TestMaterPathology"
```

## Writing Tests for New Providers

1. Create a test class inheriting from `BaseProviderTest`:
```python
class TestNewProvider(BaseProviderTest):
    @pytest.fixture
    async def provider_session(self, mock_page, mock_browser, test_credentials):
        session = NewProviderSession(mock_page, mock_browser)
        session.credentials = test_credentials["ProviderKey"]
        return session

    @pytest.mark.asyncio
    async def test_login(self, provider_session, mock_page):
        await provider_session.login()
        # Verify login steps
```

2. Implement required test methods:
- test_login: Verify authentication flow
- test_search_patient: Verify patient search
- test_error_handling: Verify error cases

3. Add provider credentials to conftest.py test_credentials fixture

## Mocking Guidelines

1. Page Actions
```python
# Mock a successful element find
mock_page.wait_for_selector.return_value = Mock()

# Mock a failed element find
mock_page.wait_for_selector.side_effect = TimeoutError()

# Mock form interactions
mock_page.fill.assert_called_with('#username', 'test_user')
mock_page.click.assert_called_with('button[type="submit"]')
```

2. Navigation
```python
# Mock page navigation
mock_page.goto.assert_called_with('https://example.com/login')

# Mock navigation error
mock_page.goto.side_effect = Exception("Failed to reach site")
```

3. TOTP/2FA
```python
# Mock TOTP generation
with patch('utils.get_totp_code') as mock_totp:
    mock_totp.return_value = '123456'
    await provider_session.login()
```

## Best Practices

1. Use Fixtures
- Use shared fixtures from conftest.py
- Create provider-specific fixtures in test classes

2. Error Testing
- Test network failures
- Test authentication failures
- Test invalid patient data
- Test timeout scenarios

3. Assertions
- Verify all required page interactions
- Check error handling
- Validate state changes

4. Documentation
- Document test scenarios
- Explain complex mocking
- Note provider-specific requirements

## Integration Testing

For running tests against real providers:

1. Create a .env file for test credentials:
```bash
MATERPATH_USERNAME=real_username
MATERPATH_PASSWORD=real_password
MATERPATH_TOTP_SECRET=real_secret
# Add other provider credentials
```

2. Run integration tests:
```bash
pytest -m "integration"
```

Note: Integration tests are disabled by default to prevent accidental API calls. Use with caution and only with test accounts.

## Common Testing Scenarios

### 1. Testing Login Flows
```python
@pytest.mark.asyncio
async def test_login_with_2fa(self, provider_session, mock_page):
    """Test login with 2FA."""
    # Mock TOTP
    with patch('utils.get_totp_code') as mock_totp:
        mock_totp.return_value = '123456'
        await provider_session.login()
        
    # Verify steps
    mock_page.goto.assert_called()
    mock_page.fill.assert_called()
    mock_page.click.assert_called()
```

### 2. Testing Patient Search
```python
@pytest.mark.asyncio
async def test_search_with_medicare(self, provider_session, mock_page):
    """Test search with Medicare number."""
    patient = {
        "family_name": "SMITH",
        "given_name": "JOHN",
        "dob": "01011990",
        "medicare_number": "1234567890"
    }
    await provider_session.search_patient(patient)
    
    # Verify form filled
    assert mock_page.fill.call_count >= 4
```

### 3. Testing Error Handling
```python
@pytest.mark.asyncio
async def test_invalid_credentials(self, provider_session, mock_page):
    """Test invalid credentials error."""
    mock_page.wait_for_selector.side_effect = TimeoutError()
    
    with pytest.raises(Exception) as exc:
        await provider_session.login()
    assert "Login failed" in str(exc.value)
```

## Debugging Tests

1. Enable verbose output:
```bash
pytest -vv
```

2. Show print statements:
```bash
pytest -s
```

3. Debug specific test:
```bash
pytest tests/test_providers.py::TestMaterPathology::test_login -vv
```

## Adding New Test Cases

When adding a new provider or test case:

1. Update conftest.py:
- Add new credentials to test_credentials fixture
- Add any new shared fixtures needed

2. Update test_providers.py:
- Create new test class inheriting from BaseProviderTest
- Implement required test methods
- Add any provider-specific test cases

3. Document provider-specific requirements:
- Note any special authentication flows
- Document required credentials
- List any known limitations

## Continuous Integration

The test suite is configured to run in CI environments:

1. Unit tests run on every push
2. Integration tests run on protected branches
3. Test credentials are stored as CI environment variables

## Maintenance

1. Keep mock objects up to date with Playwright API changes
2. Update test credentials when provider requirements change
3. Review and update documentation as needed
4. Clean up any unused fixtures or helpers
