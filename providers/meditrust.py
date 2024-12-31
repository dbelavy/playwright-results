from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, generate_2fa_code
from typing import Optional
import asyncio

class MediTrustSession(Session):
    name = "MediTrust"  # Make name a class attribute
    required_fields = []  # No patient details required
    provider_group = "Other"
    credentials_key = "Meditrust"
    
    def __init__(self, credentials: Credentials, patient: Optional[PatientDetails], shared_state: SharedState):
        super().__init__(credentials, patient, shared_state)

    @classmethod
    def create(cls, patient: Optional[PatientDetails], shared_state: SharedState) -> Optional['MediTrustSession']:
        """Create a new MediTrust session"""
        return super().create(patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
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
        """No patient search needed for MediTrust"""
        pass

async def MediTrust_process(patient: Optional[PatientDetails], shared_state: SharedState):
    # Create and run session
    session = MediTrustSession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
