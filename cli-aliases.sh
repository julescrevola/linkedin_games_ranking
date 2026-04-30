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

deploy(){
    echo "Building Docker image..."
    docker build -t linkedin-games .

    echo "Tagging Docker image..."
    docker tag linkedin-games julescrevola/linkedin-games:latest

    echo "Pushing Docker image to Docker Hub..."
    docker push julescrevola/linkedin-games:latest

    if kg deploy linkedin-games-ranking | grep -q "No resources found"; then

        echo "Creating new deployment..."
        echo "Getting AKS credentials..." # // codespell:ignore
        az aks get-credentials --resource-group rg-linkedin_games --name linkedin_games_ranking # // codespell:ignore aks

        echo "Applying Kubernetes deployment..."
        kubectl apply -f deployment.yaml

        IP_ADDRESS=$(kubectl get svc linkedin-games-ranking -o jsonpath='{.status.loadBalancer.ingress[0].externalIP}')
        echo "Deployment complete. Access the application at http://$IP_ADDRESS:80"
    else
        echo "Existing deployment found. Updating it with latest Docker image pushed to DockerHub."

        echo "Getting image digest..."
        IMAGE_DIGEST=$(docker buildx imagetools inspect julescrevola/linkedin-games:latest | grep Digest: | awk '{print $2}')

        echo "Updating Kubernetes deployment with new image digest..."
        kubectl set image deployment/linkedin-games-ranking linkedin-games-ranking=julescrevola/linkedin-games@$IMAGE_DIGEST

        IP_ADDRESS=$(kubectl get svc linkedin-games-ranking -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        echo "Deployment updated. Access the application at http://$IP_ADDRESS:80"
    fi
}

# Export the functions to make them available in the shell
export -f envc
export -f enva
export -f deploy
