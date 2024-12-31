from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format, generate_2fa_code
from typing import Optional

class MaterPathologySession(Session):
    name = "Mater Pathology"  # Make name a class attribute
    required_fields = ['family_name', 'given_name', 'dob']
    provider_group = "Pathology"
    credentials_key = "MaterPath"
    
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__(credentials, patient, shared_state)

    @classmethod
    def create(cls, patient: PatientDetails, shared_state: SharedState) -> Optional['MaterPathologySession']:
        """Create a new Mater Pathology session"""
        return super().create(patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto('https://pathresults.mater.org.au/')
        await self.page.wait_for_load_state("networkidle")

    async def login(self) -> None:
        """Handle login process including 2FA"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Click external practitioner button
        await self.page.get_by_role("button", name="I am an External Practitioner").click()
        await self.page.wait_for_load_state("networkidle")

        # Login process
        await self.page.get_by_label("Username").click()
        await self.page.get_by_label("Username").fill(self.credentials.user_name)
        await self.page.get_by_role("button", name="Next").click()
        await self.page.wait_for_load_state("networkidle")

        # Handle password entry with retries
        password_entered = False
        max_attempts = 5
        attempt = 0

        while not password_entered and attempt < max_attempts:
            attempt += 1
            is_password_visible = False
            try:
                await self.page.wait_for_selector('input[type="Password"]', state="visible", timeout=2000)
                is_password_visible = True
            except Exception:
                is_password_visible = False

            try:
                if is_password_visible:
                    await self.page.get_by_label("Password").fill(self.credentials.user_password)
                    await self.page.get_by_role("button", name="Verify").click()
                    await self.page.wait_for_load_state("networkidle")
                    password_entered = True
                    continue
            except Exception as e:
                print(f"Password field not immediately visible: {e}")

            try:
                print(f"Trying 'Verify with something else' path - attempt {attempt}")
                verify_button = await self.page.wait_for_selector('a:text("Verify with something else")', timeout=2000)
                if verify_button:
                    await verify_button.click()
                    await self.page.wait_for_load_state("networkidle")
                    await self.page.get_by_label("Select Password.").click()
                    await self.page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"Could not find 'Verify with something else': {e}")

        if not password_entered:
            raise RuntimeError("Failed to enter password after maximum attempts")

        # Handle 2FA
        try:
            # Check if we need to select OTP method
            try:
                authenticator_selector = 'a[aria-label="Select Google Authenticator"]'
                await self.page.wait_for_selector(authenticator_selector, timeout=2000)
                await self.page.locator(authenticator_selector).click()
            except Exception:
                print("Direct OTP entry available")

            # Enter 2FA code
            two_fa_code = generate_2fa_code(self.credentials.totp_secret)
            print(f"Generated 2FA code: {two_fa_code}")
            await self.page.get_by_label("Enter code").click()
            await self.page.get_by_label("Enter code").fill(two_fa_code)
            await self.page.get_by_role("button", name="Verify").click()
            await self.page.wait_for_load_state("networkidle")
        except Exception as e:
            raise RuntimeError(f"Error during 2FA entry: {e}")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        await self.page.get_by_placeholder("Surname").click()
        await self.page.get_by_placeholder("Surname").fill(self.patient.family_name)

        await self.page.get_by_placeholder("First Name").click()
        await self.page.get_by_placeholder("First Name").fill(self.patient.given_name)

        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%Y-%m-%d")
        await self.page.get_by_placeholder("Date of Birth").fill(converted_dob)

        await self.page.get_by_role("button", name="Search").click()

async def MaterPathology_process(patient: PatientDetails, shared_state: SharedState):
    # Create and run session
    session = MaterPathologySession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
