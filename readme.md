# Playwright Pathology

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
- A virtual environment tool (I used venv)

## Installation

## Prerequisites

- Python 3.12.4
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone git@bitbucket.org:dbelavy/playwrightpathology.git
cd PlaywrightPathology
```

2. Create and activate a virtual environment:
```bash
# Using venv
python3.12 -m venv venv
source venv/bin/activate  # On Unix/macOS
# OR
venv\Scripts\activate     # On Windows
```
If using conda and need to deactivate
```
conda deactivate
```

3. Install required packages:
```bash
pip install aioconsole pynput playwright pyotp
```

Not sure if this is necessary but I had browser problems so download playwright browsers into the venv and use them there.
```bash
export PLAYWRIGHT_BROWSERS_PATH=0
playwright install```

4. Install Playwright browsers:

```bash
playwright install
```

Sometimes you need to be more explicit
```
python -m playwright install
python -m playwright install-deps
```

## Configuration

1. Create a credentials file by copying the template:
```bash
cp rename_to_credentials.json credentials.json
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
python main.py
```

2. Select tasks to run when prompted:
```
1: run_medway_process
2: run_SNP_process
3: run_QScript_process
4: run_QGov_Viewer_process
5: run_myHealthRecord_process
6: run_mater_path_process
7: run_fourcyte_process
```
Enter task numbers separated by commas (e.g., "1,3,6")

3. Enter patient details when prompted:
- Family Name
- Given Name
- Date of Birth (DDMMYYYY format)
- Medicare Number (if required)
- Sex (M, F, or I) (if required)

4. Input Commands during execution:
- Enter 2FA codes when prompted:
  - Format: `Q######` for QScript (manual entry required)
  - Format: `P######` for PRODA
  - Format: `F######` for 4Cyte (now automated with pyotp - no manual entry needed)

5. Type 'x' to quit the application

### Command Line Arguments

You can also run the application with command-line arguments to skip manual input:

```bash
python main.py --family_name "Smith" --given_name "John" --dob "01011990" --medicare_number "12345" --sex "M"
```

Available arguments:
- `--family_name`: Patient's family name
- `--given_name`: Patient's given name
- `--dob`: Date of birth in DDMMYYYY format
- `--medicare_number`: Medicare number
- `--sex`: Sex (M, F, or I)

The application will display a command with these arguments at the end of execution for easy re-running with the same patient details.

## Provider Information

### Mater Pathology
- Automated login and patient search
- Requires username and password
- Required fields: family name, given name, DOB

### 4cyte
- Automated 2FA authentication using pyotp
- Requires username, password, and TOTP secret key
- TOTP secret key is obtained when first setting up 2FA with 4cyte
- Required fields: family name, given name, DOB
- Note: Manual 2FA code entry is no longer needed as it's handled automatically by pyotp

### QScript
- Multi-step authentication process:
  1. Username/password login
  2. Manual 2FA code entry (enter code starting with 'Q')
  3. PIN entry (Note: PIN system is not implemented)
- Each session is treated as a new login (no cookie persistence)
- Required fields: family name, given name, DOB
- Known limitation: PIN system is under development

### Medway
- Basic authentication
- Requires username and password
- Required fields: family name, given name, DOB

### MyHealth Record (PRODA)
- Multi-step PRODA authentication:
  1. Username/password login
  2. Manual 2FA code entry (enter code starting with 'P')
  3. Provider selection using PRODA_full_name
- Requires username, password, and PRODA_full_name in credentials.json
- PRODA_full_name must match exactly as it appears when you log in to PRODA
- Required fields: family name, DOB, medicare number, sex
- Supports gender options: Male, Female, Intersex, Not Stated
- Medicare number must include IRN (Individual Reference Number)



### SNP Sonic
- Basic authentication
- Requires username and password
- Required fields: family name, given name, DOB

### The Viewer (QGov)
- QGov login integration
- Requires username and password
- Required fields: family name, DOB, medicare number, sex

## Troubleshooting virtual environment

- I use venv which, on my machine, is shown with a (venv) at the start of the command line. 

If I encounter the "(base)" conda environment and can't activate venv:
```bash
conda deactivate
```

Then activate your Python virtual environment:
```bash
source venv/bin/activate
```

## Security Notes

- Credentials are stored locally and read from a local JSON file IN PLAIN TEXT. This needs to be updated!!!
- No credential information is transmitted to external servers except for legitimate login purposes
- Always ensure your `credentials.json` is properly secured and not shared
- For 4cyte, the TOTP secret key is sensitive information and should be secured like any other credential

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
