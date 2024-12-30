import json
import aioconsole
import argparse
import time
import asyncio
import re
import queue
import threading
from typing import Dict, Any

from playwright.sync_api import Playwright, sync_playwright, expect
from datetime import datetime
from playwright.async_api import async_playwright
from pynput import keyboard
from aioconsole import ainput

from utils import *
from models import PatientDetails


async def run_materpathnew_process(patient: PatientDetails, shared_state: Dict[str, Any]):
    async with async_playwright() as playwright:
        # Load credentials
        credentials = load_credentials(shared_state, "MaterPathNew")

        print(f"Starting MaterPathNew process")
        # print(f"Credentials loaded are: {credentials}")

        username = credentials["user_name"]
        password = credentials["user_password"]
        two_fa_secret = credentials["totp_secret"]
        # print(f"Credentials are {username} and {password} and {two_fa_secret}")
        
        # print(f"Patient details are: {patient}")

        browser = await playwright.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to login page
        await page.goto('https://pathresults.mater.org.au/')
        await page.wait_for_load_state("networkidle")

        # Click external practitioner button - fixed selector
        await page.get_by_role("button", name="I am an External Practitioner").click()
        await page.wait_for_load_state("networkidle")

        # print("Passed external practitioner")

        # Login process
        await page.get_by_label("Username").click()
        await page.get_by_label("Username").fill(username)
        await page.get_by_role("button", name="Next").click()

        # print("Passed username")

        await page.wait_for_load_state("networkidle")

        password_entered = False
        max_attempts = 5
        attempt = 0

        while not password_entered and attempt < max_attempts:
            attempt += 1
            # print(f"Password entry attempt {attempt}")
            is_password_visible = False
            try:
                await page.wait_for_selector('input[type="Password"]', state="visible", timeout=2000)
                is_password_visible = True
            except Exception as e:
                is_password_visible = False

            # print (f"Password visible: {is_password_visible}")

            # First check if password field is visible
            try:
                if is_password_visible:
                    # print(f"Password field visible, attempting direct entry - attempt {attempt}")
                    await page.get_by_label("Password").fill(password)
                    await page.get_by_role("button", name="Verify").click()
                    await page.wait_for_load_state("networkidle")
                    password_entered = True
                    continue
            except Exception as e:
                print(f"Password field not immediately visible: {e}")

            # If no password field, try the "Verify with something else" path - this may not be necessary - haven't tested this code
            try:
                print(f"Trying 'Verify with something else' path - attempt {attempt}")
                verify_button = await page.wait_for_selector('a:text("Verify with something else")', timeout=2000)
                if verify_button:
                    await verify_button.click()
                    await page.wait_for_load_state("networkidle")
                    
                    # Wait for and click the Password option
                    await page.get_by_label("Select Password.").click()
                    await page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"Could not find 'Verify with something else': {e}")

        if not password_entered:
            print("Failed to enter password after maximum attempts")
            return False

        print("Proceeding to next step...")

        # Check if we need to select OTP method
        try:
            # Look for the Google Authenticator selection button
            authenticator_selector = 'a[aria-label="Select Google Authenticator"]'
            await page.wait_for_selector(authenticator_selector, timeout=2000)
            await page.locator(authenticator_selector).click()
        except Exception as e:
            print(f"Direct OTP entry available: {e}")

        # Handle OTP entry
        try:
            two_fa_code = generate_2fa_code(two_fa_secret)
            print(f"Generated 2FA code: {two_fa_code}")
            
            await page.get_by_label("Enter code").click()
            await page.get_by_label("Enter code").fill(two_fa_code)
            await page.get_by_role("button", name="Verify").click()
            await page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"Error during OTP entry: {e}")

        print("Passed 2FA")

        # Patient search
        await page.get_by_placeholder("Surname").click()
        await page.get_by_placeholder("Surname").fill(patient.family_name)

        await page.get_by_placeholder("First Name").click()
        await page.get_by_placeholder("First Name").fill(patient.given_name)

        converted_dob = convert_date_format(patient.dob, "%d%m%Y", "%Y-%m-%d")
        await page.get_by_placeholder("Date of Birth").fill(converted_dob)

        await page.get_by_role("button", name="Search").click()

        print("Mater Path New paused for interaction")

        while not shared_state.get("exit", False):
            await asyncio.sleep(0.1)   
        print("Mater Path New received exit signal")

        # Cleanup
        await context.close()
        await browser.close()
