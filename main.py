import json
import aioconsole
import argparse
import time
import asyncio
import re
import queue
import threading

from models import PatientDetails, SharedState

from playwright.sync_api import Playwright, sync_playwright, expect
from datetime import datetime
from playwright.async_api import async_playwright
from pynput import keyboard
from aioconsole import ainput


# local files
from providers.medway import run_medway_process
from providers.the_viewer import run_QGov_Viewer_process
from providers.materpathold import run_materpathold_process
from providers.materpathnew import run_materpathnew_process
from providers.qscript import run_QScript_process
from providers.snp_sonic import run_SNP_process
from providers.myhealthrecord import run_myHealthRecord_process
from providers.fourcyte import run_fourcyte_process
from providers.meditrust import run_meditrust_process
from providers.imed import run_imed_process
from utils import input_thread, process_inputs


# Map numbers to task functions
task_functions = {
    1: run_medway_process,
    2: run_SNP_process,
    3: run_QScript_process,
    4: run_QGov_Viewer_process,
    5: run_myHealthRecord_process,
    6: run_materpathold_process,
    7: run_fourcyte_process,
    8: run_imed_process,
    9: run_meditrust_process,
    10: run_materpathnew_process
}

async def run_tasks(patient_details=None, selected_tasks=None):
    """Run the selected tasks with the given patient details.
    
    Args:
        patient_details: Optional PatientDetails object. If None, will prompt for details.
        selected_tasks: Optional list of task numbers. If None, will prompt for selection.
    """

    if selected_tasks is None:
        # Display the task options
        print("\nSelect tasks to run (separate by commas):")
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
        'run_materpathold_process': ['family_name', 'given_name', 'dob'],
        'run_fourcyte_process': ['family_name', 'given_name', 'dob'],
        'run_ucq_process': [],
        'run_meditrust_process': [],
        'run_imed_process': ['family_name', 'given_name', 'dob'],
        'run_materpathnew_process': ['family_name', 'given_name', 'dob'],


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

    # If patient_details exists, create args from existing details
    if patient_details is not None:
        args.family_name = patient_details.family_name
        args.given_name = patient_details.given_name
        args.dob = patient_details.dob
        args.medicare_number = patient_details.medicare_number
        args.sex = patient_details.sex

    # Create or update PatientDetails object from args and required fields
    patient_details = PatientDetails.from_args(args, required_fields)
    print(f"Patient Details Collected: {patient_details}\n")

    # Get CLI args string for rerunning with same patient
    flags = patient_details.to_cli_args()
    if flags:
        print(f"If you want to view this patient again enter: python main.py {flags}")

    # Define the path to the credentials file
    # CREDENTIALS_FILE = "credentials.json"

    # Start a queue AFTER we've know patient data and which processes to look into.

    # Create a fresh queue and shared state for this run
    input_queue = queue.Queue()
    shared_state = SharedState()  # Initialize with default values

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

    # Cancel all tasks
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    print("quitting input thread...")
    input_thread_instance.join()
    print("All tasks terminated.")

    return patient_details, selected_tasks

async def main():
    """Main program loop that handles patient and task selection."""
    patient_details = None
    selected_tasks = None
    
    while True:
        if patient_details is not None:
            print("\nWhat would you like to do?")
            print("1: Use same patient (select new tasks)")
            print("2: Enter new patient details")
            print("3: Exit program")
            choice = input("Enter choice (1-3): ").strip()
            
            if choice == "2":
                patient_details = None
                selected_tasks = None
            elif choice == "1":
                selected_tasks = None  # Keep patient but get new task selection
            elif choice == "3":
                print("Goodbye!")
                break
            else:
                print("Invalid choice, please try again")
                continue
                
        patient_details, selected_tasks = await run_tasks(patient_details, selected_tasks)

# Run the main function
asyncio.run(main())
