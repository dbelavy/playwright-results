# Contributing to Playwright Pathology

First off, thank you for considering contributing to Playwright Pathology! It's people like you that make this tool better for everyone.

## Be Nice

We expect contributors to be respectful and constructive in their interactions with others. 

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* Use a clear and descriptive title
* Describe the exact steps which reproduce the problem
* Provide specific examples to demonstrate the steps
* Describe the behavior you observed after following the steps
* Explain which behavior you expected to see instead and why
* Include screenshots if possible
* Include your environment details (OS, Python version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* A clear and descriptive title
* A detailed description of the proposed feature
* Explain why this enhancement would be useful
* List any alternative solutions you've considered

### Pull Requests

* Fill in the required template
* Follow the Python coding style (PEP 8)
* Include appropriate tests
* Update documentation as needed
* End all files with a newline

## Development Process

1. Fork the repo
2. Create a new branch from `main`
3. Make your changes
4. Run the test suite
5. Submit a Pull Request

### Setting Up Development Environment

```bash
# Clone your fork
git clone https://github.com/your-username/playwrightpathology.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### Running Tests

The project uses pytest for testing. Tests are organized by provider and feature.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run tests for a specific provider
pytest tests/providers/test_medway.py

# Run tests matching a pattern
pytest -k "test_login"

# Run tests and show coverage
pytest --cov=providers

# Run tests in parallel (faster)
pytest -n auto
```

### Test Structure

Tests are organized into provider-specific test files in `tests/providers/`. Each provider should have tests covering:

1. Login Flow
```python
@pytest.mark.asyncio
async def test_login(self, initialized_session, test_credentials):
    """Test the login process including any 2FA or PIN requirements."""
```

2. Patient Search
```python
@pytest.mark.asyncio
async def test_search_patient(self, initialized_session, test_patient):
    """Test patient search with all required fields."""
```

3. Error Handling
```python
@pytest.mark.asyncio
async def test_uninitialized_error(self, provider_session):
    """Test error handling for uninitialized session."""
```

4. Required Fields
```python
@pytest.mark.asyncio
async def test_required_fields(self, provider_session):
    """Test that required fields are correctly defined."""
```

5. Provider-Specific Features (if any)
```python
@pytest.mark.asyncio
async def test_specific_feature(self, initialized_session):
    """Test provider-specific functionality."""
```

### Writing Provider Tests

When writing tests for a new provider:

1. Create a new test file in `tests/providers/test_yourprovider.py`
2. Inherit from `PlaywrightTestCase` for common test utilities
3. Use fixtures for session setup:
   - `provider_session`: Basic session with credentials and patient
   - `initialized_session`: Session with mocked browser setup
4. Mock page interactions:
   ```python
   # Mock elements
   element = self.get_mock_element(click=None, fill=None)
   
   # Mock selectors
   page.get_by_role = MagicMock(side_effect=lambda role, **kwargs: {...})
   page.get_by_label = MagicMock(side_effect=lambda label: {...})
   
   # Mock locators
   page.locator = MagicMock(side_effect=lambda selector: {...})
   ```
5. Test error scenarios:
   ```python
   with pytest.raises(RuntimeError, match="Expected error"):
       await session.some_method()
   ```
6. Verify interactions:
   ```python
   element.click.assert_called_once()
   element.fill.assert_called_with(expected_value)
   ```

### Test Coverage Requirements

New providers must have tests for:

1. All public methods (login, search_patient, etc.)
2. Error handling scenarios
3. Field validation
4. Provider-specific features
5. Edge cases (e.g., patient not found)

Aim for at least 90% test coverage for new code.

### Code Style and Linting

We use several tools to ensure consistent code style. First, install the linting tools:

```bash
# Install development dependencies including linting tools
pip install -r requirements-dev.txt

# Or install individually
pip install black isort flake8
```

The tools are:

* [Black](https://github.com/psf/black): An opinionated code formatter that automatically reformats Python code to conform to PEP 8
* [isort](https://pycqa.github.io/isort/): A utility that automatically sorts and organizes Python imports
* [flake8](https://flake8.pycqa.org/): A tool that checks Python code against coding style (PEP 8) and programming errors

#### Running Style Checks

The `.` in commands below means "current directory" - it tells the tool to process all Python files in the current directory and its subdirectories.


```bash
# Format code with Black
black .

# Check if any files would be reformatted
black . --check

# Sort imports
isort .

# Check import sorting
isort . --check-only

# Run flake8 linting
flake8

# Run all checks
black . --check && isort . --check-only && flake8
```

#### Understanding Linting Output

1. Black output:
   ```bash
   # No issues:
   All done! ✨ 🍰 ✨
   
   # Files would be reformatted:
   would reformat providers/medway.py
   Oh no! 💥 💔 💥
   ```

2. isort output:
   ```bash
   # No issues:
   OK: Checked X files
   
   # Import sorting needed:
   ERROR: providers/medway.py Imports are incorrectly sorted.
   ```

3. flake8 output:
   ```bash
   # Format:
   file.py:line:column: error_code error_message
   
   # Example:
   providers/medway.py:10:1: E302 expected 2 blank lines
   ```

#### Common Linting Issues

1. Black:
   - Line length exceeds 88 characters
   - Inconsistent string quotes
   - Incorrect whitespace around operators

2. isort:
   - Standard library imports mixed with third-party
   - Missing newlines between import groups
   - Incorrect import order within groups

3. flake8:
   - E302: Missing blank lines between functions
   - F401: Unused imports
   - E501: Line too long
   - F841: Unused variables

#### Configuration

Linting rules are configured in:

- `pyproject.toml` for Black:
  ```toml
  [tool.black]
  line-length = 88
  target-version = ['py38']
  ```

- `.isort.cfg` for isort:
  ```ini
  [settings]
  profile = black
  multi_line_output = 3
  ```

- `setup.cfg` for flake8:
  ```ini
  [flake8]
  max-line-length = 88
  extend-ignore = E203
  ```

These configurations ensure all tools work together harmoniously.

## Provider Development

When adding a new provider:

1. Create a new file in the `providers` directory
2. Implement the Session class with required properties:
```python
class NewProviderSession(Session):
    name = "Provider Name"
    required_fields = [...]
    provider_group = "Group"
    credentials_key = "Key"
```
3. Add appropriate tests
4. Update documentation

## Documentation

* Use docstrings for all public modules, functions, classes, and methods
* Follow Google style for docstrings
* Keep the README.md up to date

## Questions?

Feel free to create an issue with the "question" label if you need help.
