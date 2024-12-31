# Define provider metadata at module level
REQUIRED_FIELDS = ['family_name', 'given_name', 'dob']
PROVIDER_GROUP = "Pathology"

from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format, generate_2fa_code

class FourCyteSession(Session):
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__("4cyte", credentials, patient, shared_state)
        self.active_page: Page | None = None  # For handling popup window

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        print(f"Starting {self.name} process")
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.active_page = self.page  # Start with main page as active
        await self.page.goto("https://www.4cyte.com.au/clinicians")

    async def login(self) -> None:
        """Handle login process including 2FA and popup"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Click Web Results Portal
        await self.page.get_by_role("link", name="Web Results Portal").click()

        # Handle popup window
        async with self.page.expect_popup() as page1_info:
            await self.page.get_by_label("Access results portal").click()
            popup = await page1_info.value
            self.active_page = popup  # Update active page to popup

        # Login in popup window
        await self.active_page.get_by_placeholder("Username").click()
        await self.active_page.get_by_placeholder("Username").fill(self.credentials.user_name)
        await self.active_page.get_by_placeholder("Password").click()
        await self.active_page.get_by_placeholder("Password").fill(self.credentials.user_password)
        await self.active_page.get_by_role("button", name="Log in").click()

        # Handle 2FA
        two_fa_code = generate_2fa_code(self.credentials.totp_secret)
        print(f"Generated 2FA code: {two_fa_code}")

        await self.page.wait_for_load_state("networkidle")
        await self.active_page.get_by_placeholder("-digit code").click()
        await self.active_page.get_by_placeholder("-digit code").fill(two_fa_code)
        await self.active_page.get_by_role("button", name="Submit").click()

        # Navigate to patients and handle break glass
        await self.active_page.get_by_role("button", name="Patients").click()
        await self.active_page.get_by_role("link", name=" Break Glass").click()
        await self.active_page.get_by_role("button", name="Accept").click()

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.active_page:
            raise RuntimeError("Session not initialized")

        # Convert DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")

        # Fill combined name field (surname + first name)
        await self.active_page.get_by_placeholder("Surname [space] First name").fill(
            f'{self.patient.family_name} {self.patient.given_name}'
        )
        
        # Fill DOB
        await self.active_page.get_by_placeholder("Birth Date (Required)").click()
        await self.active_page.get_by_placeholder("Birth Date (Required)").fill(converted_dob)
        
        # Initiate search
        await self.active_page.get_by_role("button", name="Search").click()

async def run_fourcyte_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials
    credentials = load_credentials(shared_state, "4cyte")
    if not credentials:
        print("Failed to load 4cyte credentials")
        return

    # Create and run session
    session = FourCyteSession(credentials, patient, shared_state)
    async with async_playwright() as playwright:
        await session.run(playwright)
