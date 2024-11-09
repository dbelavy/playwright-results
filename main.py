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


# local files


from providers.medway import *
from providers.the_viewer import *
from providers.mater_path import *
from providers.qscript import *
from providers.snp_sonic import *
from providers.myhealthrecord import *
from providers.fourcyte import *
from utils import *


async def main():
    '''Some improvements to implement with data collection for the script
    # Dictionary mapping processes to required patient detail fields
    required_fields_for_process = {
        'Process_A': ['family_name', 'dob'],
        'Process_B': ['family_name', 'given_name', 'medicare_number'],
        'Process_C': ['family_name', 'given_name', 'dob', 'medicare_number', 'sex'],
        # Add more processes and their required fields as needed
    }

    # Function to get patient details based on the required fields for a process
    def get_patient_details_for_process(process_name):
        required_fields = required_fields_for_process.get(process_name, [])

        patient_details = {}
        for field in required_fields:
            if field == 'family_name':
                patient_details[field] = args.family_name if args.family_name else input("Enter Family Name: ")
            elif field == 'given_name':
                patient_details[field] = args.given_name if args.given_name else input("Enter Given Name: ")
            elif field == 'dob':
                patient_details[field] = args.dob if args.dob else input("Enter DOB (DDMMYYYY): ")
            elif field == 'medicare_number':
                patient_details[field] = str(args.medicare_number) if args.medicare_number else str(input("Enter Medicare Number (if applicable): "))
            elif field == 'sex':
                patient_details[field] = args.sex.upper() if args.sex else input("Enter Sex (M, F, or I), or press 'Enter' to skip: ").upper()

        return patient_details

    # Example usage
    process_name = 'Process_A'  # This could be determined dynamically based on user input or program flow
    patient_details = get_patient_details_for_process(process_name)
    '''

    # Map numbers to task functions
    task_functions = {
        1: run_medway_process,
        2: run_SNP_process,
        3: run_QScript_process,
        4: run_QGov_Viewer_process,
        5: run_myHealthRecord_process,
        6: run_mater_path_process,
        7: run_fourcyte_process
        # 8: run_ucq_process # Assuming this is another task function
    }

    # Display the task options
    print("Select tasks to run (separate by commas):")
    for number, task in task_functions.items():
        print(f"{number}: {task.__name__}")

    # Prompt the user for task selection
    selected_tasks = input("Enter task numbers: ").split(',')

    # Dictionary mapping processes to required patient detail fields
    required_fields_for_process = {
        'run_medway_process': ['family_name', 'given_name', 'dob'],
        'run_SNP_process': ['family_name', 'given_name', 'dob'],
        'run_QScript_process': ['family_name', 'given_name', 'dob'],
        'run_QGov_Viewer_process': ['family_name', 'dob', 'medicare_number', 'sex'],
        'run_myHealthRecord_process': ['family_name', 'dob', 'medicare_number', 'sex'],
        'run_mater_path_process': ['family_name', 'given_name', 'dob'],
        'run_fourcyte_process': ['family_name', 'given_name', 'dob'],
        'run_ucq_process': []

        # Add more processes and their required fields as needed
    }

    required_fields = []
    # this loop appends the fields required to required_fields
    for selected_task in selected_tasks:
        try:
            # Convert to integer and remove spaces
            selected_task = int(selected_task.strip())
            if selected_task in task_functions:
                # Get the function name
                function_name = task_functions[selected_task].__name__

                # Retrieve the required fields for this task
                task_fields = required_fields_for_process.get(
                    function_name, [])

                # print(f"You've asked for task {selected_task} which is called {function_name} which requires {task_fields}")
                for item in task_fields:
                    if item not in required_fields:
                        required_fields.append(item)

            else:
                print(f"Task number {selected_task} not recognized.")
        except ValueError:
            print(f"Invalid input: {selected_task} is not a number.")

    print(f'Required fields are: {required_fields}\n')

    # Set up command line arguments for the script
    parser = argparse.ArgumentParser(
        description="Run Playwright script with user data")
    parser.add_argument("--family_name", help="Family Name", required=False)
    parser.add_argument("--given_name", help="Given Name", required=False)
    parser.add_argument(
        "--dob", help="Date of Birth (DDMMYYYY)", required=False)
    parser.add_argument("--medicare_number",
                        help="Medicare Number (optional)", required=False)
    parser.add_argument("--sex", help="Sex (M, F, or I)", required=False)
    args = parser.parse_args()

    # Initialize the patient_details dictionary with conditional input based on required fields
    patient_details = {}

    # For each field, check if it's required. If it is, use the command line value if provided, otherwise prompt for input.
    patient_details['family_name'] = args.family_name if args.family_name else (
        input("Enter Family Name: ") if 'family_name' in required_fields else None)
    patient_details['given_name'] = args.given_name if args.given_name else (
        input("Enter Given Name: ") if 'given_name' in required_fields else None)
    # Validate the date of birth input
    if 'dob' in required_fields:
        if args.dob:
            patient_details['dob'] = args.dob
        else:
            dob_pattern = re.compile(r"^\d{2}\d{2}\d{4}$")
            while True:
                dob_input = input("Enter DOB (DDMMYYYY): ")
                if dob_pattern.match(dob_input):
                    # Further validation to ensure it's a valid date
                    try:
                        datetime.strptime(dob_input, "%d%m%Y")
                        patient_details['dob'] = dob_input
                        break
                    except ValueError:
                        print(
                            "Invalid date. Please enter a valid date in DDMMYYYY format.")
                else:
                    print(
                        "Invalid date format. Please enter the date in DDMMYYYY format.")
    else:
        patient_details['dob'] = None

    # patient_details['dob'] = args.dob if args.dob else (input("Enter DOB (DDMMYYYY): ") if 'dob' in required_fields else None)
    patient_details['medicare_number'] = str(args.medicare_number) if args.medicare_number else (
        str(input("Enter Medicare Number: ")) if 'medicare_number' in required_fields else None)
    if 'sex' in required_fields:
        # Get the value from args if provided, otherwise prompt for input
        patient_details['sex'] = args.sex.upper() if args.sex else input(
            "Enter Sex (M, F, or I): ").upper()
        # Ensure valid sex input
        while patient_details['sex'] not in ["M", "F", "I", ""]:
            print("Invalid input. Please enter 'M', 'F', 'I'")
            patient_details['sex'] = input("Enter Sex (M, F, or I): ").upper()
    else:
        # If 'sex' is not required, set it to None or a default value
        patient_details['sex'] = None

    print(f"Patient Details Collected: {patient_details}\n")

    # print instructions on how to restart the app with same patient
    flags = []

    if patient_details['family_name']:
        flags.append(f"--family_name {patient_details['family_name']}")
    if patient_details['given_name']:
        flags.append(f"--given_name {patient_details['given_name']}")
    if patient_details['dob']:
        flags.append(f"--dob {patient_details['dob']}")
    if patient_details['medicare_number']:
        flags.append(f"--medicare_number {patient_details['medicare_number']}")
    if patient_details['sex']:
        flags.append(f"--sex {patient_details['sex']}")

    if flags:
        print(f"If you want to view this patient again enter: python main.py {
              ' '.join(flags)}")

    # Define the path to the credentials file
    # CREDENTIALS_FILE = "credentials.json"

    # Start a queue AFTER we've know patient data and which processes to look into.

    input_queue = queue.Queue()
    shared_state = {
        "QScript_code": None,
        "PRODA_code": None,
        "4Cyte_code": None,
        "paused": True,
        "exit": False,
        "credentials_file": "credentials.json"

    }

    # Start the input thread
    input_thread_instance = threading.Thread(
        target=input_thread, args=(input_queue,))
    input_thread_instance.start()

    # Create tasks based on the user's selection
    tasks = []
    for task_number in selected_tasks:
        try:
            # Convert to integer and remove spaces
            task_number = int(task_number.strip())
            if task_number in task_functions:
                task = asyncio.create_task(
                    task_functions[task_number](patient_details, shared_state))
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

    # print instructions on how to restart the app with same patient
    flags = []

    if patient_details['family_name']:
        flags.append(f"--family_name {patient_details['family_name']}")
    if patient_details['given_name']:
        flags.append(f"--given_name {patient_details['given_name']}")
    if patient_details['dob']:
        flags.append(f"--dob {patient_details['dob']}")
    if patient_details['medicare_number']:
        flags.append(f"--medicare_number {patient_details['medicare_number']}")
    if patient_details['sex']:
        flags.append(f"--sex {patient_details['sex']}")

    if flags:
        print(f"If you want to view this patient again enter: python main.py {
              ' '.join(flags)}")

    # print(f"If you want to view this patient again enter: python3 main.py --family_name {patient_details['family_name']} --given_name {patient_details['given_name']} --dob {patient_details['dob']} --medicare_number {patient_details['medicare_number']} --sex {patient_details['sex']} " )


# Run the main function
asyncio.run(main())
