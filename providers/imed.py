### This is Mater Pathology converted for Imed radiology + bits of 4Cyte
    

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


async def run_imed_process(patient, shared_state):
    async with async_playwright() as playwright:
        # Load credentials for the Medway process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(shared_state, "IMed")

        # Print the status and loaded credentials
        print(f"Starting I-Med process")
        # print(f"Credentials loaded are: {credentials}")

        # Extract username and password from credentials
        username = credentials["user_name"]
        password = credentials["user_password"]
        postcode = credentials["postcode"]
        suburb = credentials["suburb"]
        
        # print(f"Credentials are {username} and {password} + {postcode} + {suburb}")
        
        # Print patient details
        # print(f"Patient details are: {patient}")

        # Convert the patient's date of birth to the required format
        converted_dob = convert_date_format(patient['dob'], "%d%m%Y", "%d/%m/%Y")
        # print(f'Converted DOB: {converted_dob}')
        


        # Launch the browser and open a new page
        browser = await playwright.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the I-Med login page
        await page.goto("https://i-med.com.au/resources/access-patient-images")

        # Click throgut to login

        #await page.get_by_role("banner").locator("label").click()
        await page.get_by_test_id("dropdownInput").click()
        await page.get_by_test_id("dropdownInput").fill(postcode)
        await page.get_by_test_id("dropdownInput").press("Enter")
        await page.get_by_role("button", name=suburb).click()
         
        async with page.expect_popup() as page1_info:
            await page.get_by_role("button", name="ACCESS I-MED ONLINE").click()
            page1 = await page1_info.value


            await page.wait_for_load_state("networkidle")

            #await page1.locator("input[name=\"uid\"]").click()
            #await page1.locator("input[name=\"uid\"]").fill(username)
            #await page1.locator("input[name=\"password\"]").click()
            #await page1.locator("input[name=\"password\"]").fill(password)
            
            await page1.locator('[data-testid="SingleLineTextInputField-FormControl"][name="uid"]').fill(username)
            await page1.locator('[data-testid="SingleLineTextInputField-FormControl"][name="password"]').fill(password)
        
            
            await page1.get_by_test_id("login-button").click()
         
            # Wait for the search page and log what we find
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
            # print(f"Found elements: {json.dumps(elements, indent=2)}")

            # Try alternative selectors for the patient name field
            try:
                # Try by placeholder or label if it exists
                # Use the exact field attributes we found
                await page1.locator('[data-testid="SingleLineTextInputField-FormControl"][name="nameOrPatientId"]').fill(f'{patient["given_name"]} {patient["family_name"]}')
    
                # For DOB, use the exact test ID we found
                await page1.get_by_test_id("DOB-input-field-form-control").click()
                await page1.get_by_test_id("DOB-input-field-form-control").type(converted_dob)

            except:
                try:
                    # Try by role
                    await page1.get_by_role("textbox", name="Patient Name").fill(f'{patient["given_name"]} {patient["family_name"]}')
                except:
                    # If all else fails, try waiting and using a more specific selector
                    await page1.wait_for_selector('input[type="text"][data-testid="SingleLineTextInputField-FormControl"]')
                    await page1.locator('input[type="text"][data-testid="SingleLineTextInputField-FormControl"]').first.fill(
                        f'{patient["given_name"]} {patient["family_name"]}'
                    )

            # await page1.get_by_test_id("SingleLineTextInputField-FormControl").fill(f'{patient["given_name"]} {patient["family_name"]}')
            # await page1.get_by_test_id("DOB-input-field-form-control").click()
            # await page1.get_by_test_id("DOB-input-field-form-control").fill(converted_dob)



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
            # Wait for exit signal

            while not shared_state.get("exit", False):
                await asyncio.sleep(0.1)   
            print("I-Med received exit signal")
    


            # --Close up--
            await context.close()
            await browser.close()
