### This is mater converted for 4cyte
    

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


async def run_fourcyte_process(patient, shared_state):
    async with async_playwright() as playwright:
        # Load credentials for the Medway process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(shared_state, "4cyte")

        # Print the status and loaded credentials
        print(f"Starting 4cyte process")
        #print(f"Credentials loaded are: {credentials}")

        # Extract username and password from credentials
        username = credentials["user_name"]
        password = credentials["user_password"]
        two_fa_secret = credentials["totp_secret"]
        print(f"Credentials are {username} and {password} and {two_fa_secret}")
        
        # Print patient details
        #print(f"Patient details are: {patient}")

        # Launch the browser and open a new page
        browser = await playwright.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the 4cyte login page
        await page.goto("https://www.4cyte.com.au/clinicians")
        await page.get_by_role("link", name="Web Results Portal").click()

        #print("Waiting for popup")

        async with page.expect_popup() as page1_info:
            await page.get_by_label("Access results portal").click()
            page1 = await page1_info.value

       
            await page1.get_by_placeholder("Username").click()
            await page1.get_by_placeholder("Username").fill(username)
            await page1.get_by_placeholder("Password").click()
            await page1.get_by_placeholder("Password").fill(password)
            await page1.get_by_role("button", name="Log in").click()

            #handle 2FA


            #print("Please enter 2FA for 4Cyte (Authenticator App) starting with F\n")
            #while not shared_state["4Cyte_code"]:
            #
            #   await asyncio.sleep(1)  # Check for the 2FA code every second

            # Once the 2FA code is available, use it
            #two_fa_code = shared_state["4Cyte_code"]
            #shared_state["4Cyte_code"]=None

            # get 2FA code from PYOP
            two_fa_code = generate_2fa_code(two_fa_secret)
            print(f"Generated 2FA code: {two_fa_code}")


            #wait for PIN page to load

            #print ("await page.wait_for_load_state")
            await page.wait_for_load_state("networkidle")

            await page1.get_by_placeholder("-digit code").click()
            
            await page1.get_by_placeholder("-digit code").fill(two_fa_code)
            await page1.get_by_role("button", name="Submit").click()
            
            








            
            











            await page1.get_by_role("button", name="Patients").click()
            #print('Trying to click Break Glass')
            await page1.get_by_role("link", name=" Break Glass").click()



            # Convert the patient's date of birth to the required format
            converted_dob = convert_date_format(patient['dob'], "%d%m%Y", "%d/%m/%Y")
            #print(f'Converted DOB: {converted_dob}')



            # Fill in patient details in the web form

            await page1.get_by_role("button", name="Accept").click()
            await page1.get_by_placeholder("Surname [space] First name").fill(f'{patient["family_name"]} {patient["given_name"]}')  #surname space firstname
            await page1.get_by_placeholder("Birth Date (Required)").click()
            await page1.get_by_placeholder("Birth Date (Required)").fill(converted_dob)
            await page1.get_by_role("button", name="Search").click()
            



            print("4cyte Pathology paused for interaction")

            while not shared_state.get("exit", False):
                await asyncio.sleep(0.1)   
            print("4cyte received exit signal")
    
            # Close the browser context and the browser
            await context.close()
            await browser.close()



