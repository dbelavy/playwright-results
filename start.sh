#!/bin/bash

run_application() {
    echo "=== Initial Environment Cleanup ==="
    # Deactivate any conda environments
    if [[ ! -z "${CONDA_DEFAULT_ENV}" ]]; then
        echo "Deactivating conda environment: $CONDA_DEFAULT_ENV"
        conda deactivate
    fi

    # Deactivate any virtual environments
    if [[ ! -z "${VIRTUAL_ENV}" ]]; then
        echo "Deactivating virtual environment: $VIRTUAL_ENV"
        deactivate
    fi

    echo -e "\n=== Environment Setup ==="
    # Activate the project's venv
    echo "Activating project venv..."
    source venv/bin/activate

    # Show Python path to confirm environment
    echo "Current Python path:"
    which python3

    # Show Python version
    echo "Python version:"
    python3 --version

    echo -e "\n=== Starting Application ==="
    python3 main.py

    echo -e "\n=== Final Environment Cleanup ==="
    if [[ ! -z "${VIRTUAL_ENV}" ]]; then
        echo "Deactivating virtual environment: $VIRTUAL_ENV"
        deactivate
    fi
    if [[ ! -z "${CONDA_DEFAULT_ENV}" ]]; then
        echo "Deactivating conda environment: $CONDA_DEFAULT_ENV"
        conda deactivate
    fi
    echo "Environment cleanup complete"
}

# Run the complete lifecycle
run_application
