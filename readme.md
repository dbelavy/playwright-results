# Playwright Results

A Python-based automation tool for accessing various medical pathology and health record systems using Playwright.

## Overview

This application automates the process of accessing multiple medical systems including:
- Mater Pathology
- 4cyte
- QScript
- Medway
- MyHealth Record
- SNP Sonic
- The Viewer

## Prerequisites

- Python 3.12.4
- pip (Python package installer)
- A virtual environment tool (venv recommended)

## Installation

### macOS / Linux Installation

The install.sh and start.sh scripts handle all setup automatically on macOS and Linux:

1. Clone the repository:
```bash
git clone git@bitbucket.org:dbelavy/playwright-results.git
cd playwright-results
```

2. If using conda, deactivate it first:
```bash
conda deactivate
```

3. Run the install script:
```bash
chmod +x install.sh
./install.sh
```

4. Start the application:
```bash
chmod +x start.sh
./start.sh
```

### Windows Installation

Windows users need to perform the installation steps manually:

1. Clone the repository:
```cmd
git clone git@bitbucket.org:dbelavy/playwright-results.git
cd playwright-results
```

2. Create and activate a virtual environment:
```cmd
python -m venv venv
venv\Scripts\activate
```

If using conda, deactivate it first:
```cmd
conda deactivate
```

3. Install required packages:
```cmd
pip install aioconsole pynput playwright pyotp
```

4. Install Playwright browsers:
```cmd
playwright install
python -m playwright install-deps
```

5. Start the application:
```cmd
python main.py
```

## Configuration

1. Create a credentials file by copying the template:
```bash
cp rename_to_credentials.json credentials.json  # On macOS/Linux
copy rename_to_credentials.json credentials.json  # On Windows
```

2. Edit `credentials.json` with your credentials for each provider:
```json
{
    "4cyte": {
        "user_name": "your_username",
        "user_password": "your_password",
        "totp_secret": "your_2fa_secret_key"
    },
    "QScript": {
        "user_name": "your_username",
        "user_password": "your_password",
        "PIN": "your_pin"  (NOTE: PIN system is not fully implemented - every login is treated as new)
    },
    // Add credentials for other providers...
}
```

Note: Make sure your `credentials.json` is listed in `.gitignore` to prevent accidentally committing sensitive information.

## Usage

### Basic Usage

1. Run the main application:
```bash
./start.sh  # On macOS/Linux
python main.py  # On Windows
```

2. Select providers from the categorized list when prompted. Providers are grouped by type (e.g., Pathology, Radiology, General).

3. Enter patient details when prompted:
- Family Name
- Given Name
- Date of Birth (DDMMYYYY format)
- Medicare Number (if required)
- Sex (M, F, or I) (if required)

4. Handling 2FA codes:
- For providers requiring 2FA (like QScript, PRODA):
  1. When you receive the 2FA code (SMS/email)
  2. Copy the code to your clipboard
  3. The application will automatically detect and use the code
  4. No need to manually type the code
- Note: 4Cyte uses automated TOTP authentication, no manual code needed

5. Type 'x' to quit at any menu, or press Ctrl+C to force quit


## Provider Information

Call for help: these providers are the ones that I use. Contact me if you wish to collaborate in adding providers.

### IMed
Authentication:
- Location selection by postcode and suburb
- Username/password login in popup window
- No 2FA required
Required fields: family name, given name, DOB

### Mater Legacy
Authentication:
- Simple username/password login
- No 2FA required
- Direct access to patient search
Required fields: family name, given name, DOB

### Mater Path
Authentication:
- Multi-step login process:
  1. External practitioner selection
  2. Username entry, then password on separate page
  3. Automated TOTP 2FA (using secret key configured in credentials)
- Handles alternative authentication paths if needed
Required fields: family name, given name, DOB

### Meditrust
Authentication:
- Username/password login
- Automated TOTP 2FA (using secret key configured in credentials)
- No patient search functionality
Required fields: none (system access only)

### Mater Pathology
- Automated login and patient search
- Requires username and password
- Required fields: family name, given name, DOB

### 4cyte
Authentication:
- Username/password login in popup window
- Automated TOTP 2FA (using secret key configured in credentials)
- Break glass access required for patient records
Required fields: family name, given name, DOB

### QScript
- Multi-step authentication process:
  1. Username/password login
  2. Manual 2FA code entry (enter code starting with 'Q')
  3. PIN entry (Note: PIN system is not implemented)
- Each session is treated as a new login (no cookie persistence)
- Required fields: family name, given name, DOB
- Known limitation: PIN system is under development

### Medway
Authentication:
- Simple username/password login
- No 2FA required
- Optional Medicare number support
Required fields: family name, given name, DOB

### MyHealth Record (PRODA)
Authentication:
- Multi-step PRODA authentication:
  1. Username/password login
  2. SMS-based 2FA (automatically detected from clipboard)
  3. Provider selection using PRODA_full_name from credentials
- Requires exact PRODA_full_name match from login screen
- Includes pause between pages to prevent timing issues
Patient Search:
- Medicare number must include IRN (Individual Reference Number)
- Supports all gender options: Male, Female, Intersex, Not Stated
Required fields: family name, DOB, medicare number, sex

### QScan
Authentication:
- Username/password login
- Handles automatic redirection if password change required
- Break glass access with privacy acknowledgment
- Detailed patient matching system with confirmation
Required fields: family name, given name, DOB

### QXR
Authentication:
- Username/password login
- Unique search interface with DOB popup handling
- Error recovery with screenshots for troubleshooting
- Robust timing controls for reliable operation
Required fields: family name, given name, DOB

### SNP Sonic
Authentication:
- Username/password login
- Business selection (automatically set to "SNP")
- Dedicated search page navigation
Required fields: family name, given name, DOB

### The Viewer (QGov)
Authentication:
- QGov email/password login with explicit wait states
- Multi-page navigation with policy redirect
- Popup window handling with timeout protection
Patient Search:
- Automatic gender code conversion (M→1, F→2, I→3)
- Medicare number validation
Required fields: family name, DOB, medicare number, sex

## Troubleshooting virtual environment

### macOS / Linux
If you see "(base)" conda environment and can't activate venv:
```bash
conda deactivate
source venv/bin/activate
```

### Windows
If you see "(base)" conda environment and can't activate venv:
```cmd
conda deactivate
venv\Scripts\activate
```

## Security Notes

### Credentials Storage
- Credentials are stored in a local JSON file for easy user editing
- Recommended security measures:
  1. Set file permissions to 600 (owner read/write only) on macOS/Linux:
     ```bash
     chmod 600 credentials.json
     ```
  2. Never commit credentials.json to version control (keep in .gitignore)
  4. Keep rename_to_credentials.json in the repo as a template

### General Security
- No credential information is transmitted to external servers except for legitimate login purposes
- Always ensure your credentials.json is properly secured and not shared
- For services with TOTP secret keys, this is sensitive information and should be secured like passwords

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
