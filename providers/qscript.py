

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


async def run_QScript_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials first before starting browser
    credentials = load_credentials(shared_state, "QScript")
    if not credentials:
        print("Failed to load QScript credentials")
        return

    async with async_playwright() as playwright:        

        # Print the status and loaded credentials
        print(f"Starting QScript process")
        #print(f"Credentials loaded are: {credentials}")

        # Extract username and password from credentials
        username = credentials.user_name
        password = credentials.user_password
        pin = credentials.PIN
        #print(f"Credentials are {username}, {password}, and {pin}")
        
        # Print patient details
        print(f"QS Patient details are: {patient}")
    
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://hp.qscript.health.qld.gov.au/home")
        await page.wait_for_load_state("networkidle")

        

        # username entry
        await page.get_by_placeholder("Enter username").click()
        await page.get_by_placeholder("Enter username").fill(username)
        await page.get_by_label("Next").click()

        #now, if I haven't logged in recently, I will be asked for a password and then 2FA. Then I have to enter a PIN to use for the rest of the day

        await page.wait_for_load_state("networkidle")
        await page.get_by_placeholder("Enter password").click()
        await page.get_by_placeholder("Enter password").fill(password)
        await page.wait_for_load_state("networkidle")
        await page.get_by_label("Log In").click()

        # Handle 2FA asynchronously
        #two_fa_code = await ainput("Enter 2FA code for QScript: ")
        #await page.get_by_placeholder("Verification code").fill(two_fa_code)
        #await page.get_by_role("button", name="Verify").click()



        # Wait for the 2FA code to be entered from the Queue
        print("Please enter 2FA for QScript starting with a Q.\nmsverify: Use verification code ###### for QScript authentication.\n")
        while not shared_state.QScript_code:
            await asyncio.sleep(1)  # Check for the 2FA code every second

        # Once the 2FA code is available, use it
        two_fa_code = shared_state.QScript_code
        shared_state.QScript_code = None
        await page.get_by_placeholder("Verification code").fill(two_fa_code)
        await page.get_by_role("button", name="Verify").click()


        # Handle 2FA - this failed once we went asynchronous
        #two_fa_code = input("Enter 2FA code for QScript: ")
        #await page.get_by_placeholder("Verification code").fill(two_fa_code)
        #await page.get_by_role("button", name="Verify").click()
        

        #wait for PIN page to load

        #print ("await page.wait_for_load_state")
        await page.wait_for_load_state("networkidle")
        #print("Sleep for 10 seconds")
        #await asyncio.sleep(10)
    
        # Pause for manual interaction
        
        #here we have code to put in the PIN the first time if I haven't logged into QScript yet today. This doesn't work properly.
        #THIS SECTION DOESN'T WORK FOR THE PIN
        # await page.wait_for_load_state("networkidle")
        #old process
        #await page.wait_for_selector("#pinCreate")
        #print("found #pinCreate")
        #await page.fill("#pinCreate", pin)
        
        #print("Filled pincreate")
        #await page.get_by_role("button", name="OK").click()
        #print ("awaited button click")

        await page.get_by_placeholder("Enter PIN").fill(pin)
        await page.get_by_label("Save PIN and Log In").click()

        #if I have logged in, I jsut need to enter my PIN. I need to write this because I don't know what the workflow is. It seems Playwright doesn't keep any cookies so every login is a new episode. It doesn't remember the PIN.

            
        #print("Clicking on the first name input field...")
        await page.locator("[data-test-id=\"patientSearchFirstName\"]").click()

        # Fill in patient details
        await page.locator("[data-test-id=\"patientSearchFirstName\"]").fill(patient.given_name)
        await page.locator("[data-test-id=\"patientSearchFirstName\"]").press("Tab")
        await page.locator("[data-test-id=\"patientSearchSurname\"]").fill(patient.family_name)
        await page.locator("[data-test-id=\"patientSearchSurname\"]").press("Tab")

        # Convert and fill date of birth
        converted_dob = convert_date_format(patient.dob, "%d%m%Y", "%d/%m/%Y")
        #print(f"Converted DOB: {converted_dob}")

        #print("Filling in the date of birth...")
        await page.locator("[data-test-id=\"dateOfBirth\"]").get_by_placeholder(" ").fill(converted_dob)

        #print("Clicking on the 'Search' button...")
        await page.get_by_label("Search").click()


        print("QScript paused for interaction")

        while not shared_state.exit:
            await asyncio.sleep(0.1)

        print("QScript no longer paused")



        await context.close()
        await browser.close()
