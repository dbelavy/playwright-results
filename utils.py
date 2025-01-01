import argparse
import asyncio
import json
import queue
import re
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Set

import aioconsole
import pyotp
import pyperclip
from aioconsole import ainput
from playwright.async_api import async_playwright
from playwright.sync_api import Playwright, expect, sync_playwright
from pynput import keyboard

from models import Credentials, SharedState


class ClipboardTwoFactorMonitor:
    def __init__(self, shared_state: SharedState):
        self.shared_state = shared_state
        self.waiting_providers: Set[str] = set()
        self.last_clipboard = ""
        self.patterns = {
            r"Use verification code (\d{6}) for QScript authentication": "QScript",
            r"Your verification code is (\d{6}) for Provider Digital Access": "PRODA",
        }

    def add_provider(self, provider: str):
        self.waiting_providers.add(provider)
        # Increment the pending 2FA count
        self.shared_state.pending_2fa_count = (
            getattr(self.shared_state, "pending_2fa_count", 0) + 1
        )

        print(f"\nMonitoring clipboard for {provider} 2FA code...")
        print("Just copy the SMS message and the code will be automatically detected")
        print("Or enter code manually: 1=PRODA, 2=QScript (e.g. 1123456)")
        print("Enter 'x' to quit")

        if len(self.waiting_providers) > 1:
            print(
                f"\nCurrently waiting for {len(self.waiting_providers)} 2FA codes from: {', '.join(self.waiting_providers)}"
            )

    def remove_provider(self, provider: str):
        if provider in self.waiting_providers:
            self.waiting_providers.discard(provider)
            # Decrement the pending 2FA count
            self.shared_state.pending_2fa_count = max(
                0, getattr(self.shared_state, "pending_2fa_count", 0) - 1
            )

    def check_clipboard(self):
        try:
            current_clipboard = pyperclip.paste()
            if current_clipboard != self.last_clipboard:
                self.last_clipboard = current_clipboard

                # Check clipboard content against patterns for waiting providers
                for pattern, provider in self.patterns.items():
                    if provider in self.waiting_providers:
                        match = re.search(pattern, current_clipboard)
                        if match:
                            code = match.group(1)  # Get the captured 6-digit code
                            self.shared_state.set_2fa_code(provider, code)
                            print(
                                f"\n✓ 2FA code automatically detected for {provider}: {code}"
                            )
                            self.remove_provider(provider)

                            # Show remaining providers if any
                            if self.waiting_providers:
                                print(
                                    f"\nStill waiting for {len(self.waiting_providers)} 2FA codes from: {', '.join(self.waiting_providers)}"
                                )
                            return True
        except Exception as e:
            print(f"\nError reading clipboard: {e}")
        return False


async def process_inputs(input_queue, shared_state: SharedState):
    monitor = ClipboardTwoFactorMonitor(shared_state)

    while True:
        if not input_queue.empty():
            user_input = input_queue.get()

            # Check for quit command
            if user_input.lower() == "x":
                print("\nReceived quit instruction...")
                shared_state.exit = True
                break

            # Allow manual entry as fallback (e.g. 1123456)
            match = re.match(r"^([12])(\d{6})$", user_input)
            if match:
                menu_num, code = match.groups()
                provider_map = {"1": "PRODA", "2": "QScript"}
                if menu_num in provider_map:
                    provider = provider_map[menu_num]
                    if provider in monitor.waiting_providers:
                        shared_state.set_2fa_code(provider, code)
                        print(f"\n✓ 2FA code manually entered for {provider}")
                        monitor.remove_provider(provider)

                        # Show remaining providers if any
                        if monitor.waiting_providers:
                            print(
                                f"\nStill waiting for {len(monitor.waiting_providers)} 2FA codes from: {', '.join(monitor.waiting_providers)}"
                            )
                    else:
                        print(
                            f"\n⚠ No {provider} process is currently waiting for a 2FA code"
                        )
                        if monitor.waiting_providers:
                            print(
                                f"\nWaiting for codes from: {', '.join(monitor.waiting_providers)}"
                            )

        # Check if any provider is waiting for 2FA
        if hasattr(shared_state, "new_2fa_request"):
            provider = shared_state.new_2fa_request
            if provider and provider not in monitor.waiting_providers:
                monitor.add_provider(provider)
            shared_state.new_2fa_request = None

        # Check clipboard for new 2FA codes
        monitor.check_clipboard()

        await asyncio.sleep(0.1)


def input_thread(input_queue):
    print("Enter 'x' to quit")
    while True:
        try:
            user_input = input("> ")
            input_queue.put(user_input)
            if user_input.lower() == "x":
                break
        except EOFError:
            print("EOF encountered in input stream.")
            break


def load_credentials(shared_state: SharedState, company: str) -> Optional[Credentials]:
    """Load credentials for a specific provider using the Credentials class"""
    try:
        return Credentials.load(shared_state.credentials_file, company)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading credentials: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error loading credentials: {e}")
        return None


def generate_2fa_code(totp_secret):
    """
    Generates a 2FA code using the provided TOTP secret.

    :param totp_secret: The TOTP secret key (base32-encoded) used to generate the OTP code.
    :return: The current OTP code.
    """
    try:
        # Create a TOTP object using the secret
        totp = pyotp.TOTP(totp_secret)

        # Get the current OTP code
        current_otp = totp.now()

        return current_otp
    except Exception as e:
        print(f"An error occurred while generating the 2FA code: {e}")
        return None


def convert_gender(input_gender, output_format_required):
    # Define a mapping based on the output format string "M1F2I3"
    if output_format_required == "M1F2I3":
        gender_mapping = {"M": "1", "F": "2", "I": "3"}

    return gender_mapping.get(input_gender, None)


def convert_date_format(date_string, input_format, output_format):
    """
    Convert a date string from one format to another
    """
    try:
        # Convert the input string to a datetime object
        date_obj = datetime.strptime(date_string, input_format)

        # Format the datetime object to the desired output format
        return date_obj.strftime(output_format)
    except ValueError:
        print("Invalid date format.")
        return None
