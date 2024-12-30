
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


async def run_myHealthRecord_process(patient: PatientDetails, shared_state: Dict[str, Any]):
    async with async_playwright() as playwright:        
        # Load credentials for the myHR process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(shared_state, "PRODA")

        print(f"Starting myHealthRecord process")

        # Extract credentials
        username = credentials["user_name"]
        password = credentials["user_password"]
        PRODA_full_name = credentials["PRODA_full_name"]

        browser = await playwright.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to login page
        await page.goto("https://proda.humanservices.gov.au/prodalogin/pages/public/login.jsf?TAM_OP=login&USER")
        
        await page.wait_for_load_state("networkidle")
        await page.get_by_label("Username").click()
        await page.get_by_label("Username").fill(username)
        await page.get_by_label("Password", exact=True).click()
        await page.get_by_label("Password", exact=True).fill(password)
        await page.get_by_role("button", name="Login", exact=True).click()

    
        
        await page.wait_for_load_state("networkidle")

        
        # Handle 2FA asynchronously
        
        # Wait for the 2FA code to be entered from the Queue
        print("Please enter 2FA for PRODA starting with a P. eg P123456 \n")
        while not shared_state["PRODA_code"]:
            
            await asyncio.sleep(1)  # Check for the 2FA code every second

        # Once the 2FA code is available, use it
        two_fa_code = shared_state["PRODA_code"]
        shared_state["PRODA_code"]=None
        

        await page.get_by_label("Enter Code").click()
        await page.get_by_label("Enter Code").fill(two_fa_code)
        print("MyHR waiting for click the 2FA \"Next\" button")
        await asyncio.sleep(0.2)
        # Using keyboard Enter as it's more reliable than clicking Next
        await page.keyboard.press('Enter')

        print("Clicking through to my health record")
        await page.get_by_role("link", name="My Health Record").click()
        await page.wait_for_load_state("networkidle")

        await page.click(f'input[name="radio1"][value="{PRODA_full_name}"]')
        # next one stopped working
        # await page.get_by_text(PRODA_full_name, exact=True).click()


        await page.wait_for_selector('input#submitValue', state='visible')
        await page.wait_for_load_state("networkidle")
        await page.click('input#submitValue')

        # Added pause between pages to prevent failures
        await asyncio.sleep(5)
        await page.wait_for_load_state("networkidle")

        print("Filling in patient details")
        
        # Fill in family name - using query selector as it's most reliable
        element_handle = await page.query_selector("#lname")
        await element_handle.click()
        await element_handle.fill(patient.family_name)
        await element_handle.press("Tab")

        # Convert and fill date of birth
        converted_dob = convert_date_format(patient.dob, "%d%m%Y", "%d/%m/%Y")
        await page.get_by_placeholder("DD-Mmm-YYYY").fill(converted_dob)

        # Handle gender selection
        if patient.sex == "M":
            await page.get_by_label("Male", exact=True).check()
        elif patient.sex == "F":
            await page.get_by_label("Female").check()
        elif patient.sex == "I":
            await page.get_by_label("Intersex").check()
        else:
            await page.get_by_label("Not Stated").check()
        
        # Fill in Medicare details
        await page.get_by_label("Medicare").check()
        await page.get_by_placeholder("Medicare number with IRN").click()
        await page.get_by_placeholder("Medicare number with IRN").fill(patient.medicare_number)
        await page.get_by_role("button", name="Search").click()
        print("My Health Record paused for interaction")

        while not shared_state.get("exit", False):
            await asyncio.sleep(0.1)

        print("My Health Record received exit signal")

        await context.close()
        await browser.close()
