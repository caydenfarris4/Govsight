#!/bin/bash

# GovSight Cloud Run Deployment Script
# This script builds and deploys GovSight to Google Cloud Run

set -e  # Exit on error

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-govsight-production}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-govsight-app}"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/govsight-repo/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Install from https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Install from https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check if logged in to gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
        log_error "Not logged in to gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Set GCP project
set_project() {
    log_info "Setting GCP project to: ${PROJECT_ID}"
    gcloud config set project ${PROJECT_ID}
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    VERSION_TAG="${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S)"
    LATEST_TAG="${IMAGE_NAME}:latest"
    
    docker build -t ${VERSION_TAG} -t ${LATEST_TAG} .
    
    log_info "Built image: ${VERSION_TAG}"
}

# Push to Artifact Registry
push_image() {
    log_info "Pushing image to Artifact Registry..."
    
    # Configure Docker auth
    gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
    
    # Push both tags
    docker push ${VERSION_TAG}
    docker push ${LATEST_TAG}
    
    log_info "Image pushed successfully"
}

# Deploy to Cloud Run
deploy_to_cloudrun() {
    log_info "Deploying to Cloud Run..."
    
    gcloud run deploy ${SERVICE_NAME} \
        --image=${LATEST_TAG} \
        --platform=managed \
        --region=${REGION} \
        --allow-unauthenticated \
        --memory=2Gi \
        --cpu=2 \
        --timeout=300 \
        --concurrency=80 \
        --min-instances=1 \
        --max-instances=10 \
        --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
        --quiet
    
    log_info "Deployment complete"
}

# Get service URL
get_service_url() {
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --format="value(status.url)")
    
    log_info "Service URL: ${SERVICE_URL}"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Wait a few seconds for service to be ready
    sleep 5
    
    HEALTH_URL="${SERVICE_URL}/health"
    
    if curl -f -s ${HEALTH_URL} > /dev/null; then
        log_info "Health check passed"
    else
        log_warn "Health check failed - service may still be starting"
    fi
}

# Main deployment flow
main() {
    log_info "Starting GovSight deployment to Cloud Run"
    log_info "Project: ${PROJECT_ID}"
    log_info "Region: ${REGION}"
    log_info "Service: ${SERVICE_NAME}"
    echo ""
    
    check_prerequisites
    set_project
    build_image
    push_image
    deploy_to_cloudrun
    get_service_url
    health_check
    
    echo ""
    log_info "Deployment completed successfully!"
    log_info "Access your application at: ${SERVICE_URL}"
    echo ""
    log_info "To map custom domains, run:"
    log_info "  gcloud run domain-mappings create --service=${SERVICE_NAME} --domain=citya.govsight.net --region=${REGION}"
}

# Run main function
main
