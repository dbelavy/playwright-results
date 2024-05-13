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
        #print(f"Credentials are {username} and {password}")
        
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


            print("Please enter 2FA for 4Cyte (Authenticator App) starting with F\n")
            while not shared_state["4Cyte_code"]:
            
                await asyncio.sleep(1)  # Check for the 2FA code every second

            # Once the 2FA code is available, use it
            two_fa_code = shared_state["4Cyte_code"]
            shared_state["4Cyte_code"]=None
          
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





'''from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.4cyte.com.au/clinicians")
    page.get_by_role("link", name="Web Results Portal").click()
    with page.expect_popup() as page1_info:
        page.get_by_label("Access results portal").click()
    page1 = page1_info.value
    page1.get_by_placeholder("Username").click()
    page1.get_by_placeholder("Username").fill("233309DB")
    page1.get_by_placeholder("Password").click()
    page1.get_by_placeholder("Password").fill("Xd><ysYC{?**7+io")
    page1.get_by_role("button", name="Log in").click()
    page1.get_by_placeholder("-digit code").click()
    page1.get_by_placeholder("-digit code").fill("314306")
    page1.get_by_text("No").click()
    page1.get_by_placeholder("Trusted device name (optional)").click()
    page1.get_by_placeholder("Trusted device name (optional)").fill("Mac")
    page1.get_by_role("button", name="Submit").click()
    page1.get_by_role("button", name="Patients").click()
    page1.get_by_role("link", name=" Break Glass").click()
    page1.get_by_role("button", name="Accept").click()
    page1.get_by_placeholder("Surname [space] First name").click()
    page1.get_by_placeholder("Surname [space] First name").fill("foxwell kayla")
    page1.get_by_placeholder("Birth Date (Required)").click()
    page1.get_by_placeholder("Birth Date (Required)").fill("18022006")
    page1.get_by_role("button", name="Search").click()
    page1.get_by_role("button", name="OK").click()
    page1.get_by_placeholder("Birth Date (Required)").click()
    page1.get_by_placeholder("Birth Date (Required)").click()
    page1.get_by_placeholder("Birth Date (Required)").click()
    page1.get_by_placeholder("Birth Date (Required)").fill("18022006/")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowLeft")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowRight")
    page1.get_by_placeholder("Birth Date (Required)").fill("18022006")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowLeft")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowLeft")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowLeft")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowLeft")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowLeft")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowLeft")
    page1.get_by_placeholder("Birth Date (Required)").fill("18/022006")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowRight")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowRight")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowRight")
    page1.get_by_placeholder("Birth Date (Required)").press("ArrowLeft")
    page1.get_by_placeholder("Birth Date (Required)").fill("18/02/2006")
    page1.get_by_role("button", name="Search").click()
    page1.get_by_role("cell", name="FOXWELL, Kayla Grace").click()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
'''
