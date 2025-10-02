#!/bin/bash

# Env name
ENV_NAME="linkedin_games_ranking"
# Define the envc command
envc() {
    # Deactivate any currently active environment
    if [[ -n "$CONDA_DEFAULT_ENV" ]]; then
        echo "Deactivating current environment: $CONDA_DEFAULT_ENV"
        conda deactivate
    fi

    # Remove the environment if it already exists
    if conda env list | grep -q "^${ENV_NAME}\s"; then
        echo "Removing existing environment: $ENV_NAME"
        conda env remove -n $ENV_NAME -y
    fi

    # Create a new environment from environment.yml
    echo "Creating new environment from environment.yml"
    conda env create -f environment.yml -n $ENV_NAME

    # Activate the new environment
    echo "Activating new environment: $ENV_NAME"
    conda activate $ENV_NAME
}

# Export the function to make it available in the shell
export -f envc