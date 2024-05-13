import json
import aioconsole
import argparse
import time
import asyncio
import re
import queue

import threading

from playwright.sync_api import Playwright, sync_playwright, expect
from datetime import datetime
from playwright.async_api import async_playwright
from pynput import keyboard
from aioconsole import ainput

from utils import *





async def run_SNP_process(patient, shared_state):
    async with async_playwright() as playwright:
        # Load credentials for the SNP process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(shared_state, "Sonic")

        # Print the status and loaded credentials
        print(f"Starting SNP process")
        #print(f"Credentials loaded are: {credentials}")

        # Extract username and password from credentials
        username = credentials["user_name"]
        password = credentials["user_password"]
        #print(f"Credentials are {username} and {password}")
        
        # Print patient details
        #print(f"Patient details are: {patient}")

        # Launch the browser and open a new page
        browser = await playwright.firefox.launch(headless=False)
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
        await page.locator("#familyName").fill(patient["family_name"])
        await page.locator("#familyName").press("Tab")
        #<input _ngcontent-ng-c2346702383="" type="text" id="familyName" placeholder="" name="Surname" class="form-control ng-valid ng-dirty ng-touched">
        await page.locator("#givenName").fill(patient["given_name"])
        #<input _ngcontent-ng-c2346702383="" type="text" id="givenName" placeholder="" name="GivenName" class="form-control ng-pristine ng-valid ng-touched">
        await page.locator("#givenName").press("Tab")
        await page.get_by_label("Sex").press("Tab")
        
        # Convert the patient's date of birth to the required format
        converted_dob = convert_date_format(patient['dob'], "%d%m%Y", "%d/%m/%Y")
        #print(f'Converted DOB:{converted_dob}')

        # Fill in the date of birth field
        await page.get_by_placeholder("DD/MM/YYYY").fill(converted_dob)

        # Initiate the search process on the page
        await page.get_by_role("button", name="Search").click()

        print("Sonic paused for interaction")

        while not shared_state.get("exit", False):
            await asyncio.sleep(0.1)          
        
        print("Sonic received exit instruction")
 
        # Close the browser context and the browser
        await context.close()
        await browser.close()


