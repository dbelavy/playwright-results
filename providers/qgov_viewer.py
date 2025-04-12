from typing import Optional

from playwright._impl._errors import TimeoutError
from playwright.async_api import Playwright, async_playwright

from models import Credentials, PatientDetails, Session, SharedState
from utils import convert_date_format, convert_gender


class QGovViewerSession(Session):
    name = "QGov Viewer"  # Make name a class attribute
    required_fields = ["family_name", "dob", "medicare_number", "sex"]
    provider_group = "General"
    credentials_key = "QGov"

    def __init__(
        self,
        credentials: Credentials,
        patient: PatientDetails,
        shared_state: SharedState,
    ):
        super().__init__(credentials, patient, shared_state)

    @classmethod
    def create(
        cls, patient: PatientDetails, shared_state: SharedState
    ) -> Optional["QGovViewerSession"]:
        """Create a new QGov Viewer session"""
        return super().create(patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://hpp.health.qld.gov.au/my.policy")
        await self.page.goto("https://hpp.health.qld.gov.au/")

    async def login(self) -> None:
        """Handle login process"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Wait for and click login link
        #await self.page.wait_for_selector('a:text("Log in")', state="visible")
        #await self.page.get_by_role("link", name="Log in").click()
        await self.page.get_by_role("link", name="Log in").click()


        # Wait for QGov login notification
        # await self.page.wait_for_selector('button[aria-label="Continue with QDI (formerly"]', state="visible")

        # await self.page.locator('button[aria-label="Continue with QGov"]').click()
        await self.page.get_by_label("Continue with QDI (formerly").click()
        # Wait for email field and fill credentials
        # await self.page.wait_for_selector(  'input[placeholder="Your email address"]', state="visible" )
        await self.page.get_by_label("Email address").click()
        await self.page.get_by_label("Email address").fill(self.credentials.user_name)

        #await self.page.get_by_placeholder("Your email address").fill(self.credentials.user_name   )

        # Wait for password field and fill
        # await self.page.wait_for_selector('input[type="password"]', state="visible")
        await self.page.locator('[aria-label="Password"][type="password"]').click()
        await self.page.locator('[aria-label="Password"][type="password"]').fill(self.credentials.user_password)

        # Click login and wait for navigation
        await self.page.get_by_role("button", name="Continue").click()
        #await self.page.get_by_role("button", name="Log in").click()
        #await self.page.wait_for_load_state("domcontentloaded")

        # implement SMS listener
        # Handle 2FA
        try:
            self.shared_state.new_2fa_request = "QGov"  # Tell monitor we need a code
            two_fa_code = await self.shared_state.wait_for_2fa("QGov")
            await self.page.get_by_label("Enter the 6-digit code").click()
            await self.page.get_by_label("Enter the 6-digit code").fill(two_fa_code)
            await self.page.get_by_role("button", name="Continue").click()
            await self.page.wait_for_load_state("networkidle")
        except asyncio.CancelledError:
            print("QScript login cancelled - exiting")
            raise


    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Wait for Medicare field and fill
        await self.page.wait_for_selector("#MedicareNumber", state="visible")
        await self.page.locator("#MedicareNumber").fill(self.patient.medicare_number)

        # Handle gender selection with conversion
        gender = convert_gender(self.patient.sex, "M1F2I3")
        await self.page.get_by_label("Sex").select_option(gender)

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")
        await self.page.get_by_placeholder("DD/MM/YYYY").fill(converted_dob)
        await self.page.get_by_placeholder("DD/MM/YYYY").press("Tab")

        # Fill surname and search
        await self.page.get_by_label("Patient Surname").fill(self.patient.family_name)
        await self.page.get_by_role("button", name="Search").click()

        # Handle popup
        async def handle_popup(popup):
            await popup.wait_for_load_state()

        # Set up popup handler first
        print("Waiting for popup")
        self.page.on("popup", handle_popup)

        # Click viewer with timeout handling
        print("Clicking on the Viewer")
        try:
            await self.page.get_by_role("link", name="The Viewer").click(timeout=30000)
        except TimeoutError:
            print("Timeout occurred while trying to click 'The Viewer' link.")


async def QGovViewer_process(patient: PatientDetails, shared_state: SharedState):
    # Create and run session
    session = QGovViewerSession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
