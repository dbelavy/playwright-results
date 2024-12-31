#!/usr/bin/env zsh

# Function to check Python version
check_python_version() {
    local required_version="3.11.8"
    local current_version=$(python3 -c 'import platform; print(platform.python_version())')
    
    if [[ "$current_version" == "$required_version" ]]; then
        return 0
    else
        echo "Python version mismatch. Required: $required_version, Current: $current_version"
        return 1
    fi
}

# Function to check and setup environment
setup_environment() {
    # First, inform about any active conda environment
    if [[ ! -z "${CONDA_DEFAULT_ENV}" ]]; then
        echo "Note: Conda environment '${CONDA_DEFAULT_ENV}' is currently active"
    fi

    # Check if we're already in the correct venv with right Python version
    if [[ ! -z "${VIRTUAL_ENV}" ]] && [[ "${VIRTUAL_ENV}" == *"/venv" ]]; then
        if check_python_version; then
            echo "Already in correct virtual environment with Python 3.11.8"
            return 0
        else
            echo "Note: In project's venv but Python version is incorrect"
        fi
    fi

    # If we're not in the correct environment, activate our venv
    if [[ -d "venv" ]]; then
        echo "Activating project virtual environment..."
        source venv/bin/activate
        
        if check_python_version; then
            echo "Successfully activated correct environment"
            return 0
        else
            echo "Error: Virtual environment has incorrect Python version"
            return 1
        fi
    else
        echo "Error: Virtual environment not found. Please run install.sh first"
        return 1
    fi
}

# Create a new subshell to contain our environment changes
(
    echo "=== Environment Setup ==="

    if setup_environment; then
        echo "=== Starting Application ==="
        echo "Current Python path: $(which python3)"
        echo "Python version: $(python3 --version)"
        python3 main.py
    else
        echo "=== Environment setup failed ==="
        exit 1
    fi
)

# Original shell environment remains unchanged
echo "=== Script Complete ==="
