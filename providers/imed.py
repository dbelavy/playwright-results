import json
import aioconsole
import argparse
import time
import asyncio
import re
import queue
import threading
from playwright.sync_api import Playwright, sync_playwright, expect
from models import PatientDetails, SharedState
from datetime import datetime
from playwright.async_api import async_playwright
from pynput import keyboard
from aioconsole import ainput

from utils import load_credentials, convert_date_format


async def run_imed_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials first before starting browser
    credentials = load_credentials(shared_state, "IMed")
    if not credentials:
        print("Failed to load I-Med credentials")
        return

    async with async_playwright() as playwright:
        print(f"Starting I-Med process")

        # Extract credentials
        username = credentials.user_name
        password = credentials.user_password
        postcode = credentials.postcode
        suburb = credentials.suburb

        # Convert date of birth to required format
        converted_dob = convert_date_format(patient.dob, "%d%m%Y", "%d/%m/%Y")

        # Launch the browser and open a new page
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the I-Med login page
        await page.goto("https://i-med.com.au/resources/access-patient-images")

        # Click through to login
        await page.get_by_test_id("dropdownInput").click()
        await page.get_by_test_id("dropdownInput").fill(postcode)
        await page.get_by_test_id("dropdownInput").press("Enter")
        await page.get_by_role("button", name=suburb).click()
         
        async with page.expect_popup() as page1_info:
            await page.get_by_role("button", name="ACCESS I-MED ONLINE").click()
            page1 = await page1_info.value

            await page.wait_for_load_state("networkidle")
            
            # Fill in login credentials using data-testid selectors
            await page1.locator('[data-testid="SingleLineTextInputField-FormControl"][name="uid"]').fill(username)
            await page1.locator('[data-testid="SingleLineTextInputField-FormControl"][name="password"]').fill(password)
            await page1.get_by_test_id("login-button").click()
         
            # Wait for the search page and check available elements
            await page1.wait_for_load_state("networkidle")
            
            print("After login - checking available elements...")
            elements = await page1.evaluate("""() => {
                const elements = document.querySelectorAll('[data-testid]');
                return Array.from(elements).map(el => ({
                    testId: el.getAttribute('data-testid'),
                    type: el.getAttribute('type'),
                    name: el.getAttribute('name')
                }));
            }""")

            # Try alternative selectors for the patient name field
            try:
                # Try by placeholder or label if it exists
                # Use the exact field attributes we found
                await page1.locator('[data-testid="SingleLineTextInputField-FormControl"][name="nameOrPatientId"]').fill(f'{patient.given_name} {patient.family_name}')
    
                # For DOB, use the exact test ID we found
                await page1.get_by_test_id("DOB-input-field-form-control").click()
                await page1.get_by_test_id("DOB-input-field-form-control").type(converted_dob)

            except:
                try:
                    # Try by role
                    await page1.get_by_role("textbox", name="Patient Name").fill(f'{patient.given_name} {patient.family_name}')
                except:
                    # If all else fails, try waiting and using a more specific selector
                    await page1.wait_for_selector('input[type="text"][data-testid="SingleLineTextInputField-FormControl"]')
                    await page1.locator('input[type="text"][data-testid="SingleLineTextInputField-FormControl"]').first.fill(
                        f'{patient.given_name} {patient.family_name}'
                    )

            await page.wait_for_load_state("networkidle")

            # Request everything available
            await page1.get_by_role("button", name="Referred by me").click()
            await page1.get_by_role("button", name="Referred by anyone").click()
            await page1.get_by_role("button", name="All listed practices").click()
            await page1.get_by_role("button", name="All listed practices").click()
            await page1.get_by_role("button", name="Past week").click()
            await page1.get_by_role("button", name="All time").click()
            await page1.get_by_test_id("mobile-search").click()

            print("I-Med Radiology paused for interaction")

            while not shared_state.exit:
                await asyncio.sleep(0.1)   
            print("I-Med received exit signal")

            # Close the browser context and the browser
            await context.close()
            await browser.close()
