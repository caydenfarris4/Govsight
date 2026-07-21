# GovSight Production Deployment Guide
## Google Cloud Run Deployment with Custom Domains

This guide walks you through deploying GovSight to Google Cloud Run with custom domain support for multi-city deployments (citya.govsight.net, cityb.govsight.net, etc.).

## Prerequisites

- Google Cloud Platform account with billing enabled
- `gcloud` CLI installed and configured
- Docker installed locally (for testing)
- Domain ownership of govsight.net with DNS management access
- GovSight codebase ready for deployment

## Architecture Overview

```
Internet
    ↓
Cloud Load Balancer (handles SSL/TLS)
    ↓
Cloud Run Service (auto-scaling containers)
    ↓
┌─────────────────────────────────────────────┐
│  GovSight Streamlit App                     │
│  - Subdomain detection (citya, cityb, etc.) │
│  - Cloud SQL connection                     │
│  - GCS, BigQuery, Vertex AI integration     │
└─────────────────────────────────────────────┘
    ↓
Cloud SQL (PostgreSQL) - Persistent database
```

## Step 1: Prepare Your GCP Project

### Create and Configure Project

```bash
# Set your project variables
export PROJECT_ID="govsight-production"
export REGION="us-central1"
export SERVICE_NAME="govsight-app"

# Create project (if needed)
gcloud projects create $PROJECT_ID --name="GovSight Production"

# Set as active project
gcloud config set project $PROJECT_ID

# Enable required APIs
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
```

## Step 2: Set Up Cloud SQL Database

GovSight uses SQLite in development, but Cloud Run is stateless. We'll use Cloud SQL PostgreSQL for production.

### Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create govsight-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --root-password=$(openssl rand -base64 32)

# Create database
gcloud sql databases create govsight_primary --instance=govsight-db

# Create user
gcloud sql users create govsight_user \
    --instance=govsight-db \
    --password=$(openssl rand -base64 32)

# Get connection name (save this!)
gcloud sql instances describe govsight-db --format="value(connectionName)"
# Output: govsight-production:us-central1:govsight-db
```

### Store Database Credentials in Secret Manager

```bash
# Store DB connection string
echo "postgresql://govsight_user:YOUR_PASSWORD@/govsight_primary?host=/cloudsql/govsight-production:us-central1:govsight-db" | \
    gcloud secrets create DATABASE_URL --data-file=-

# Store other secrets
echo -n "YOUR_OPENAI_API_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
echo -n "YOUR_ADMIN_PASSWORD" | gcloud secrets create ADMIN_PASSWORD --data-file=-
echo -n "YOUR_FRED_API_KEY" | gcloud secrets create FRED_API_KEY --data-file=-
echo -n "YOUR_BEA_API_KEY" | gcloud secrets create BEA_API_KEY --data-file=-
```

## Step 3: Build and Push Container Image

### Create Artifact Registry Repository

```bash
# Create repository for Docker images
gcloud artifacts repositories create govsight-repo \
    --repository-format=docker \
    --location=$REGION \
    --description="GovSight container images"

# Configure Docker to use gcloud credentials
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### Build and Push Image

```bash
# Build the Docker image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/govsight-repo/${SERVICE_NAME}:latest .

# Test locally (optional)
docker run -p 8080:8080 \
    -e PORT=8080 \
    -e GOOGLE_CLOUD_PROJECT=$PROJECT_ID \
    ${REGION}-docker.pkg.dev/${PROJECT_ID}/govsight-repo/${SERVICE_NAME}:latest

# Push to Artifact Registry
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/govsight-repo/${SERVICE_NAME}:latest
```

## Step 4: Deploy to Cloud Run

### Initial Deployment

```bash
# Deploy with Cloud SQL connection
gcloud run deploy $SERVICE_NAME \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/govsight-repo/${SERVICE_NAME}:latest \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --add-cloudsql-instances=govsight-production:us-central1:govsight-db \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-secrets="DATABASE_URL=DATABASE_URL:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,ADMIN_PASSWORD=ADMIN_PASSWORD:latest,FRED_API_KEY=FRED_API_KEY:latest,BEA_API_KEY=BEA_API_KEY:latest" \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --concurrency=80 \
    --min-instances=1 \
    --max-instances=10
```

### Configure Service Account Permissions

```bash
# Get the Cloud Run service account
SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(spec.template.spec.serviceAccountName)")

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user"
```

## Step 5: Configure Custom Domain with Subdomains

### Map Custom Domain to Cloud Run

```bash
# Add domain mapping for each city subdomain
gcloud run domain-mappings create \
    --service=$SERVICE_NAME \
    --domain=citya.govsight.net \
    --region=$REGION

gcloud run domain-mappings create \
    --service=$SERVICE_NAME \
    --domain=cityb.govsight.net \
    --region=$REGION

gcloud run domain-mappings create \
    --service=$SERVICE_NAME \
    --domain=cityc.govsight.net \
    --region=$REGION

# Get the DNS records you need to add
gcloud run domain-mappings describe \
    --domain=citya.govsight.net \
    --region=$REGION
```

### Add DNS Records to Your Domain Registrar

After running the domain mapping commands, GCP will provide DNS records. Add these to your domain registrar:

**For each subdomain (citya, cityb, cityc):**

```
Type: A
Name: citya
Value: [IP address from gcloud command]
TTL: 3600

Type: AAAA
Name: citya
Value: [IPv6 address from gcloud command]
TTL: 3600
```

**SSL Certificate:**
Google Cloud automatically provisions and manages SSL/TLS certificates for your custom domains. This can take 15-60 minutes.

## Step 6: Multi-City Configuration

The application uses subdomain detection to determine which city's data to display. This is handled automatically by the `SubdomainManager` utility.

### How It Works

1. User visits `citya.govsight.net`
2. Streamlit app detects subdomain: "citya"
3. App loads city-specific configuration and data
4. Database queries filter by city identifier

### City Configuration

Create a city configuration file `configs/cities.json`:

```json
{
  "citya": {
    "name": "City A",
    "display_name": "City of Springfield",
    "database_prefix": "citya",
    "timezone": "America/New_York",
    "fiscal_year_start": "07-01",
    "contact_email": "finance@citya.gov"
  },
  "cityb": {
    "name": "City B",
    "display_name": "City of Riverside",
    "database_prefix": "cityb",
    "timezone": "America/Los_Angeles",
    "fiscal_year_start": "07-01",
    "contact_email": "finance@cityb.gov"
  }
}
```

## Step 7: Database Migration

Since Cloud Run uses Cloud SQL instead of SQLite, you'll need to migrate your schema and data.

### Export SQLite Data (Development)

```bash
# Export from SQLite to SQL dump
sqlite3 databases/caselle_gl0_mock.db .dump > migration.sql

# Convert SQLite syntax to PostgreSQL (you may need to adjust)
sed -i 's/AUTOINCREMENT/SERIAL/g' migration.sql
sed -i 's/INTEGER PRIMARY KEY/SERIAL PRIMARY KEY/g' migration.sql
```

### Import to Cloud SQL

```bash
# Connect to Cloud SQL
gcloud sql connect govsight-db --user=govsight_user

# In PostgreSQL prompt:
\i migration.sql
```

### Automated Migration Script

Use the included migration script:

```bash
python scripts/migrate_to_cloudsql.py \
    --sqlite-db=databases/caselle_gl0_mock.db \
    --cloudsql-connection=govsight-production:us-central1:govsight-db
```

## Step 8: CI/CD with Cloud Build

### Automated Deployments

Create a Cloud Build trigger for automatic deployments on git push:

```bash
# Connect your repository (GitHub, GitLab, etc.)
gcloud builds triggers create github \
    --repo-name=govsight \
    --repo-owner=YOUR_GITHUB_USERNAME \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml
```

The `cloudbuild.yaml` file handles:
1. Building Docker image
2. Pushing to Artifact Registry
3. Deploying to Cloud Run
4. Running database migrations

## Step 9: Monitoring and Logging

### Enable Cloud Monitoring

```bash
# Cloud Run automatically sends logs to Cloud Logging
# View logs:
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
    --limit=50 \
    --format=json

# Set up uptime checks
gcloud monitoring uptime create govsight-health-check \
    --display-name="GovSight Health Check" \
    --resource-type=uptime-url \
    --host=citya.govsight.net \
    --path=/health
```

### Create Alerting Policies

```bash
# Alert on high error rate
gcloud alpha monitoring policies create \
    --notification-channels=YOUR_NOTIFICATION_CHANNEL \
    --display-name="GovSight Error Rate" \
    --condition-threshold-value=10 \
    --condition-threshold-duration=300s
```

## Step 10: Testing Your Deployment

### Health Check

```bash
# Test the deployment
curl https://citya.govsight.net/health

# Expected response:
{
  "status": "healthy",
  "subdomain": "citya",
  "city": "City of Springfield",
  "database": "connected",
  "gcp_services": {
    "storage": "available",
    "bigquery": "available",
    "vertex_ai": "available"
  }
}
```

### Load Testing

```bash
# Install artillery for load testing
npm install -g artillery

# Run load test
artillery quick --count 100 --num 10 https://citya.govsight.net
```

## Cost Optimization

### Estimated Monthly Costs

| Service | Configuration | Est. Cost |
|---------|--------------|-----------|
| Cloud Run | 1-10 instances, 2GB RAM | $20-150/mo |
| Cloud SQL | db-f1-micro | $7-15/mo |
| Cloud Storage | 50GB + operations | $1-5/mo |
| BigQuery | 1TB queries/mo | $5/mo |
| Vertex AI | Pay per use | $0-50/mo |
| **Total** | | **$33-225/mo** |

### Cost Reduction Tips

1. **Use Cloud Run min-instances=0** for low-traffic periods (cold starts are ~2s)
2. **Cloud SQL automated backups** - set retention to 7 days
3. **Set BigQuery dataset expiration** to 90 days for old data
4. **Use Cloud Storage lifecycle policies** to archive old documents
5. **Enable Cloud CDN** for static assets

### Budget Alerts

```bash
# Set budget alert
gcloud billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="GovSight Monthly Budget" \
    --budget-amount=200USD \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90 \
    --threshold-rule=percent=100
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=100

# Common issues:
# 1. Port mismatch - ensure PORT env var is 8080
# 2. Missing secrets - verify secret access
# 3. Cloud SQL connection - check instance name
```

### Database Connection Errors

```bash
# Test Cloud SQL connection
gcloud sql connect govsight-db --user=govsight_user

# Verify Cloud Run has SQL client role
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.role:roles/cloudsql.client"
```

### Domain Not Working

```bash
# Check domain mapping status
gcloud run domain-mappings describe \
    --domain=citya.govsight.net \
    --region=$REGION

# Verify DNS propagation
dig citya.govsight.net

# Check SSL certificate status (can take 60 minutes)
gcloud run domain-mappings list --region=$REGION
```

### High Costs

```bash
# Analyze Cloud Run usage
gcloud logging read "resource.type=cloud_run_revision" \
    --format="table(timestamp, resource.labels.service_name, httpRequest.requestUrl)" \
    --limit=1000

# Check BigQuery costs
bq show --format=prettyjson -j PROJECT_ID:LOCATION.JOB_ID

# Review Cloud SQL metrics
gcloud sql operations list --instance=govsight-db
```

## Rollback Procedures

### Rollback to Previous Version

```bash
# List revisions
gcloud run revisions list --service=$SERVICE_NAME --region=$REGION

# Rollback to specific revision
gcloud run services update-traffic $SERVICE_NAME \
    --to-revisions=govsight-app-00042-xzy=100 \
    --region=$REGION
```

### Database Rollback

```bash
# Cloud SQL automated backups allow point-in-time recovery
gcloud sql backups list --instance=govsight-db

# Restore from backup
gcloud sql backups restore BACKUP_ID \
    --backup-instance=govsight-db \
    --backup-id=BACKUP_ID
```

## Security Best Practices

1. **Never commit secrets** - Use Secret Manager
2. **Enable VPC Connector** for private Cloud SQL access
3. **Use IAM conditions** for time-based access
4. **Enable Cloud Armor** for DDoS protection
5. **Implement Cloud Identity-Aware Proxy** for admin access
6. **Regular security scanning** with Container Analysis
7. **Enable audit logging** for all services
8. **Use Workload Identity** for service accounts
9. **Implement rate limiting** in application code
10. **Regular dependency updates** via Dependabot

## Maintenance Tasks

### Weekly
- Review error logs and address issues
- Check uptime and performance metrics
- Verify backup completion

### Monthly
- Review and optimize costs
- Update dependencies and security patches
- Test disaster recovery procedures
- Review access logs for suspicious activity

### Quarterly
- Load testing and capacity planning
- Security audit and penetration testing
- Review and update documentation
- Database performance tuning

## Next Steps

1. **Set up staging environment** - Duplicate setup for testing
2. **Implement blue-green deployments** - Zero-downtime updates
3. **Add Cloud CDN** - Improve global performance
4. **Configure Cloud Armor** - WAF and DDoS protection
5. **Set up Cloud Scheduler** - Automated tasks and reports
6. **Implement Workload Identity** - Enhanced security
7. **Add custom metrics** - Business-specific monitoring
8. **Configure log-based metrics** - Advanced alerting

## Support Resources

- **Cloud Run Documentation**: https://cloud.google.com/run/docs
- **Cloud SQL Documentation**: https://cloud.google.com/sql/docs
- **Domain Mapping Guide**: https://cloud.google.com/run/docs/mapping-custom-domains
- **GCP Support**: https://cloud.google.com/support
- **GovSight Repository**: [Your GitHub URL]

## Quick Reference Commands

```bash
# Deploy new version
./scripts/deploy.sh

# View logs
gcloud run services logs read govsight-app --region=us-central1 --limit=100

# Update environment variable
gcloud run services update govsight-app \
    --update-env-vars=NEW_VAR=value \
    --region=us-central1

# Scale instances
gcloud run services update govsight-app \
    --min-instances=2 \
    --max-instances=20 \
    --region=us-central1

# Add new city subdomain
gcloud run domain-mappings create \
    --service=govsight-app \
    --domain=newcity.govsight.net \
    --region=us-central1
```
