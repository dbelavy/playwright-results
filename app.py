import streamlit as st
import asyncio
import json
import queue
import threading
from datetime import datetime
import re
from providers.medway import *
from providers.the_viewer import *
from providers.mater_path import *
from providers.qscript import *
from providers.snp_sonic import *
from providers.myhealthrecord import *
from providers.fourcyte import *
from providers.meditrust import *
from providers.imed import *
from utils import *

# Configure the Streamlit page
st.set_page_config(
    page_title="Medical Records Automation",
    page_icon="🏥",
    layout="wide"
)

# Initialize session state variables
if 'process_running' not in st.session_state:
    st.session_state.process_running = False
if 'shared_state' not in st.session_state:
    st.session_state.shared_state = {
        "QScript_code": None,
        "PRODA_code": None,
        "4Cyte_code": None,
        "paused": True,
        "exit": False,
        "credentials_file": "credentials.json"
    }
if 'selected_tasks' not in st.session_state:
    st.session_state.selected_tasks = []
if 'required_fields' not in st.session_state:
    st.session_state.required_fields = []

# Define available tasks
TASKS = {
    "Medway": run_medway_process,
    "SNP": run_SNP_process,
    "QScript": run_QScript_process,
    "QGov Viewer": run_QGov_Viewer_process,
    "MyHealth Record": run_myHealthRecord_process,
    "Mater Path": run_mater_path_process,
    "4Cyte": run_fourcyte_process,
    "iMed": run_imed_process,
    "Meditrust": run_meditrust_process
}

# Define required fields for each process
REQUIRED_FIELDS = {
    'run_medway_process': ['family_name', 'given_name', 'dob'],
    'run_SNP_process': ['family_name', 'given_name', 'dob'],
    'run_QScript_process': ['family_name', 'given_name', 'dob'],
    'run_QGov_Viewer_process': ['family_name', 'dob', 'medicare_number', 'sex'],
    'run_myHealthRecord_process': ['family_name', 'dob', 'medicare_number', 'sex'],
    'run_mater_path_process': ['family_name', 'given_name', 'dob'],
    'run_fourcyte_process': ['family_name', 'given_name', 'dob'],
    'run_meditrust_process': [],
    'run_imed_process': ['family_name', 'given_name', 'dob']
}

# Field labels with required indicator
FIELD_LABELS = {
    'family_name': "Family Name",
    'given_name': "Given Name",
    'dob': "Date of Birth (DDMMYYYY)",
    'medicare_number': "Medicare Number",
    'sex': "Sex"
}

def validate_dob(dob):
    """Validate date of birth format and value"""
    if not re.match(r"^\d{8}$", dob):
        return False
    try:
        datetime.strptime(dob, "%d%m%Y")
        return True
    except ValueError:
        return False

def get_required_fields(selected_tasks):
    """Get all required fields for selected tasks"""
    required_fields = set()
    for task_name in selected_tasks:
        task_func = TASKS[task_name]
        fields = REQUIRED_FIELDS.get(task_func.__name__, [])
        required_fields.update(fields)
    return list(required_fields)

def on_tasks_change():
    """Update required fields when tasks change"""
    st.session_state.required_fields = get_required_fields(st.session_state.selected_tasks)

async def run_automation(patient_details, selected_tasks):
    """Run the selected automation tasks"""
    tasks = []
    input_queue = queue.Queue()
    
    for task_name in selected_tasks:
        task_func = TASKS[task_name]
        task = asyncio.create_task(task_func(patient_details, st.session_state.shared_state))
        tasks.append(task)
    
    # Add input processing task
    input_task = asyncio.create_task(process_inputs(input_queue, st.session_state.shared_state))
    tasks.append(input_task)
    
    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        st.error(f"Error during automation: {str(e)}")
    finally:
        for task in tasks:
            task.cancel()

def main():
    st.title("Medical Records Automation")
    
    # Create two columns for the layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Patient Details")
        
        # Task selection outside the form for real-time updates
        st.subheader("Select Tasks")
        st.session_state.selected_tasks = st.multiselect(
            "Choose tasks to run",
            options=list(TASKS.keys()),
            key="task_selector",
            on_change=on_tasks_change
        )

        # Show required fields based on selected tasks
        if st.session_state.selected_tasks:
            st.info(f"Required fields for selected tasks: {', '.join(get_required_fields(st.session_state.selected_tasks))}")
        
        # Patient details form
        with st.form("patient_details"):
            # Add fields with required indicator based on selected tasks
            required_fields = get_required_fields(st.session_state.selected_tasks)
            
            family_name = st.text_input(
                f"{FIELD_LABELS['family_name']} {'*' if 'family_name' in required_fields else ''}"
            )
            
            given_name = st.text_input(
                f"{FIELD_LABELS['given_name']} {'*' if 'given_name' in required_fields else ''}"
            )
            
            dob = st.text_input(
                f"{FIELD_LABELS['dob']} {'*' if 'dob' in required_fields else ''}"
            )
            
            medicare_number = st.text_input(
                f"{FIELD_LABELS['medicare_number']} {'*' if 'medicare_number' in required_fields else ''}"
            )
            
            sex = st.selectbox(
                f"{FIELD_LABELS['sex']} {'*' if 'sex' in required_fields else ''}",
                ["", "M", "F", "I"]
            )
            
            submitted = st.form_submit_button("Start Automation")
            
            if submitted:
                if not st.session_state.selected_tasks:
                    st.error("Please select at least one task.")
                    return
                
                # Create patient details dictionary
                patient_details = {
                    'family_name': family_name,
                    'given_name': given_name,
                    'dob': dob,
                    'medicare_number': medicare_number,
                    'sex': sex
                }
                
                # Validate DOB if required
                if 'dob' in required_fields:
                    if not dob:
                        st.error("Date of Birth is required for the selected tasks.")
                        return
                    if not validate_dob(dob):
                        st.error("Please enter a valid date of birth in DDMMYYYY format.")
                        return
                
                # Check all required fields are filled
                missing_fields = []
                for field in required_fields:
                    if not patient_details[field]:
                        missing_fields.append(FIELD_LABELS[field])
                
                if missing_fields:
                    st.error(f"Please fill in the following required fields: {', '.join(missing_fields)}")
                    return
                
                # Start automation
                st.session_state.process_running = True
                asyncio.run(run_automation(patient_details, st.session_state.selected_tasks))
    
    with col2:
        st.header("Status")
        
        # 2FA Input Section - Always visible
        st.subheader("2FA Verification Codes")
        with st.container():
            st.markdown("Enter verification codes when prompted:")
            
            # QScript 2FA
            qscript_code = st.text_input(
                "QScript 2FA Code",
                placeholder="Enter code starting with Q",
                key="qscript_2fa"
            )
            if qscript_code:
                st.session_state.shared_state["QScript_code"] = qscript_code
                st.success(f"QScript code entered: {qscript_code}")
            
            # PRODA 2FA
            proda_code = st.text_input(
                "PRODA 2FA Code",
                placeholder="Enter code starting with P",
                key="proda_2fa"
            )
            if proda_code:
                st.session_state.shared_state["PRODA_code"] = proda_code
                st.success(f"PRODA code entered: {proda_code}")
            
            # 4Cyte 2FA
            fourcyte_code = st.text_input(
                "4Cyte 2FA Code",
                placeholder="Enter verification code",
                key="4cyte_2fa"
            )
            if fourcyte_code:
                st.session_state.shared_state["4Cyte_code"] = fourcyte_code
                st.success(f"4Cyte code entered: {fourcyte_code}")
        
        # Automation Status Section
        st.markdown("---")  # Visual separator
        st.subheader("Automation Status")
        if st.session_state.process_running:
            st.info("Automation in progress...")
            
            # Control buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Pause/Resume"):
                    st.session_state.shared_state["paused"] = not st.session_state.shared_state["paused"]
            
            with col2:
                if st.button("Stop"):
                    st.session_state.shared_state["exit"] = True
                    st.session_state.process_running = False
                    st.experimental_rerun()

if __name__ == "__main__":
    main()
