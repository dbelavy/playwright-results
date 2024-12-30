import json
import aioconsole
import argparse
import time
import asyncio
import re
import queue
import threading
import importlib
import inspect
from pathlib import Path

from models import PatientDetails, SharedState
from datetime import datetime
from playwright.async_api import async_playwright
from pynput import keyboard
from aioconsole import ainput
from utils import input_thread, process_inputs

def load_providers():
    """Dynamically load all provider modules and their run functions"""
    providers = {}
    providers_dir = Path(__file__).parent / 'providers'
    
    # Skip __pycache__ and __init__.py
    for file_path in providers_dir.glob('*.py'):
        if file_path.stem.startswith('__'):
            continue
            
        try:
            # Import module using relative path
            module_name = f'providers.{file_path.stem}'
            module = importlib.import_module(module_name)
            
            # Find the run function
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if name.startswith('run_') and name.endswith('_process'):
                    # Convert function name to provider name
                    provider_name = name[4:-8].replace('_', ' ').title()
                    # Get required fields from module
                    required_fields = getattr(module, 'REQUIRED_FIELDS', [])
                    providers[provider_name] = (func, required_fields)
                    break
                    
        except Exception as e:
            print(f"Error loading provider {file_path.stem}: {e}")
            
    return providers

async def run_tasks(patient_details=None, selected_providers=None):
    """Run the selected tasks with the given patient details."""
    # Load all available providers
    providers = load_providers()
    
    if selected_providers is None:
        # Display available providers
        print("\nAvailable providers:")
        for i, name in enumerate(providers.keys(), 1):
            print(f"{i}. {name}")
            
        # Get provider selection
        selection = input("\nSelect providers (comma-separated names or numbers): ").strip()
        
        # Handle both number and name input
        selected_providers = []
        for item in selection.split(','):
            item = item.strip()
            if item.isdigit():
                # Convert number to provider name
                idx = int(item) - 1
                if 0 <= idx < len(providers):
                    selected_providers.append(list(providers.keys())[idx])
            else:
                # Try to match provider name
                matches = [name for name in providers.keys() 
                         if name.lower().startswith(item.lower())]
                selected_providers.extend(matches)

    # Get required fields from selected providers
    required_fields = set()
    for provider in selected_providers:
        if provider in providers:
            _, fields = providers[provider]
            required_fields.update(fields)

    print(f'\nRequired fields are: {list(required_fields)}\n')

    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Run Playwright script with user data")
    parser.add_argument("--family_name", help="Family Name", required=False)
    parser.add_argument("--given_name", help="Given Name", required=False)
    parser.add_argument("--dob", help="Date of Birth (DDMMYYYY)", required=False)
    parser.add_argument("--medicare_number", help="Medicare Number", required=False)
    parser.add_argument("--sex", help="Sex (M, F, or I)", required=False)
    args = parser.parse_args()

    # Use existing patient details if available
    if patient_details is not None:
        args.family_name = patient_details.family_name
        args.given_name = patient_details.given_name
        args.dob = patient_details.dob
        args.medicare_number = patient_details.medicare_number
        args.sex = patient_details.sex

    # Create or update PatientDetails object
    patient_details = PatientDetails.from_args(args, list(required_fields))
    print(f"Patient Details Collected: {patient_details}\n")

    # Get CLI args string for rerunning
    flags = patient_details.to_cli_args()
    if flags:
        print(f"If you want to view this patient again enter: python main.py {flags}")

    # Set up shared state and input handling
    input_queue = queue.Queue()
    shared_state = SharedState()

    # Start input thread
    input_thread_instance = threading.Thread(target=input_thread, args=(input_queue,))
    input_thread_instance.start()

    # Create tasks for selected providers
    tasks = []
    for provider in selected_providers:
        if provider in providers:
            run_func, _ = providers[provider]
            task = asyncio.create_task(run_func(patient_details, shared_state))
            tasks.append(task)
            print(f'Starting {provider} process')

    # Add input processing task
    input_task = asyncio.create_task(process_inputs(input_queue, shared_state))
    tasks.append(input_task)

    # Wait for all tasks
    print("Waiting for all tasks to complete...")
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("Tasks cancelled during shutdown.")

    # Cleanup
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    print("quitting input thread...")
    input_thread_instance.join()
    print("All tasks terminated.")

    return patient_details, selected_providers

async def main():
    """Main program loop that handles patient and provider selection."""
    patient_details = None
    selected_providers = None
    
    while True:
        if patient_details is not None:
            print("\nWhat would you like to do?")
            print("1: Use same patient (select new providers)")
            print("2: Enter new patient details")
            print("3: Exit program")
            choice = input("Enter choice (1-3): ").strip()
            
            if choice == "2":
                patient_details = None
                selected_providers = None
            elif choice == "1":
                selected_providers = None
            elif choice == "3":
                print("Goodbye!")
                break
            else:
                print("Invalid choice, please try again")
                continue
                
        patient_details, selected_providers = await run_tasks(patient_details, selected_providers)

# Run the main function
asyncio.run(main())
