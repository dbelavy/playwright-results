import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from core import PageDataCollector
from pathlib import Path
from playwright.async_api import Browser, BrowserContext, Page, Playwright


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
    def load(cls, file_path: str, provider: str) -> "Credentials":
        """Load credentials for a specific provider"""
        try:
            with open(file_path, "r") as file:
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
    two_fa_codes: Dict[str, str] = field(default_factory=dict)
    two_fa_events: Dict[str, asyncio.Event] = field(default_factory=dict)
    new_2fa_request: Optional[str] = None  # Keep this for monitor compatibility
    exit: bool = False
    credentials_file: str = "credentials.json"

    async def wait_for_2fa(self, provider_name: str) -> str:
        """Wait for 2FA code with periodic reminders
        Args:
            provider_name: Name of provider requesting 2FA
        Returns:
            The 2FA code
        Raises:
            asyncio.CancelledError if exit signal received
        """
        if provider_name not in self.two_fa_events:
            self.two_fa_events[provider_name] = asyncio.Event()

        print(f"\nWaiting for {provider_name} 2FA code...")

        while not self.two_fa_events[provider_name].is_set():
            # Check for exit signal
            if self.exit:
                raise asyncio.CancelledError("Exit signal received")

            # Wait for either the event or 30 seconds
            try:
                await asyncio.wait_for(
                    self.two_fa_events[provider_name].wait(), timeout=30
                )
            except asyncio.TimeoutError:
                # No code yet, print reminder and keep waiting
                print(f"Still waiting for {provider_name} 2FA code...")

        return self.two_fa_codes[provider_name]

    def set_2fa_code(self, provider_name: str, code: str):
        """Set 2FA code for any provider"""
        self.two_fa_codes[provider_name] = code
        if provider_name in self.two_fa_events:
            self.two_fa_events[provider_name].set()


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

        # Validate Medicare number if provided
        if self.medicare_number:
            # Remove any spaces or non-digit characters
            cleaned_number = "".join(filter(str.isdigit, self.medicare_number))
            if len(cleaned_number) < 11:
                raise ValueError("Medicare number must be at least 11 digits")
            self.medicare_number = cleaned_number

    @classmethod
    def from_args(cls, args, required_fields: list[str]):
        """Create PatientDetails from argparse args and required fields"""
        details = {}

        # Handle each field based on args or user input
        details["family_name"] = (
            args.family_name
            if args.family_name
            else (
                input("Enter Family Name: ")
                if "family_name" in required_fields
                else None
            )
        )

        details["given_name"] = (
            args.given_name
            if args.given_name
            else (
                input("Enter Given Name: ") if "given_name" in required_fields else None
            )
        )

        if "dob" in required_fields:
            if args.dob:
                details["dob"] = args.dob
            else:
                while True:
                    dob_input = input("Enter DOB (DDMMYYYY): ")
                    try:
                        datetime.strptime(dob_input, "%d%m%Y")
                        details["dob"] = dob_input
                        break
                    except ValueError:
                        print(
                            "Invalid date. Please enter a valid date in DDMMYYYY format."
                        )

        if "medicare_number" in required_fields:
            if args.medicare_number:
                details["medicare_number"] = str(args.medicare_number)
            else:
                while True:
                    medicare_input = input("Enter Medicare Number: ")
                    cleaned_number = "".join(filter(str.isdigit, medicare_input))
                    if len(cleaned_number) >= 11:
                        details["medicare_number"] = cleaned_number
                        break
                    print("Invalid Medicare number. Must be at least 11 digits.")

        if "sex" in required_fields:
            details["sex"] = args.sex.upper() if args.sex else None
            while not details["sex"] or details["sex"] not in ["M", "F", "I"]:
                details["sex"] = input("Enter Sex (M, F, or I): ").upper()

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


class Session(ABC):
    """Base session class for handling provider interactions"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider display name"""
        pass

    @property
    @abstractmethod
    def required_fields(self) -> list[str]:
        """Required patient fields"""
        pass

    @property
    @abstractmethod
    def provider_group(self) -> str:
        """Provider group (e.g., 'Pathology', 'Radiology')"""
        pass

    @property
    @abstractmethod
    def credentials_key(self) -> str:
        """Key for credentials.json"""
        pass

    def __init__(
        self,
        credentials: Credentials,
        patient: PatientDetails,
        shared_state: SharedState,
    ):
        self.credentials = credentials
        self.patient = patient
        self.shared_state = shared_state
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    @classmethod
    def create(
        cls, patient: PatientDetails, shared_state: SharedState
    ) -> Optional["Session"]:
        """Create a new session with loaded credentials"""
        from utils import load_credentials  # Import here to avoid circular dependency

        credentials = load_credentials(shared_state, cls.credentials_key)
        if not credentials:
            print(f"Failed to load {cls.credentials_key} credentials")
            return None
        return cls(credentials, patient, shared_state)

    @abstractmethod
    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        task = "initializing browser"

        pass

    @abstractmethod
    async def login(self) -> None:
        """Handle login process"""
        pass

    @abstractmethod
    async def search_patient(self) -> None:
        """Handle patient search"""
        pass

    async def wait_for_exit(self) -> None:
        """Wait for exit signal"""
        print(f"{self.name} paused for interaction")
        while not self.shared_state.exit:
            await asyncio.sleep(0.1)
        print(f"{self.name} received exit signal")

    async def cleanup(self) -> None:
        """Clean up resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def run(self, playwright: Playwright) -> None:
        """Run the complete session"""
        # Initialize collector for this session
        collector = PageDataCollector(
            output_dir=Path(f"screen_shots_data/{self.name.lower()}")
        )
        
        try:
            print(f"\n=== Starting {self.name} Process ===")
            await self.initialize(playwright)
            # if self.page:  # Capture post-initialization state
            #     await collector.capture_page_data(
            #         self.page,
            #         task="initialization"
            #     )

            print(f"\n=== {self.name} Login ===")
            await self.login()

            print(f"\n=== {self.name} Patient Search ===")
            try:
                await self.search_patient()
            except Exception as e:
                print(f"Error during patient search: {e}")
            print("\n=== Search Complete ===")
            await self.wait_for_exit()
        finally:
            await self.cleanup()
