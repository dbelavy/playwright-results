import asyncio
from typing import Optional

from playwright.async_api import Page, Playwright, async_playwright

from models import Credentials, PatientDetails, Session, SharedState
from utils import convert_date_format


class IMedSession(Session):
    name = "IMed"  # Make name a class attribute
    required_fields = ["family_name", "given_name", "dob"]
    provider_group = "Radiology"
    credentials_key = "IMed"

    def __init__(
        self,
        credentials: Credentials,
        patient: PatientDetails,
        shared_state: SharedState,
    ):
        super().__init__(credentials, patient, shared_state)
        self.active_page: Page | None = None  # For handling popup window

    @classmethod
    def create(
        cls, patient: PatientDetails, shared_state: SharedState
    ) -> Optional["IMedSession"]:
        """Create a new IMed session"""
        return super().create(patient, shared_state)

    async def initialize(self, playwright: Playwright) -> None:
        """Initialize browser session"""
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
        await self.active_page.locator(
            '[data-testid="SingleLineTextInputField-FormControl"][name="uid"]'
        ).fill(self.credentials.user_name)
        await self.active_page.locator(
            '[data-testid="SingleLineTextInputField-FormControl"][name="password"]'
        ).fill(self.credentials.user_password)
        await self.active_page.get_by_test_id("login-button").click()

        # Wait for the search page and check available elements
        await self.active_page.wait_for_load_state("networkidle")

        # Wait for page to be ready and verify elements
        await self.active_page.wait_for_load_state("networkidle")
        await self.active_page.evaluate(
            """() => {
            // Verify critical elements are present
            const elements = document.querySelectorAll('[data-testid]');
            return elements.length > 0;
        }"""
        )

    async def search_patient(self) -> None:
        """Handle patient search"""
        if not self.active_page:
            raise RuntimeError("Session not initialized")

        # Try alternative selectors for the patient name field
        try:
            # Try by placeholder or label if it exists
            # Use the exact field attributes we found
            await self.active_page.locator(
                '[data-testid="SingleLineTextInputField-FormControl"][name="nameOrPatientId"]'
            ).fill(f"{self.patient.given_name} {self.patient.family_name}")

            # For DOB, use the exact test ID we found
            await self.active_page.get_by_test_id(
                "DOB-input-field-form-control"
            ).click()
            await self.active_page.get_by_test_id("DOB-input-field-form-control").type(
                convert_date_format(self.patient.dob, "%d%m%Y", "%d/%m/%Y")
            )

        except Exception as e:
            print(f"Primary selector failed: {str(e)}")
            try:
                # Try by role
                await self.active_page.get_by_role("textbox", name="Patient Name").fill(
                    f"{self.patient.given_name} {self.patient.family_name}"
                )
            except Exception as e:
                print(f"Secondary selector failed: {str(e)}")
                # If all else fails, try waiting and using a more specific selector
                await self.active_page.wait_for_selector(
                    'input[type="text"][data-testid="SingleLineTextInputField-FormControl"]'
                )
                await self.active_page.locator(
                    'input[type="text"][data-testid="SingleLineTextInputField-FormControl"]'
                ).first.fill(f"{self.patient.given_name} {self.patient.family_name}")

        # Request everything available
        await self.active_page.get_by_role("button", name="Referred by me").click()
        await self.active_page.get_by_role("button", name="Referred by anyone").click()
        await self.active_page.get_by_role(
            "button", name="All listed practices"
        ).click()
        await self.active_page.get_by_role(
            "button", name="All listed practices"
        ).click()
        await self.active_page.get_by_role("button", name="Past week").click()
        await self.active_page.get_by_role("button", name="All time").click()
        await self.active_page.get_by_test_id("mobile-search").click()


async def IMed_process(patient: PatientDetails, shared_state: SharedState):
    # Create and run session
    session = IMedSession.create(patient, shared_state)
    if not session:
        return
    async with async_playwright() as playwright:
        await session.run(playwright)
