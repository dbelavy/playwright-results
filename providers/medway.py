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


async def run_medway_process(patient, shared_state):
    async with async_playwright() as playwright:
        # Load credentials for the Medway process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(shared_state, "Medway")

        # Print the status and loaded credentials
        print(f"Starting Medway process")
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
        await page.goto("https://www.medway.com.au/login")

        # Fill in the login form using the loaded credentials
        await page.get_by_placeholder("e.g. name@domain.com").click()
        await page.get_by_placeholder("e.g. name@domain.com").fill(username)
        await page.get_by_placeholder("Password").click()
        await page.get_by_placeholder("Password").fill(password)
        await page.get_by_role("button", name="Log in").click()

        # Wait for the network activity to idle before proceeding
        await page.wait_for_load_state("networkidle")

        # Fill in patient details in the web form
        await page.get_by_label("Patient surname").click()
        await page.get_by_label("Patient surname").fill(patient["family_name"])
        await page.get_by_label("Patient surname").press("Tab")
        await page.get_by_label("Patient given name(s)").click()
        await page.get_by_label("Patient given name(s)").fill(patient["given_name"])
        await page.get_by_label("Patient given name(s)").press("Tab")

        if patient['medicare_number'] != None:
            medicare_field = page.get_by_placeholder("digit Medicare number")
            await medicare_field.fill(patient['medicare_number'][:10])
            await medicare_field.press("Tab")  # Move to the next field

        # Convert the patient's date of birth to the required format
        converted_dob = convert_date_format(patient['dob'], "%d%m%Y", "%Y-%m-%d")
        #print(converted_dob)

        # Fill in the date of birth field
        dob_field = page.get_by_role("textbox", name="Date of birth")
        await dob_field.fill(converted_dob)

        # Initiate the search process on the page
        await page.get_by_role("button", name="Search").click()

        print("Medway paused for interaction")

        while not shared_state.get("exit", False):
            await asyncio.sleep(0.1)   
        print("Medway received exit signal")
  
        # Close the browser context and the browser
        await context.close()
        await browser.close()
