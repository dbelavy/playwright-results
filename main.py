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


from providers.medway import *
from providers.the_viewer import *
from providers.qscript import *
from providers.snp_sonic import *
from utils import *









async def main():
    # Set up command line arguments for the script
    parser = argparse.ArgumentParser(description="Run Playwright script with user data")
    parser.add_argument("--family_name", help="Family Name", required=False)
    parser.add_argument("--given_name", help="Given Name", required=False)
    parser.add_argument("--dob", help="Date of Birth (DDMMYYYY)", required=False)
    parser.add_argument("--medicare_number", help="Medicare Number (optional)", required=False)
    parser.add_argument("--sex", help="Sex (M, F, or I)", required=False)
    args = parser.parse_args()

    # Initialize the patient_details dictionary
    patient_details = {
        'family_name': args.family_name if args.family_name else input("Enter Family Name: "),
        'given_name': args.given_name if args.given_name else input("Enter Given Name: "),
        'dob': args.dob if args.dob else input("Enter DOB (DDMMYYYY): "),
        'medicare_number': str(args.medicare_number) if args.medicare_number else str(input("Enter Medicare Number (if applicable): ")),
        'sex': args.sex.upper() if args.sex else input("Enter Sex (M, F, or I), or press 'Enter' to skip: ").upper()
    }

    # Ensure valid sex input
    while not patient_details['sex'] in ["M", "F", "I", ""]:
        print("Invalid input. Please enter 'M', 'F', 'I', or press 'Enter' to skip.")
        patient_details['sex'] = input("Enter Sex (M, F, or I), or press 'Enter' to skip: ").upper()

    print(f"Patient Details Collected: {patient_details}")

    # Define the path to the credentials file
    CREDENTIALS_FILE = "credentials.json"
    
    # Map numbers to task functions
    task_functions = {
        1: run_medway_process,
        2: run_SNP_process,
        3: run_QScript_process,
        4: run_QGov_Viewer_process  # Assuming this is another task function
    }

    # Display the task options
    print("Select tasks to run (separate by commas):")
    for number, task in task_functions.items():
        print(f"{number}: {task.__name__}")

    # Prompt the user for task selection
    selected_tasks = input("Enter task numbers: ").split(',')

    # Start a queue AFTER we've know patient data and which processes to look into.
    
    input_queue = queue.Queue()
    shared_state = {
        "QScript_code": None,
        "myHR_code": None,
        "paused": True,
        "exit": False
        }

    # Start the input thread
    input_thread_instance = threading.Thread(target=input_thread, args=(input_queue,))
    input_thread_instance.start()

    
    # Create tasks based on the user's selection
    tasks = []
    for task_number in selected_tasks:
        try:
            task_number = int(task_number.strip())  # Convert to integer and remove spaces
            if task_number in task_functions:
                task = asyncio.create_task(task_functions[task_number](CREDENTIALS_FILE, patient_details, shared_state))
                print(f'Starting task: ', task_functions[task_number])
                tasks.append(task)
            else:
                print(f"Task number {task_number} not recognized.")
        except ValueError:
            print(f"Invalid input: {task_number} is not a number.")

    # Add the input processing task which has to start regardless
    input_task = asyncio.create_task(process_inputs(input_queue, shared_state))
    tasks.append(input_task)

    # Wait for all tasks to complete
    print("Waiting for all tasks to complete...")
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("Tasks cancelled during shutdown.")
        pass  # This is normal during shutdown


    # Cancel all tasks - suspect redundancy here.
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    print("quitting input thread...")
    input_thread_instance.join()  # Ensure input thread is also completed
    print("All tasks terminated.")
    

# Run the main function
asyncio.run(main())
