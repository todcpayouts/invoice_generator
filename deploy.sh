#!/bin/bash

# Exit on any error
set -e

# Configuration
PROJECT_ID="green-webbing-437519-a7"
REGION="us-central1"
SERVICE_NAME="invoice-generator"
BUCKET_NAME="todc_invoice_generator"
SERVICE_ACCOUNT="70295468269-compute@developer.gserviceaccount.com"

# Print functions
echo_info() {
    echo "[INFO] $1"
}

echo_error() {
    echo "[ERROR] $1"
    exit 1
}

# Setup project
echo_info "Setting up project..."
gcloud config set project $PROJECT_ID

# Enable required services
echo_info "Enabling required services..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

# Create or update secret with service account content
echo_info "Setting up secret..."
if [[ -f "service-account.json" ]]; then
    SECRET_NAME="invoice-creds"
    
    # Create or update the secret
    cat service-account.json | gcloud secrets create $SECRET_NAME \
        --data-file=- \
        --replication-policy="automatic" \
        2>/dev/null || \
    cat service-account.json | gcloud secrets versions add $SECRET_NAME \
        --data-file=-
        
    # Set permissions
    gcloud secrets add-iam-policy-binding $SECRET_NAME \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor"
else
    echo_error "service-account.json not found!"
    exit 1
fi

# Deploy to Cloud Run
echo_info "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 0 \
    --max-instances 10 \
    --set-env-vars "BUCKET_NAME=$BUCKET_NAME" \
    --update-secrets="GOOGLE_APPLICATION_CREDENTIALS=invoice-creds:latest" \
    --service-account="$SERVICE_ACCOUNT"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format='value(status.url)')

echo_info "Deployment completed!"
echo_info "Service URL: $SERVICE_URL"