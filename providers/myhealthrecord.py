

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






async def run_myHealthRecord_process(patient_details, shared_state):
    async with async_playwright() as playwright:        
        # Load credentials for the myHR process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(shared_state, "PRODA")

        # Print the status and loaded credentials
        print(f"Starting myHealthRecord process")
        #print(f"Credentials loaded are: {credentials}")

        # Extract username and password from credentials
        username = credentials["user_name"]
        password = credentials["user_password"]
        PRODA_full_name = credentials["PRODA_full_name"]

    
        #print(f"Credentials are {username}, {password}")
        
        # Print patient details
        # print(f"Patient details are: {patient_details}")
    
        browser = await playwright.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        #print(f"MyHR Loading login pages")

        '''
        await page.goto("https://www.servicesaustralia.gov.au/proda-provider-digital-access")
        
        await page.get_by_role("button", name="PRODA \" / \"").click()
        await page.get_by_role("menuitem", name="PRODA Log in to access HPOS,").click()
        await page.get_by_role("link", name="Sign in").click()
        '''
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
        
        # print("MyHR Waiting for network idle")
        # await page.wait_for_load_state("networkidle")

        print("MyHR waiting for click the 2FA \"Next\" button")
        await asyncio.sleep(0.2)
        # the "next" click doesn't seem to progress the page reliably. Trying a Keyboard "Enter below"
        #await page.get_by_role("button", name="Next").click()
        await page.keyboard.press('Enter')

        print("Clicking through to my health record")

        await page.get_by_role("link", name="My Health Record").click()

        #trying this to get in - having errors
        await page.wait_for_load_state("networkidle")

        await page.click(f'input[name="radio1"][value="{PRODA_full_name}"]')
        #next one stopped working
        #await page.get_by_text(PRODA_full_name, exact=True).click()

        await page.wait_for_selector('input#submitValue', state='visible')

        print("Waiting for network idle before clicking next")
        await page.wait_for_load_state("networkidle")


        await page.click('input#submitValue')
        #await page.wait_for_selector('input#submitValue', state='visible')
        #await page.click('input#submitValue')

        #Had lots of problems with failures so added a pause between pages. This seems to have helped.
        await asyncio.sleep(5)


        print("Waiting for network idle")
        await page.wait_for_load_state("networkidle")
        


        print("Filling in patient details")

        print(f"Filling in the patient's family name")
        
        #await page.get_by_role("textbox", name="Please fill out the field.").click()
        #await page.get_by_role("textbox", name="Please fill out the field.").fill(patient_details['family_name'])
        #await page.get_by_role("textbox", name="Please fill out the field.").press("Tab")
        #this one didn't work reliably.

        #this next bit didn't work at all.
        #await page.query_selector("#lname").click()
        #await page.query_selector("#lname").fill(patient_details['family_name'])
        #await page.query_selector("#lname").press("Tab")

        #this works pretty well the first time I tried it.
        element_handle = await page.query_selector("#lname")
        await element_handle.click()
        await element_handle.fill(patient_details['family_name'])
        await element_handle.press("Tab")



     

        #change date to DD/MM/YYYY
        print("Converting the date of birth format...")
        converted_dob = convert_date_format(patient_details['dob'], "%d%m%Y", "%d/%m/%Y")
        print(f"Converted DOB: {converted_dob}")


        print("Filling in DOB")
        await page.get_by_placeholder("DD-Mmm-YYYY").fill(converted_dob)

        print("having a crack at the gender options")
        if patient_details['sex'] == "M":
            await page.get_by_label("Male", exact=True).check()
        elif patient_details['sex'] == "F":
            await page.get_by_label("Female").check()
        elif patient_details['sex'] == "I":
            await page.get_by_label("Intersex").check()
        else:
            await page.get_by_label("Not Stated").check()
        
        print("Trying medicare details")
        await page.get_by_label("Medicare").check()
        await page.get_by_placeholder("Medicare number with IRN").click()
        await page.get_by_placeholder("Medicare number with IRN").fill(patient_details["medicare_number"])
        await page.get_by_role("button", name="Search").click()




        print("My Health Record paused for interaction")

        while not shared_state.get("exit", False):
            await asyncio.sleep(0.1)

        print("My Health Record received exit signal")



        await context.close()
        await browser.close()









