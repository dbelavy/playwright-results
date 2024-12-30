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


async def run_SNP_process(patient: PatientDetails, shared_state: SharedState):
    # Load credentials first before starting browser
    credentials = load_credentials(shared_state, "Sonic")
    if not credentials:
        print("Failed to load Sonic credentials")
        return

    async with async_playwright() as playwright:
        # Print the status and loaded credentials
        print(f"Starting SNP process")

        # Extract username and password from credentials
        username = credentials.user_name
        password = credentials.user_password
        #print(f"Credentials are {username} and {password}")
        
        # Print patient details
        #print(f"Patient details are: {patient}")

        # Launch the browser and open a new page
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the SNP login page
        
        await page.goto("https://www.sonicdx.com.au/#/login")

        # Wait for the network activity to idle before proceeding
        await page.wait_for_load_state("networkidle")

        # Fill in the login form using the loaded credentials
        await page.locator("#username").click()
        await page.locator("#username").fill(username)
        #This is the Selector for Sullivan Nicholaides from Sonic
        await page.locator("#selected-business").select_option("SNP")
        await page.locator("#password").click()
        await page.locator("#password").fill(password)
        #await page.locator("div").filter(has_text=re.compile(r"^Login$")).click()
        await page.get_by_role("button", name="Login").click()



        # Wait for the network activity to idle before proceeding
        await page.wait_for_load_state("networkidle")

        # Fill in patient details in the web form

        await page.get_by_role("link", name="Search", exact=True).click()
        await page.locator("#familyName").click()
        await page.locator("#familyName").fill(patient.family_name)
        await page.locator("#familyName").press("Tab")
        await page.locator("#givenName").fill(patient.given_name)
        await page.locator("#givenName").press("Tab")
        await page.get_by_label("Sex").press("Tab")
        
        # Convert the patient's date of birth to the required format
        converted_dob = convert_date_format(patient.dob, "%d%m%Y", "%d/%m/%Y")
        #print(f'Converted DOB:{converted_dob}')

        # Fill in the date of birth field
        await page.get_by_placeholder("DD/MM/YYYY").fill(converted_dob)

        # Initiate the search process on the page
        await page.get_by_role("button", name="Search").click()

        print("Sonic paused for interaction")

        while not shared_state.exit:
            await asyncio.sleep(0.1)          
        
        print("Sonic received exit instruction")
 
        # Close the browser context and the browser
        await context.close()
        await browser.close()
