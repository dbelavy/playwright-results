from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format
import asyncio

# Define provider requirements at module level
REQUIRED_FIELDS = ['family_name', 'given_name', 'dob']

class IMedSession(Session):
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__("I-Med", credentials, patient, shared_state)
        self.active_page: Page | None = None  # For handling popup window

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        print(f"Starting {self.name} process")
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self.active_page = self.page  # Start with main page as active
        await self.page.goto("https://i-med.com.au/resources/access-patient-images")

    async def login(self) -> None:
        """Handle login process including location selection and popup"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # Location selection
        await self.page.get_by_test_id("dropdownInput").click()
        await self.page.get_by_test_id("dropdownInput").fill(self.credentials.postcode)
        await self.page.get_by_test_id("dropdownInput").press("Enter")
        await self.page.get_by_role("button", name=self.credentials.suburb).click()

        # Handle popup window
        async with self.page.expect_popup() as page1_info:
            await self.page.get_by_role("button", name="ACCESS I-MED ONLINE").click()
            popup = await page1_info.value
            self.active_page = popup  # Update active page to popup

        # Add a small delay to ensure popup is ready
        await asyncio.sleep(2)
        
        # Fill in login credentials using data-testid selectors
        await self.active_page.locator('[data-testid="SingleLineTextInputField-FormControl"][name="uid"]').fill(self.credentials.user_name)
        await self.active_page.locator('[data-testid="SingleLineTextInputField-FormControl"][name="password"]').fill(self.credentials.user_password)
        await self.active_page.get_by_test_id("login-button").click()
     
        # Wait for the search page and check available elements
        await self.active_page.wait_for_load_state("networkidle")
        
        print("After login - checking available elements...")
        elements = await self.active_page.evaluate("""() => {
            const elements = document.querySelectorAll('[data-testid]');
            return Array.from(elements).map(el => ({
                testId: el.getAttribute('data-testid'),
                type: el.getAttribute('type'),
                name: el.getAttribute('name')
            }));
        }""")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.active_page:
            raise RuntimeError("Session not initialized")

        # Try alternative selectors for the patient name field
        try:
            # Try by placeholder or label if it exists
            # Use the exact field attributes we found
            await self.active_page.locator('[data-testid="SingleLineTextInputField-FormControl"][name="nameOrPatientId"]').fill(f'{self.patient.given_name} {self.patient.family_name}')

            # For DOB, use the exact test ID we found
            await self.active_page.get_by_test_id("DOB-input-field-form-control").click()
            await self.active_page.get_by_test_id("DOB-input-field-form-control").type(convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y"))

        except:
            try:
                # Try by role
                await self.active_page.get_by_role("textbox", name="Patient Name").fill(f'{self.patient.given_name} {self.patient.family_name}')
            except:
                # If all else fails, try waiting and using a more specific selector
                await self.active_page.wait_for_selector('input[type="text"][data-testid="SingleLineTextInputField-FormControl"]')
                await self.active_page.locator('input[type="text"][data-testid="SingleLineTextInputField-FormControl"]').first.fill(
                    f'{self.patient.given_name} {self.patient.family_name}'
                )

        # Request everything available
        await self.active_page.get_by_role("button", name="Referred by me").click()
        await self.active_page.get_by_role("button", name="Referred by anyone").click()
        await self.active_page.get_by_role("button", name="All listed practices").click()
        await self.active_page.get_by_role("button", name="All listed practices").click()
        await self.active_page.get_by_role("button", name="Past week").click()
        await self.active_page.get_by_role("button", name="All time").click()
        await self.active_page.get_by_test_id("mobile-search").click()

async def run_imed_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials
    credentials = load_credentials(shared_state, "IMed")
    if not credentials:
        print("Failed to load I-Med credentials")
        return

    # Create and run session
    session = IMedSession(credentials, patient, shared_state)
    async with async_playwright() as playwright:
        await session.run(playwright)
