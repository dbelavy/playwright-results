### This is 4Cyte adapted for meditrust
    

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


async def run_meditrust_process(patient, shared_state):
    async with async_playwright() as playwright:
        # Load credentials for the process
        # Assuming load_credentials is a synchronous function, no await is needed
        credentials = load_credentials(shared_state, "Meditrust")

        # Print the status and loaded credentials
        print(f"Starting Meditrust process")
        #print(f"Credentials loaded are: {credentials}")

        # Extract username and password from credentials
        username = credentials["user_name"]
        password = credentials["user_password"]
        two_fa_secret = credentials["totp_secret"]
        print(f"Credentials are loaded for {username}") # and {password} and {two_fa_secret}")
        
        
        # Launch the browser and open a new page
        browser = await playwright.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the Meditrust login page
        await page.goto("https://www.meditrust.com.au/mtv4/home")
        await page.get_by_role("link", name=" Login").click()

        await page.get_by_label("Username:").click()
        await page.get_by_label("Username:").fill(username)
        await page.get_by_label("Password:").click()
        await page.get_by_label("Password:").fill(password)
        await page.get_by_role("button", name="Login").click()
        await page.get_by_placeholder("Authentication Code").click()
        #handle 2FA
        two_fa_code = generate_2fa_code(two_fa_secret)
        # print(f"Generated 2FA code: {two_fa_code}")
        await page.get_by_placeholder("Authentication Code").fill(two_fa_code)

        await page.get_by_role("button", name="Submit").click()
     
        print("Meditrust paused for interaction")

        while not shared_state.get("exit", False):
            await asyncio.sleep(0.1)   
        print("Meditrust received exit signal")

        # Close the browser context and the browser
        await context.close()
        await browser.close()
