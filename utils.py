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




async def process_inputs(input_queue, shared_state):
    while True:
        if not input_queue.empty():
            user_input = input_queue.get()
            
            # Check for a code in the format Q###### or M######
            match = re.match(r"^(Q|P|F)(\d{6})$", user_input, re.IGNORECASE)
            if match:
                code_type = match.group(1).upper()  # Q or M or F
                code_number = match.group(2)  # 6-digit number
                if code_type == 'Q':
                    print(f"Received 2FA code for QScript: {code_number}")
                    shared_state["QScript_code"] = code_number
                elif code_type == 'P':
                    print(f"Received 2FA code for PRODA: {code_number}")
                    shared_state["PRODA_code"] = code_number
                elif code_type == 'F':
                    print(f"Received 2FA code for 4Cyte: {code_number}")
                    shared_state["4Cyte_code"] = code_number
            
            # Check for 'x' to quit
            elif user_input.lower() == 'x':
                print("Received Quitting instruction...")
                shared_state["exit"] = True
                break

        await asyncio.sleep(0.1)

def input_thread(input_queue):
    while True:
        try:
            user_input = input("Enter command: ")
            input_queue.put(user_input)
            if user_input.lower() == 'x':
                break
        except EOFError:
            print("EOF encountered in input stream.")
            break

        



# Function to load credentials from a JSON file
def load_credentials(shared_state, company):
    try:
        # Open and read the JSON file
        file_path = shared_state["credentials_file"]
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Check if the company's credentials are in the file
        if company not in data:
            print(f"Error: Credentials for {company} not found in the file.")
            return None

    # Handle specific errors related to file operations and JSON parsing
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} could not be decoded.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred loading the credential file: {e}")
        return None
    else:
        # If no errors, return the credentials
        #print('Credentials loaded for:', company, 'which are:', data[company])
        return data[company]


def convert_gender(input_gender, output_format_required):
    # Define a mapping based on the output format string "M1F2I3"
    if output_format_required == "M1F2I3":
        gender_mapping = {
            "M": "1",
            "F": "2",
            "I": "3"
        }
    
    return gender_mapping.get(input_gender, None)


# Function to convert a date string from one format to another
def convert_date_format(date_string, input_format, output_format):
    """
    [Function documentation]
    """
    try:
        # Convert the input string to a datetime object
        date_obj = datetime.strptime(date_string, input_format)
        
        # Format the datetime object to the desired output format
        return date_obj.strftime(output_format)
    except ValueError:
        print("Invalid date format.")
        return None


