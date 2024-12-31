from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format

# Define provider metadata at module level
REQUIRED_FIELDS = ['family_name', 'given_name', 'dob']
PROVIDER_GROUP = "Pathology"
CREDENTIALS_KEY = "Sonic"  # Matches the key in credentials.json

class SonicSession(Session):
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__("Sonic", credentials, patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        print(f"Starting SNP process")
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://www.sonicdx.com.au/#/login")
        await self.page.wait_for_load_state("networkidle")

    async def login(self) -> None:
        """Handle login process including business selection"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Fill username and select SNP business
        await self.page.locator("#username").click()
        await self.page.locator("#username").fill(self.credentials.user_name)
        await self.page.locator("#selected-business").select_option("SNP")
        
        # Fill password and login
        await self.page.locator("#password").click()
        await self.page.locator("#password").fill(self.credentials.user_password)
        await self.page.get_by_role("button", name="Login").click()
        await self.page.wait_for_load_state("networkidle")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Navigate to search page
        await self.page.get_by_role("link", name="Search", exact=True).click()
        
        # Fill patient details
        await self.page.locator("#familyName").click()
        await self.page.locator("#familyName").fill(self.patient.family_name)
        await self.page.locator("#familyName").press("Tab")
        await self.page.locator("#givenName").fill(self.patient.given_name)
        await self.page.locator("#givenName").press("Tab")
        await self.page.get_by_label("Sex").press("Tab")

        # Convert and fill DOB
        converted_dob = convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")
        await self.page.get_by_placeholder("DD/MM/YYYY").fill(converted_dob)

        # Initiate search
        await self.page.get_by_role("button", name="Search").click()

async def run_SNP_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials
    credentials = load_credentials(shared_state, "Sonic")
    if not credentials:
        print("Failed to load Sonic credentials")
        return

    # Create and run session
    session = SonicSession(credentials, patient, shared_state)
    async with async_playwright() as playwright:
        await session.run(playwright)
