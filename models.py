from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List
import json
import asyncio
from playwright.async_api import Page, Browser, BrowserContext, Playwright


@dataclass
class Credentials:
    """Unified credentials class that handles all provider types"""
    user_name: str
    user_password: str
    totp_secret: Optional[str] = None  # For 2FA providers
    PIN: Optional[str] = None  # For QScript
    postcode: Optional[str] = None  # For IMed
    suburb: Optional[str] = None  # For IMed
    PRODA_full_name: Optional[str] = None  # For PRODA

    @classmethod
    def load(cls, file_path: str, provider: str) -> 'Credentials':
        """Load credentials for a specific provider"""
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            
            if provider not in data:
                raise ValueError(f"Credentials for {provider} not found")
            
            return cls(**data[provider])
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Credentials file {file_path} not found")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in credentials file {file_path}")
        except TypeError as e:
            raise ValueError(f"Invalid credential format: {e}")

@dataclass
class SharedState:
    QScript_code: Optional[str] = None
    PRODA_code: Optional[str] = None
    FourCyte_code: Optional[str] = None  # Changed from 4Cyte_code to be a valid Python identifier
    paused: bool = True
    exit: bool = False
    credentials_file: str = "credentials.json"

@dataclass
class PatientDetails:
    family_name: str
    given_name: Optional[str] = None
    dob: Optional[str] = None
    medicare_number: Optional[str] = None
    sex: Optional[str] = None

    def __post_init__(self):
        # Validate DOB format if provided
        if self.dob:
            try:
                datetime.strptime(self.dob, "%d%m%Y")
            except ValueError:
                raise ValueError("DOB must be in DDMMYYYY format")
        
        # Validate sex if provided
        if self.sex and self.sex not in ["M", "F", "I"]:
            raise ValueError("Sex must be 'M', 'F', or 'I'")

    @classmethod
    def from_args(cls, args, required_fields: list[str]):
        """Create PatientDetails from argparse args and required fields"""
        details = {}
        
        # Handle each field based on args or user input
        details['family_name'] = args.family_name if args.family_name else (
            input("Enter Family Name: ") if 'family_name' in required_fields else None)
        
        details['given_name'] = args.given_name if args.given_name else (
            input("Enter Given Name: ") if 'given_name' in required_fields else None)
        
        if 'dob' in required_fields:
            if args.dob:
                details['dob'] = args.dob
            else:
                while True:
                    dob_input = input("Enter DOB (DDMMYYYY): ")
                    try:
                        datetime.strptime(dob_input, "%d%m%Y")
                        details['dob'] = dob_input
                        break
                    except ValueError:
                        print("Invalid date. Please enter a valid date in DDMMYYYY format.")
        
        details['medicare_number'] = str(args.medicare_number) if args.medicare_number else (
            str(input("Enter Medicare Number: ")) if 'medicare_number' in required_fields else None)
        
        if 'sex' in required_fields:
            details['sex'] = args.sex.upper() if args.sex else None
            while not details['sex'] or details['sex'] not in ["M", "F", "I"]:
                details['sex'] = input("Enter Sex (M, F, or I): ").upper()
        
        return cls(**details)

    def to_cli_args(self) -> str:
        """Convert patient details to CLI arguments string"""
        flags = []
        if self.family_name:
            flags.append(f"--family_name {self.family_name}")
        if self.given_name:
            flags.append(f"--given_name {self.given_name}")
        if self.dob:
            flags.append(f"--dob {self.dob}")
        if self.medicare_number:
            flags.append(f"--medicare_number {self.medicare_number}")
        if self.sex:
            flags.append(f"--sex {self.sex}")
        return " ".join(flags)


class Provider:
    """Unified provider class that handles all provider types through configuration"""
    
    def __init__(self, name: str, credentials: Credentials, patient: PatientDetails, shared_state: SharedState, debug: bool = False):
        self.name = name
        self.credentials = credentials
        self.patient = patient
        self.shared_state = shared_state
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.debug = debug
        self.step_delay = 2 if debug else 0  # Add delay between steps in debug mode
        
        # Provider-specific configuration
        self.config = PROVIDER_CONFIGS.get(name, {})
        if not self.config:
            raise ValueError(f"No configuration found for provider {name}")
            
        if self.debug and 'debug_notes' in self.config:
            print(f"\nDebug Notes for {name}:")
            for category, notes in self.config['debug_notes'].items():
                print(f"\n{category.upper()}:")
                if isinstance(notes, list):
                    for note in notes:
                        print(f"- {note}")
                else:
                    print(f"- {notes}")
            print("\nStarting provider with debug mode ON")
            print("Step delay:", self.step_delay, "seconds")

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser and page"""
        if self.debug:
            print(f"\nInitializing {self.name} provider")
            print(f"Launching browser...")
            
        self.browser = await playwright.firefox.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        if self.debug:
            print(f"Navigating to: {self.config['url']}")
            
        # Navigate to provider URL
        await self.page.goto(self.config['url'])
        
        if self.debug:
            print("Initial page load complete")

    async def login(self) -> None:
        """Execute provider's login sequence"""
        if self.debug:
            print("\nStarting login sequence")
            print(f"Total login steps: {len(self.config['login_sequence'])}")
            
        for i, step in enumerate(self.config['login_sequence'], 1):
            if self.debug:
                print(f"\nLogin step {i}/{len(self.config['login_sequence'])}")
            await self._execute_step(step)

    async def search_patient(self) -> None:
        """Execute provider's patient search sequence"""
        if self.debug:
            print("\nStarting patient search sequence")
            print(f"Total search steps: {len(self.config['search_sequence'])}")
            print(f"Patient details: {self.patient}")
            
        for i, step in enumerate(self.config['search_sequence'], 1):
            if self.debug:
                print(f"\nSearch step {i}/{len(self.config['search_sequence'])}")
            await self._execute_step(step)
        
    async def _execute_step(self, step: Dict[str, Any]) -> None:
        """Execute a single step in a sequence with debug support"""
        action = step['action']
        
        if self.debug:
            print(f"\nStep: {step}")
            print(f"URL: {self.page.url}")
            
            # Show available elements if requested
            if input("\nPress Enter to continue (or 'p' to print page elements): ").lower() == 'p':
                await self._print_elements()
                
        try:
            if action == 'click':
                if self.debug:
                    print(f"Attempting to click element with label: {step['label']}")
                await self.page.get_by_label(step['label']).click()
                
            elif action == 'fill':
                value = self._get_value(step['value'])
                if self.debug:
                    print(f"Filling element '{step['label']}' with value: {value}")
                await self.page.get_by_label(step['label']).fill(value)
                
            elif action == 'wait_load':
                if self.debug:
                    print("Waiting for page load...")
                await self.page.wait_for_load_state("networkidle")
                if self.debug:
                    print("Page loaded")
                    
            elif action == 'wait_2fa':
                code_field = step['code_field']
                if self.debug:
                    print(f"Waiting for 2FA code in field: {code_field}")
                while not getattr(self.shared_state, code_field):
                    await asyncio.sleep(1)
                code = getattr(self.shared_state, code_field)
                setattr(self.shared_state, code_field, None)
                if self.debug:
                    print(f"Received 2FA code: {code}")
                await self.page.get_by_label(step['label']).fill(code)
            
            if self.debug:
                print("Step completed successfully")
                if self.step_delay > 0:
                    print(f"Debug delay: {self.step_delay} seconds...")
                    await asyncio.sleep(self.step_delay)
                
        except Exception as e:
            if self.debug:
                print(f"\nError executing step: {e}")
                await self._print_elements()
                if input("\nWould you like to retry this step? (y/n): ").lower() == 'y':
                    print("Retrying step...")
                    await self._execute_step(step)
                    return
            raise

    async def _print_elements(self) -> None:
        """Print all elements on the page with their attributes"""
        print("\nElements on page:")
        
        # Get all elements with any attributes
        elements = await self.page.query_selector_all('*[aria-label], *[placeholder], *[name], *[id], *[role], input, select, textarea')
        for element in elements:
            tag = await element.evaluate('el => el.tagName.toLowerCase()')
            attrs = {}
            
            # Get common attributes
            for attr in ['aria-label', 'placeholder', 'name', 'id', 'role', 'type']:
                value = await element.get_attribute(attr)
                if value:
                    attrs[attr] = value
                    
            # Print element with its attributes
            attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
            print(f"- <{tag} {attr_str}>")

    def _get_value(self, key: str) -> str:
        """Get a value from credentials or patient details"""
        if key.startswith('cred.'):
            return getattr(self.credentials, key[5:])
        elif key.startswith('patient.'):
            return getattr(self.patient, key[8:])
        return key

    async def cleanup(self) -> None:
        """Clean up browser resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def wait_for_exit(self) -> None:
        """Wait for exit signal"""
        print(f"{self.name} paused for interaction")
        while not self.shared_state.exit:
            await asyncio.sleep(0.1)
        print(f"{self.name} received exit signal")

# Provider configurations
PROVIDER_CONFIGS = {
    'Medway': {
        'url': 'https://www.medway.com.au/login',
        'debug_notes': {
            'login': 'Standard login form with username/password',
            'known_issues': [
                'Sometimes the login button needs a second click',
                'Wait for page load after login is critical'
            ],
            'selectors': [
                'Username and Password fields use aria-label',
                'Login button uses role="button"',
                'Patient search fields use aria-label'
            ],
            'timing': [
                'Allow page to fully load before entering credentials',
                'Wait for redirect after login',
                'Search results may take a few seconds to load'
            ]
        },
        'login_sequence': [
            {'action': 'click', 'label': 'Username'},
            {'action': 'fill', 'label': 'Username', 'value': 'cred.user_name'},
            {'action': 'click', 'label': 'Password'},
            {'action': 'fill', 'label': 'Password', 'value': 'cred.user_password'},
            {'action': 'click', 'label': 'Log in'},
            {'action': 'wait_load'}
        ],
        'search_sequence': [
            {'action': 'click', 'label': 'Patient surname'},
            {'action': 'fill', 'label': 'Patient surname', 'value': 'patient.family_name'},
            {'action': 'click', 'label': 'Patient given name(s)'},
            {'action': 'fill', 'label': 'Patient given name(s)', 'value': 'patient.given_name'}
        ]
    },
    'QScript': {
        'url': 'https://hp.qscript.health.qld.gov.au/home',
        'debug_notes': {
            'login': 'Multi-step login: username -> password -> 2FA -> PIN',
            'known_issues': [
                'PIN entry may fail if page not fully loaded',
                '2FA timeout is strict - enter code quickly',
                'Verify button sometimes needs extra wait'
            ],
            'selectors': [
                'Username/password fields use placeholder',
                'Next/Verify buttons use role="button"',
                'Patient search fields use data-test-id'
            ],
            'timing': [
                'Wait for page load between each login step',
                'Quick 2FA code entry required (timeout ~30s)',
                'PIN entry needs full page load',
                'Search can be slow with large result sets'
            ],
            'search_tips': [
                'First name and surname must be exact',
                'DOB format must be DD/MM/YYYY with slashes',
                'Search is case-sensitive'
            ]
        },
        'login_sequence': [
            {'action': 'click', 'label': 'Enter username'},
            {'action': 'fill', 'label': 'Enter username', 'value': 'cred.user_name'},
            {'action': 'click', 'label': 'Next'},
            {'action': 'wait_load'},
            {'action': 'click', 'label': 'Enter password'},
            {'action': 'fill', 'label': 'Enter password', 'value': 'cred.user_password'},
            {'action': 'click', 'label': 'Log In'},
            {'action': 'wait_load'},
            {'action': 'wait_2fa', 'label': 'Verification code', 'code_field': 'QScript_code'},
            {'action': 'click', 'label': 'Verify'},
            {'action': 'wait_load'},
            {'action': 'fill', 'label': 'Enter PIN', 'value': 'cred.PIN'},
            {'action': 'click', 'label': 'Save PIN and Log In'}
        ],
        'search_sequence': [
            {'action': 'click', 'label': 'patientSearchFirstName'},
            {'action': 'fill', 'label': 'patientSearchFirstName', 'value': 'patient.given_name'},
            {'action': 'click', 'label': 'patientSearchSurname'},
            {'action': 'fill', 'label': 'patientSearchSurname', 'value': 'patient.family_name'},
            {'action': 'fill', 'label': 'dateOfBirth', 'value': 'patient.dob'},
            {'action': 'click', 'label': 'Search'}
        ]
    },
    'FourCyte': {
        'url': 'https://www.4cyte.com.au/clinicians',
        'debug_notes': {
            'login': 'Portal redirect -> login -> 2FA -> Break Glass',
            'known_issues': [
                'Portal redirect can be slow',
                'Break Glass button timing is critical',
                'Patient search requires exact format'
            ],
            'selectors': [
                'Web Results Portal link by name',
                'Username/Password fields by placeholder',
                'Break Glass link by exact text',
                'Patient search uses combined name field'
            ],
            'timing': [
                'Wait for portal redirect before login',
                'Allow time for 2FA popup',
                'Break Glass needs networkidle',
                'Search results load progressively'
            ],
            'search_tips': [
                'Name format must be "Surname [space] First name"',
                'DOB must include slashes (DD/MM/YYYY)',
                'Search is not case-sensitive'
            ],
            'popup_handling': [
                'Results portal opens in new window',
                'Break Glass confirmation needs Accept click',
                'Search results may open in new tab'
            ]
        },
        'login_sequence': [
            {'action': 'click', 'label': 'Web Results Portal'},
            {'action': 'click', 'label': 'Access results portal'},
            {'action': 'click', 'label': 'Username'},
            {'action': 'fill', 'label': 'Username', 'value': 'cred.user_name'},
            {'action': 'click', 'label': 'Password'},
            {'action': 'fill', 'label': 'Password', 'value': 'cred.user_password'},
            {'action': 'click', 'label': 'Log in'},
            {'action': 'wait_2fa', 'label': '-digit code', 'code_field': 'FourCyte_code'},
            {'action': 'click', 'label': 'Submit'},
            {'action': 'click', 'label': 'Patients'},
            {'action': 'click', 'label': ' Break Glass'},
            {'action': 'click', 'label': 'Accept'}
        ],
        'search_sequence': [
            {'action': 'fill', 'label': 'Surname [space] First name', 'value': 'patient.family_name patient.given_name'},
            {'action': 'click', 'label': 'Birth Date (Required)'},
            {'action': 'fill', 'label': 'Birth Date (Required)', 'value': 'patient.dob'},
            {'action': 'click', 'label': 'Search'}
        ]
    }
}
