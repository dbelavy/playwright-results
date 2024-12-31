from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format
import asyncio

# Define provider metadata at module level
REQUIRED_FIELDS = ['family_name', 'given_name', 'dob']
PROVIDER_GROUP = "Radiology"

class QXRSession(Session):
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__("QXR", credentials, patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        print(f"\n=== Starting {self.name} Process ===")
        # print(f"Launching browser and navigating to QXR...")
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://qxrpacs.com.au/Portal/app#/")
        await self.page.wait_for_load_state("networkidle")
        # print("✓ Page loaded successfully")

    async def login(self) -> None:
        """Handle login process"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        print("\n=== QXR Login ===")
        # print(f"Attempting login with username: {self.credentials.user_name}")
        
        # Username entry
        # print("Entering username...")
        await self.page.get_by_placeholder("Username").click()
        await self.page.get_by_placeholder("Username").fill(self.credentials.user_name)
        
        # Password entry
        # print("Entering password...")
        await self.page.get_by_placeholder("Password").click()
        await self.page.get_by_placeholder("Password").fill(self.credentials.user_password)
        
        # Submit login
        # print("Submitting login form...")
        await self.page.get_by_role("button").click()
        await self.page.wait_for_load_state("networkidle")
        # print("✓ Login submitted")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        print("\n=== QXR Patient Search ===")
        # print(f"Patient Details:")
        # print(f"- Family Name: {self.patient.family_name}")
        # print(f"- Given Name: {self.patient.given_name}")
        # print(f"- DOB (raw): {self.patient.dob}")
        
        # Click search field
        # print("\n1. Clicking search field...")
        await self.page.get_by_placeholder("Search patient name, id,").click()
        await self.page.wait_for_load_state("networkidle")
        # print("✓ Search field clicked")
        
        # Enter patient name in format "surname,firstname"
        search_text = f"{self.patient.family_name}, {self.patient.given_name}"
        # print(f"\n2. Entering search text: {search_text}")
        await self.page.get_by_placeholder("Search patient name, id,").fill(search_text)
        await self.page.wait_for_load_state("networkidle")
        # print("✓ Search text entered")
        

        # Handle DOB popup
        # print("\n3. Opening DOB popup...")
        try:
            # print("Looking for arrow...")
            arrow = self.page.locator("div.arrow.arrow-up").first
            await arrow.wait_for(state="visible", timeout=5000)
            # print("✓ Found arrow")
            
            # print("Clicking arrow...")
            await arrow.click()
            # print("✓ Clicked arrow")
            
            # Add delay to visually verify popup
            # print("Waiting 3 seconds to verify popup...")
            await self.page.wait_for_timeout(1000)
            
        except Exception as e:
            print(f"\n❌ Error clicking arrow: {str(e)}")
            await self.page.screenshot(path="qxr_error.png")
            raise

        # Handle DOB
        # print("\n4. Processing DOB...")
        raw_dob = self.patient.dob
        converted_dob = convert_date_format(raw_dob, "%d%m%Y", "%d/%m/%Y")
        # print(f"- Input DOB: {raw_dob}")
        # print(f"- Converted DOB: {converted_dob}")
        
        # Wait for and enter DOB
        # print("\n5. Entering DOB...")
        # print("Waiting for DOB field...")
        dob_field = self.page.get_by_placeholder("DD/MM/YYYY")
        await dob_field.wait_for(state="visible", timeout=5000)
        # print("✓ DOB field found")
        
        await dob_field.click()
        await dob_field.fill(converted_dob)
        await self.page.wait_for_timeout(1000)
        # print(f"✓ DOB entered: {converted_dob}")
        
        # Wait for and click search button
        # print("\n6. Submitting search...")
        try:
            # print("Waiting for search button...")
            search_button = self.page.get_by_role("button").nth(1)
            await search_button.wait_for(state="visible", timeout=5000)
            # print("✓ Search button found")
            
            await search_button.click()
            await self.page.wait_for_load_state("networkidle")
            # print("✓ Search submitted")
        except Exception as e:
            print(f"\n❌ Error clicking search button: {str(e)}")
            await self.page.screenshot(path="qxr_search_error.png")
            raise
        
        print("\n=== Search Complete ===")

async def run_QXR_process(patient: PatientDetails, shared_state: SharedState):
    """Main entry point for QXR provider"""
    # Load credentials
    print("\nInitializing QXR process...")
    credentials = load_credentials(shared_state, "QXR")
    if not credentials:
        print("❌ Failed to load QXR credentials")
        return

    # Create and run session
    session = QXRSession(credentials, patient, shared_state)
    async with async_playwright() as playwright:
        await session.run(playwright)
