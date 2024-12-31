from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, generate_2fa_code
from typing import Optional
import asyncio

# Define provider requirements at module level
REQUIRED_FIELDS = []  # No patient details required
PROVIDER_GROUP = "Other"
CREDENTIALS_KEY = "Meditrust"  # Matches the key in credentials.json

class MeditrustSession(Session):
    def __init__(self, credentials: Credentials, patient: Optional[PatientDetails], shared_state: SharedState):
        super().__init__("Meditrust", credentials, patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        print(f"Starting {self.name} process")
        print(f"Credentials are loaded for {self.credentials.user_name}")
        
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://www.meditrust.com.au/mtv4/home")

    async def login(self) -> None:
        """Handle login process including 2FA"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Initial login
        await self.page.get_by_role("link", name=" Login").click()
        await self.page.get_by_label("Username:").click()
        await self.page.get_by_label("Username:").fill(self.credentials.user_name)
        await self.page.get_by_label("Password:").click()
        await self.page.get_by_label("Password:").fill(self.credentials.user_password)
        await self.page.get_by_role("button", name="Login").click()

        # Handle 2FA
        await self.page.get_by_placeholder("Authentication Code").click()
        two_fa_code = generate_2fa_code(self.credentials.totp_secret)
        await self.page.get_by_placeholder("Authentication Code").fill(two_fa_code)
        await self.page.get_by_role("button", name="Submit").click()

    async def search_patient(self) -> None:
        """No patient search needed for Meditrust"""
        pass

async def run_meditrust_process(patient: Optional[PatientDetails], shared_state: SharedState):
    # Load credentials
    credentials = load_credentials(shared_state, "Meditrust")
    if not credentials:
        print("Failed to load Meditrust credentials")
        return

    # Create and run session
    session = MeditrustSession(credentials, patient, shared_state)
    async with async_playwright() as playwright:
        await session.run(playwright)
