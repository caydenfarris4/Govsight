#!/bin/bash

# GovSight GCP Initial Setup Script
# This script sets up the initial GCP infrastructure for GovSight

set -e

# Configuration
PROJECT_ID="${1:-govsight-production}"
REGION="${2:-us-central1}"
SERVICE_NAME="govsight-app"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Create project
create_project() {
    log_info "Creating GCP project: ${PROJECT_ID}"
    
    if gcloud projects describe ${PROJECT_ID} &>/dev/null; then
        log_warn "Project ${PROJECT_ID} already exists"
    else
        gcloud projects create ${PROJECT_ID} --name="GovSight Production"
    fi
    
    gcloud config set project ${PROJECT_ID}
}

# Enable APIs
enable_apis() {
    log_info "Enabling required APIs..."
    
    gcloud services enable run.googleapis.com
    gcloud services enable sql-component.googleapis.com
    gcloud services enable sqladmin.googleapis.com
    gcloud services enable compute.googleapis.com
    gcloud services enable storage.googleapis.com
    gcloud services enable bigquery.googleapis.com
    gcloud services enable aiplatform.googleapis.com
    gcloud services enable secretmanager.googleapis.com
    gcloud services enable cloudbuild.googleapis.com
    gcloud services enable artifactregistry.googleapis.com
    
    log_info "APIs enabled"
}

# Create Artifact Registry
create_artifact_registry() {
    log_info "Creating Artifact Registry repository..."
    
    if gcloud artifacts repositories describe govsight-repo --location=${REGION} &>/dev/null; then
        log_warn "Repository govsight-repo already exists"
    else
        gcloud artifacts repositories create govsight-repo \
            --repository-format=docker \
            --location=${REGION} \
            --description="GovSight container images"
    fi
    
    gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
}

# Create Cloud SQL instance
create_cloud_sql() {
    log_info "Creating Cloud SQL instance..."
    
    if gcloud sql instances describe govsight-db &>/dev/null; then
        log_warn "Cloud SQL instance govsight-db already exists"
    else
        DB_ROOT_PASSWORD=$(openssl rand -base64 32)
        
        gcloud sql instances create govsight-db \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region=${REGION} \
            --root-password=${DB_ROOT_PASSWORD}
        
        log_info "Created Cloud SQL instance with root password: ${DB_ROOT_PASSWORD}"
        log_warn "SAVE THIS PASSWORD - it won't be shown again!"
    fi
    
    # Create database
    if gcloud sql databases describe govsight_primary --instance=govsight-db &>/dev/null; then
        log_warn "Database govsight_primary already exists"
    else
        gcloud sql databases create govsight_primary --instance=govsight-db
    fi
    
    # Create user
    DB_USER_PASSWORD=$(openssl rand -base64 32)
    
    if gcloud sql users list --instance=govsight-db --filter="name=govsight_user" --format="value(name)" | grep -q "govsight_user"; then
        log_warn "User govsight_user already exists"
    else
        gcloud sql users create govsight_user \
            --instance=govsight-db \
            --password=${DB_USER_PASSWORD}
        
        log_info "Created database user with password: ${DB_USER_PASSWORD}"
        log_warn "SAVE THIS PASSWORD - it won't be shown again!"
    fi
    
    # Get connection name
    CONNECTION_NAME=$(gcloud sql instances describe govsight-db --format="value(connectionName)")
    log_info "Cloud SQL connection name: ${CONNECTION_NAME}"
}

# Create GCS bucket
create_storage_bucket() {
    log_info "Creating Cloud Storage bucket..."
    
    BUCKET_NAME="${PROJECT_ID}-documents"
    
    if gsutil ls -b gs://${BUCKET_NAME} &>/dev/null; then
        log_warn "Bucket ${BUCKET_NAME} already exists"
    else
        gsutil mb -l ${REGION} gs://${BUCKET_NAME}
        gsutil versioning set on gs://${BUCKET_NAME}
        
        log_info "Created bucket: gs://${BUCKET_NAME}"
    fi
}

# Create BigQuery dataset
create_bigquery_dataset() {
    log_info "Creating BigQuery dataset..."
    
    if bq ls -d ${PROJECT_ID}:govsight_analytics &>/dev/null; then
        log_warn "Dataset govsight_analytics already exists"
    else
        bq mk -d \
            --location=${REGION} \
            --description="GovSight Analytics Dataset" \
            ${PROJECT_ID}:govsight_analytics
        
        log_info "Created BigQuery dataset: govsight_analytics"
    fi
}

# Setup secrets (interactive)
setup_secrets() {
    log_info "Setting up Secret Manager..."
    
    read -p "Enter OpenAI API Key (or press Enter to skip): " OPENAI_KEY
    if [ ! -z "$OPENAI_KEY" ]; then
        echo -n "$OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=- || \
            echo -n "$OPENAI_KEY" | gcloud secrets versions add OPENAI_API_KEY --data-file=-
    fi
    
    read -p "Enter Admin Password (or press Enter to skip): " ADMIN_PASS
    if [ ! -z "$ADMIN_PASS" ]; then
        echo -n "$ADMIN_PASS" | gcloud secrets create ADMIN_PASSWORD --data-file=- || \
            echo -n "$ADMIN_PASS" | gcloud secrets versions add ADMIN_PASSWORD --data-file=-
    fi
    
    read -p "Enter FRED API Key (or press Enter to skip): " FRED_KEY
    if [ ! -z "$FRED_KEY" ]; then
        echo -n "$FRED_KEY" | gcloud secrets create FRED_API_KEY --data-file=- || \
            echo -n "$FRED_KEY" | gcloud secrets versions add FRED_API_KEY --data-file=-
    fi
    
    read -p "Enter BEA API Key (or press Enter to skip): " BEA_KEY
    if [ ! -z "$BEA_KEY" ]; then
        echo -n "$BEA_KEY" | gcloud secrets create BEA_API_KEY --data-file=- || \
            echo -n "$BEA_KEY" | gcloud secrets versions add BEA_API_KEY --data-file=-
    fi
    
    log_info "Secrets configured (you can add more later)"
}

# Print summary
print_summary() {
    echo ""
    log_info "GCP Setup Complete!"
    echo ""
    log_info "Next steps:"
    echo "  1. Review and save all passwords shown above"
    echo "  2. Update DATABASE_URL secret with connection string"
    echo "  3. Run './scripts/deploy.sh' to deploy the application"
    echo "  4. Configure custom domains with 'gcloud run domain-mappings create'"
    echo ""
    log_info "Project: ${PROJECT_ID}"
    log_info "Region: ${REGION}"
    log_info "Cloud SQL: govsight-db"
    log_info "Artifact Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/govsight-repo"
    echo ""
}

# Main setup flow
main() {
    log_info "Starting GovSight GCP Setup"
    log_info "Project: ${PROJECT_ID}"
    log_info "Region: ${REGION}"
    echo ""
    
    create_project
    enable_apis
    create_artifact_registry
    create_cloud_sql
    create_storage_bucket
    create_bigquery_dataset
    setup_secrets
    print_summary
}

# Run main
main
