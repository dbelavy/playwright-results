from playwright.async_api import Playwright, async_playwright, Page
from models import PatientDetails, SharedState, Credentials, Session
from utils import load_credentials, convert_date_format
from typing import Optional
import asyncio

# Define provider metadata at module level
REQUIRED_FIELDS = ['family_name', 'given_name', 'dob']
PROVIDER_GROUP = "Radiology"
CREDENTIALS_KEY = "QScan"  # Matches the key in credentials.json

class QScanSession(Session):
    name = "QScan"  # Make name a class attribute
    
    def __init__(self, credentials: Credentials, patient: PatientDetails, shared_state: SharedState):
        super().__init__(self.name, credentials, patient, shared_state)

    @classmethod
    def create(cls, patient: PatientDetails, shared_state: SharedState) -> Optional['QScanSession']:
        """Create a new QScan session"""
        return super().create(cls.name, CREDENTIALS_KEY, patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
        # print(f"Launching browser and navigating to QScan...")
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.page.goto("https://www.qscaniq.com.au/Portal/app#/")
        await self.page.wait_for_load_state("networkidle")
        # print("✓ Page loaded successfully")

    async def login(self) -> None:
        """Handle login process"""
        if not self.page:
            raise RuntimeError("Session not initialized")

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
        
        # Check for password change page
        current_url = self.page.url
        if "changePassword" in current_url:
            # print("\nDetected password change page, redirecting...")
            await self.page.goto("https://www.qscaniq.com.au/Portal/app#/")
            await self.page.wait_for_load_state("networkidle")
            # print("✓ Redirected to main page")

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.page:
            raise RuntimeError("Session not initialized")

        # print(f"Patient Details:")
        # print(f"- Family Name: {self.patient.family_name}")
        # print(f"- Given Name: {self.patient.given_name}")
        # print(f"- DOB (raw): {self.patient.dob}")
        
        # Click Break Glass button
        # print("\n1. Clicking Break Glass button...")
        await self.page.locator("a.btn.portalButton.selfServeButton[title='Access restricted studies']").click()
        # print("✓ Break Glass clicked")
        
        # Wait for 1 seconds after Break Glass
        # print("Waiting 1 seconds after Break Glass...")
        await self.page.wait_for_timeout(1000)
        # print("✓ Wait complete")
        
        # Handle privacy dialog and input fields
        # print("\n2. Handling privacy dialog...")
        # print("Checking acknowledgment checkbox...")
        await self.page.locator("input#gwt-uid-1[type='checkbox']").click()
        # print("✓ Checkbox checked")
        
        # Wait and tab to patient name field
        # print("\n3. Navigating to patient name field...")
        await self.page.wait_for_timeout(1000)
        await self.page.keyboard.press("Tab")  # Skip patient ID field

        # Enter patient name
        search_text = f"{self.patient.family_name},{self.patient.given_name}"
        # print(f"\n4. Entering patient name: {search_text}")
        await self.page.keyboard.type(search_text)
        # print("✓ Patient name entered")
        
        # Tab to DOB field
        # print("\n5. Navigating to DOB field...")
        await self.page.keyboard.press("Tab")
        
        # Enter DOB
        dob = convert_date_format(self.patient.dob, "%d%m%Y", "%Y%m%d")
        # print(f"\n6. Entering DOB: {dob}")
        await self.page.keyboard.type(dob)
        # print("✓ DOB entered")
        
        # Click Check Patient button
        # print("\n7. Clicking Check Patient button...")
        await self.page.locator("button.gwt-Button.checkPatientButton").click()
        await self.page.wait_for_load_state("networkidle")
        # print("✓ Search submitted")
        
        # Check search results
        # print("\n8. Checking search results...")
        try:
            # First check for patient found message
            patient_found = await self.page.locator("div.gwt-HTML:text('A patient that matches your search criteria was found:')").wait_for(state="visible", timeout=5000)
            print("✓ Patient found - clicking Access Studies button...")
            await self.page.locator("button.gwt-Button.accessButton").click()
            print("✓ QScan patient studies accessed")
        except Exception:
            try:
                # Check for no patient found message
                no_patient_message = await self.page.locator("div.gwt-HTML:text('No patient that matches your search criteria was found.')").wait_for(state="visible", timeout=5000)
                print("✓ No matching patient found - QScan search complete")
            except Exception:
                print("QScan patient results may be available - pausing for interaction")
        

async def QScan_process(patient: PatientDetails, shared_state: SharedState):
    """Main entry point for QScan provider"""
    # Create and run session
    session = QScanSession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
