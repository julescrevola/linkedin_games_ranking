#!/bin/bash

# Env name
ENV_NAME="linkedin_games_ranking"

envc() {
    # Check if the environment already exists
    if [ -d ".venv" ]; then
        echo "Virtual environment already exists: .venv"
        enva
    else
        # Create a new environment from uv.lock
        echo "Creating new environment with uv"
        uv sync

        # Activate the new environment
        echo "Activating new environment: $ENV_NAME"
        source .venv/Scripts/activate
    fi
}

enva() {
    echo "Activating environment: $ENV_NAME"
    source .venv/Scripts/activate
}

# Export the functions to make them available in the shell
export -f envc
export -f enva
