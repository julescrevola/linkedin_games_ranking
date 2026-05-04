#!/bin/bash

# Load env ariables
set -a
source .env
set +a

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
        if [[ -n $DOMAIN ]]; then
            echo "Deployment complete. Access the application at https://$DOMAIN"
        else
            echo "Deployment complete. Access the application at http://$IP_ADDRESS:80"
        fi
    else
        echo "Existing deployment found. Updating it with latest Docker image pushed to DockerHub."

        echo "Getting image digest..."
        IMAGE_DIGEST=$(docker buildx imagetools inspect julescrevola/linkedin-games:latest | grep Digest: | awk '{print $2}')

        echo "Updating Kubernetes deployment with new image digest..."
        kubectl set image deployment/linkedin-games-ranking linkedin-games-ranking=julescrevola/linkedin-games@$IMAGE_DIGEST

        IP_ADDRESS=$(kubectl get svc linkedin-games-ranking -o jsonpath='{.status.loadBalancer.ingress[0].externalIP}')
        if [[ -n $DOMAIN ]]; then
            echo "Deployment updated. Access the application at https://$DOMAIN"
        else
            echo "Deployment updated. Access the application at http://$IP_ADDRESS:80"
        fi
    fi
}

host(){
    echo "▶ Using subscription $SUBSCRIPTION_ID"
    az account set --subscription "$SUBSCRIPTION_ID"

    echo "▶ Connecting kubectl to AKS..."
    az aks get-credentials \
    -g "$AKS_RG" \
    -n "$AKS_NAME" \
    --overwrite-existing

    echo "▶ Installing NGINX Ingress Controller..."
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml

    echo "▶ Waiting for NGINX controller to be ready..."
    kubectl wait \
    --namespace "$INGRESS_NAMESPACE" \
    --for=condition=available deployment/ingress-nginx-controller \
    --timeout=5m

    echo "▶ Fetching NGINX LoadBalancer external IP..."
    INGRESS_IP=""
    while [[ -z "$INGRESS_IP" ]]; do
    INGRESS_IP=$(kubectl get svc ingress-nginx-controller \
        -n "$INGRESS_NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || true)
    sleep 5
    done

    echo "✅ NGINX External IP: $INGRESS_IP"

    echo "▶ Creating A records in Azure DNS..."
    az network dns record-set a create \
    -g "$DNS_ZONE_RG" \
    -z "$DNS_ZONE_NAME" \
    -n "@" \
    --ttl 300 >/dev/null || true

    az network dns record-set a add-record \
    -g "$DNS_ZONE_RG" \
    -z "$DNS_ZONE_NAME" \
    -n "@" \
    -a "$INGRESS_IP" >/dev/null || true

    az network dns record-set a create \
    -g "$DNS_ZONE_RG" \
    -z "$DNS_ZONE_NAME" \
    -n "www" \
    --ttl 300 >/dev/null || true

    az network dns record-set a add-record \
    -g "$DNS_ZONE_RG" \
    -z "$DNS_ZONE_NAME" \
    -n "www" \
    -a "$INGRESS_IP" >/dev/null || true

    echo "▶ Installing cert-manager..."
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

    echo "▶ Granting Azure DNS permissions to AKS system identity..."
    AKS_PRINCIPAL_ID=$(az aks show \
    -g "$AKS_RG" \
    -n "$AKS_NAME" \
    --query identity.principalId \
    -o tsv)
    echo "AKS principalId: $AKS_PRINCIPAL_ID"

    if ! az role assignment create \
    --assignee-object-id "$AKS_PRINCIPAL_ID" \
    --assignee-principal-type ServicePrincipal \
    --role "DNS Zone Contributor" \
    --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$DNS_ZONE_RG/providers/Microsoft.Network/dnszones/$DNS_ZONE_NAME" \
    2>&1 | grep -q "MissingSubscription"; then
        :  # Success or different error
    else # Pause the script if error MissingSubscription
        echo "MissingSubscription error detected."
        echo "Please go to the Azure Portal > Your DNS Zone resource > Access Control (IAM) > Add > Add role assignment > Select DNS Zone Contributor in Role, then select Managed Identity in Members > + Select Members > Choose your subscription, and in Managed Identity, choose Kubernetes Service, then select your AKS resource > Select > Review + assign."
        read -p "Press Enter to continue..."
    fi

    echo "▶ Creating ClusterIssuer (DNS-01 + system identity)..."
    kubectl apply -f cluster_issuer.yaml
    echo "▶ Restarting cert-manager to pick up MSI permissions..."
    kubectl rollout restart deployment cert-manager -n "$CERT_MANAGER_NAMESPACE"

    echo "▶ Creating Ingress with TLS..."
    kubectl apply -f ingress.yaml

    echo "▶ Done."
    echo
    echo "Now run:"
    echo "  kubectl get certificate -w"
    echo "and wait for READY to be True."
    echo
    echo "Then check DNS propagation with:"
    echo "  nslookup -type=TXT _acme-challenge.$DOMAIN"
    echo "You should see a TXT record with a value that cert-manager created for domain validation."
    echo
    echo "It might take a few minutes for the certificate to be issued and DNS to propagate, so be patient and try the command multiple times!"
    echo "To check the logs, you can also run:"
    echo "  kubectl logs -n $CERT_MANAGER_NAMESPACE deployment/cert-manager"
    echo
    echo "Once everything is ready, access the application at https://$DOMAIN"
}

# Export the functions to make them available in the shell
export -f envc
export -f enva
export -f deploy
export -f host
