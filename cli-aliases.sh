#!/bin/bash

# Load env variables
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
        enva
    fi
}

enva() {
    echo "Activating environment: $ENV_NAME"
    source .venv/Scripts/activate
}

# Start the FastAPI backend (dev mode)
dev_api() {
    echo "Starting FastAPI backend on http://localhost:8000"
    uvicorn src.api.main:app --reload --port 8000
}

# Start the React frontend (dev mode)
dev_frontend() {
    echo "Starting React frontend on http://localhost:5173"
    cd frontend && npm run dev
}

# Install frontend dependencies
frontend_install() {
    echo "Installing frontend dependencies..."
    cd frontend && npm install && cd ..
}

docker_build_push() {
    echo "Building Docker image..."
    docker build -t linkedin-games .

    echo "Tagging Docker image..."
    docker tag linkedin-games julescrevola/linkedin-games:latest

    echo "Pushing Docker image to Docker Hub..."
    docker push julescrevola/linkedin-games:latest
}

deploy_aks() {
    # Build and push to Docker
    docker_build_push
    # Deploy to AKS
    if kg deploy linkedin-games-ranking | grep -q "No resources found"; then

        echo "Creating new deployment..."
        echo "Getting AKS credentials..." # // codespell:ignore
        az aks get-credentials --resource-group rg-linkedin_games --name linkedin_games_ranking # // codespell:ignore aks

        echo "Applying Kubernetes deployment..."
        kubectl apply -f deployment.yaml

        IP_ADDRESS=$(kubectl get svc linkedin-games-ranking -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
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

        IP_ADDRESS=$(kubectl get svc linkedin-games-ranking -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
        if [[ -n $DOMAIN ]]; then
            echo "Deployment updated. Access the application at https://$DOMAIN"
        else
            echo "Deployment updated. Access the application at http://$IP_ADDRESS:80"
        fi
    fi
}

deploy_aca() {
    # Build and push to Docker
    docker_build_push
    # Deploy to ACA
    echo "Deploying to Azure Container Apps..."
    if az containerapp show --name "$ACA_NAME" --resource-group "$RG" >/dev/null 2>&1; then
        az containerapp secret set \
            --name "$ACA_NAME" \
            --resource-group "$RG" \
            --secrets supabase-url="$SUPABASE_URL" supabase-key="$SUPABASE_KEY"

        az containerapp update \
            --name "$ACA_NAME" \
            --resource-group "$RG" \
            --image julescrevola/linkedin-games:latest \
            --set-env-vars SUPABASE_URL=secretref:supabase-url SUPABASE_KEY=secretref:supabase-key
        echo "Deployment complete. Access the application at https://$DOMAIN"
    else
        az containerapp create \
            --name "$ACA_NAME" \
            --resource-group "$RG" \
            --image julescrevola/linkedin-games:latest \
            --environment "$ACA_ENV_NAME" \
            --target-port 8000 \
            --ingress 'external' \
            --registry-server 'index.docker.io' \
            --registry-username "$DOCKERHUB_USERNAME" \
            --registry-password "$DOCKERHUB_PASSWORD" \
            --secrets supabase-url="$SUPABASE_URL" supabase-key="$SUPABASE_KEY" \
            --env-vars SUPABASE_URL=secretref:supabase-url SUPABASE_KEY=secretref:supabase-key
        IP_ADDRESS=$(nslookup $(az containerapp show --name "$ACA_NAME" --resource-group "$RG" --query properties.configuration.ingress.fqdn -o tsv) | grep 'Address' | tail -n1 | awk '{print $2}')
        echo "Deployment complete. Change the DNS records to point to the new Container App IP address : $IP_ADDRESS, and access the application at https://$DOMAIN"
    fi
}

host_aca() {
    echo "▶ Resolving Container App endpoint..."
    ACA_FQDN=$(az containerapp show \
        --name "$ACA_NAME" \
        --resource-group "$RG" \
        --query properties.configuration.ingress.fqdn \
        -o tsv)

    if [[ -z "$ACA_FQDN" ]]; then
        echo "Could not resolve ACA FQDN. Ensure ingress is enabled on the container app."
        return 1
    fi

    ACA_IP=$(nslookup "$ACA_FQDN" | awk '/^Address: /{print $2}' | tail -n1)
    if [[ -z "$ACA_IP" ]]; then
        echo "Could not resolve ACA IP from FQDN: $ACA_FQDN"
        return 1
    fi

    ASUID_VALUE=$(az containerapp show \
        --name "$ACA_NAME" \
        --resource-group "$RG" \
        --query properties.customDomainVerificationId \
        -o tsv)
    if [[ -z "$ASUID_VALUE" ]]; then
        echo "Could not read Container App customDomainVerificationId (asuid value)."
        return 1
    fi

    upsert_a_record() {
        local record_name="$1"
        local record_ip="$2"

        az network dns record-set a create \
            -g "$DNS_ZONE_RG" \
            -z "$DNS_ZONE_NAME" \
            -n "$record_name" \
            --ttl 300 >/dev/null

        az network dns record-set a update \
            -g "$DNS_ZONE_RG" \
            -z "$DNS_ZONE_NAME" \
            -n "$record_name" \
            --set aRecords=[] >/dev/null

        az network dns record-set a add-record \
            -g "$DNS_ZONE_RG" \
            -z "$DNS_ZONE_NAME" \
            -n "$record_name" \
            -a "$record_ip" >/dev/null
    }

    upsert_txt_record() {
        local record_name="$1"
        local txt_value="$2"

        az network dns record-set txt create \
            -g "$DNS_ZONE_RG" \
            -z "$DNS_ZONE_NAME" \
            -n "$record_name" \
            --ttl 300 >/dev/null

        az network dns record-set txt update \
            -g "$DNS_ZONE_RG" \
            -z "$DNS_ZONE_NAME" \
            -n "$record_name" \
            --set txtRecords=[] >/dev/null

        az network dns record-set txt add-record \
            -g "$DNS_ZONE_RG" \
            -z "$DNS_ZONE_NAME" \
            -n "$record_name" \
            --value "$txt_value" >/dev/null
    }

    echo "▶ Creating/updating @ and www A records in Azure DNS..."
    upsert_a_record "@" "$ACA_IP"
    upsert_a_record "www" "$ACA_IP"

    echo "▶ Creating/updating asuid TXT record..."
    upsert_txt_record "asuid" "$ASUID_VALUE"

    echo "✅ DNS records configured"
}

host_aks() {
    echo "▶ Using subscription $SUBSCRIPTION_ID"
    az account set --subscription "$SUBSCRIPTION_ID"

    echo "▶ Connecting kubectl to AKS..."
    az aks get-credentials \
    -g "$RG" \
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
    -g "$RG" \
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
export -f deploy_aks
export -f host_aks
export -f docker_build_push
export -f deploy_aca
export -f host_aca
export -f dev_api
export -f dev_frontend
