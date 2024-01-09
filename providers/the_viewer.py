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


### The viewer using a QGov login
        
async def run_QGov_Viewer_process(CREDENTIALS_FILE, patient, shared_state):
    async with async_playwright() as playwright:
        # Load credentials for the QGov process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(CREDENTIALS_FILE, "QGov")

        # Print the status and loaded credentials
        print(f"Starting QGov The Viewer process")
        #print(f"Credentials loaded are: {credentials}")

        # Extract username and password from credentials
        username = credentials["user_name"]
        password = credentials["user_password"]
        #print(f"Credentials are {username} and {password}")
        
        # Print patient details
        #print(f"Patient details are: {patient}")

        # Launch the browser and open a new page
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        
      
        # Navigate to the HPP login page
        await page.goto("https://hpp.health.qld.gov.au/")



        # Wait for the network activity to idle before proceeding
        await page.wait_for_load_state("networkidle")

        # Fill in the login form using the loaded credentials


        # Wait for the network activity to idle before proceeding
        await page.wait_for_load_state("networkidle")

        await page.get_by_role("link", name="Login with QGov").click()
        await page.get_by_placeholder("Your email address").click()
        await page.get_by_placeholder("Your email address").fill(username)
        await page.get_by_label("Password").click()
        await page.get_by_label("Password").fill(password)
        await page.get_by_role("button", name="Log in").click()

        

        # Wait for the network activity to idle before proceeding
        await page.wait_for_load_state("networkidle")

        # Fill in patient details in the web form

        await page.locator("#MedicareNumber").click()
        await page.locator("#MedicareNumber").fill(patient["medicare_number"])
                                                   
        #change gender into the correct format  M="1", F="2", Indeterminate = "3"
        gender = convert_gender(patient["sex"],"M1F2I3")
        #print (f'Gender: {gender}')
        await page.get_by_label("Sex").select_option(gender)
        
        #

        # Convert the patient's date of birth to the required format
        converted_dob = convert_date_format(patient['dob'], "%d%m%Y", "%d/%m/%Y")
        #print(converted_dob)

        # Fill in the date of birth field
        await page.get_by_placeholder("DD/MM/YYYY").click()
        await page.get_by_placeholder("DD/MM/YYYY").fill(converted_dob)
        await page.get_by_placeholder("DD/MM/YYYY").press("Tab")

        await page.get_by_label("Patient Surname").fill(patient["family_name"])
        await page.get_by_role("button", name="Search").click()


        # Function to handle popup interaction
        async def handle_popup(popup):
            await popup.wait_for_load_state()
            # Perform necessary actions on the popup
            # ...

        # Set up event listener for popup
        print("Waiting for popup")
        page.on("popup", handle_popup)

        # Trigger action that causes the popup
        print("Clicking on the Viewer")
        await page.get_by_role("link", name="The Viewer").click()

        # Here, handle_popup will be called when the popup opens

        # Wait until you're done with the popup
        # This could be a flag in shared_state that is set inside handle_popup
        #while not shared_state.get("popup_done", False):
        #    await asyncio.sleep(1)




        # Initiate the search process on the page
        #await page.get_by_role("button", name="Search").click()

        print("QGov The Viewer paused for interaction")

        while not shared_state.get("exit", False):
            await asyncio.sleep(0.1)    

        print("QGov The Viewer received exit instruction")
  
        # Close the browser context and the browser
        await context.close()
        await browser.close()


