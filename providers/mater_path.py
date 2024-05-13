
### This is medway converted for mater pathology
    

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


async def run_mater_path_process(patient, shared_state):
    async with async_playwright() as playwright:
        # Load credentials for the Medway process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(shared_state, "MaterPath")

        # Print the status and loaded credentials
        print(f"Starting Mater Pathology process")
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

        # Navigate to the Medway login page
        await page.goto("https://laboratoryresults.mater.org.au/cis/cis.dll")







        # Fill in the login form using the loaded credentials
        
        await page.locator("input[name=\"salamiloginlogin\"]").click()
        await page.locator("input[name=\"salamiloginlogin\"]").fill(username)

        #await page.get_by_placeholder("e.g. name@domain.com").fill(username)

        await page.locator("input[name=\"salamiloginpassword\"]").click()
        await page.locator("input[name=\"salamiloginpassword\"]").fill(password)
        await page.get_by_role("button", name="Login").click()



        #await page.get_by_placeholder("Password").click()
        #await page.get_by_placeholder("Password").fill(password)
        #await page.get_by_role("button", name="Log in").click()

        # Wait for the network activity to idle before proceeding
        await page.wait_for_load_state("networkidle")

        # Fill in patient details in the web form
        await page.get_by_role("cell", name="Welcome to the Mater").get_by_role("link").nth(1).click()
        await page.locator("input[name=\"surname\"]").click()
        await page.locator("input[name=\"surname\"]").fill(patient["family_name"])
        await page.locator("input[name=\"firstname\"]").click()
        await page.locator("input[name=\"firstname\"]").fill(patient["given_name"])

        # Convert the patient's date of birth to the required format
        converted_dob = convert_date_format(patient['dob'], "%d%m%Y", "%d/%m/%Y")
        print(f'Converted DOB: {converted_dob}')

        # Fill in the date of birth field
        
        await page.locator("input[name=\"dob\"]").click()
        await page.locator("input[name=\"dob\"]").fill(converted_dob)
        
        #click search
        await page.get_by_role("button", name="Search").click()


        print("Mater Pathology paused for interaction")

        while not shared_state.get("exit", False):
            await asyncio.sleep(0.1)   
        print("Medway received exit signal")
  
        # Close the browser context and the browser
        await context.close()
        await browser.close()





        '''
    page.locator("input[name=\"salamiloginlogin\"]").click()
    
    page.locator("input[name=\"salamiloginlogin\"]").press("Tab")
    
    
    

    # ---------------------
    context.close()
    browser.close()
'''

