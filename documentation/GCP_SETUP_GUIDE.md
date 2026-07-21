# Google Cloud Platform Setup Guide
## GovSight Financial Intelligence Platform

This guide walks you through setting up Google Cloud Platform integration for the GovSight platform, enabling enterprise-grade document archiving, data analytics, and AI capabilities.

## Overview

The GovSight platform integrates with four core GCP services:
1. **Google Cloud Storage (GCS)** - Document archiving and file management
2. **BigQuery** - Data warehousing and analytics
3. **Vertex AI** - AI/ML model deployment and predictions
4. **Google Cloud Secret Manager** - Centralized credential management

All GCP features use **lazy initialization** - the application works perfectly without GCP configuration, but gains powerful cloud capabilities when configured.

## Prerequisites

- Google Cloud Platform account
- `gcloud` CLI installed and configured
- Project billing enabled
- Basic understanding of GCP IAM and permissions

## Step 1: Create GCP Project

```bash
gcloud projects create govsight-production --name="GovSight Financial Platform"

gcloud config set project govsight-production

gcloud auth application-default login
```

## Step 2: Enable Required APIs

```bash
gcloud services enable storage.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

## Step 3: Set Up Authentication

### For Development (Local/Replit)

```bash
gcloud auth application-default login
```

This creates Application Default Credentials (ADC) that the SDK automatically uses.

### For Production (Cloud Run, GKE, etc.)

Create a service account with required permissions:

```bash
gcloud iam service-accounts create govsight-app \
    --display-name="GovSight Application Service Account"

gcloud projects add-iam-policy-binding govsight-production \
    --member="serviceAccount:govsight-app@govsight-production.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding govsight-production \
    --member="serviceAccount:govsight-app@govsight-production.iam.gserviceaccount.com" \
    --role="roles/bigquery.admin"

gcloud projects add-iam-policy-binding govsight-production \
    --member="serviceAccount:govsight-app@govsight-production.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding govsight-production \
    --member="serviceAccount:govsight-app@govsight-production.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud iam service-accounts keys create govsight-key.json \
    --iam-account=govsight-app@govsight-production.iam.gserviceaccount.com
```

Set the environment variable to point to the key:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/govsight-key.json"
```

## Step 4: Create Cloud Storage Buckets

Create four buckets for organized document management:

```bash
export PROJECT_ID="govsight-production"
export REGION="us-central1"

gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://govsight-reports/
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://govsight-exports/
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://govsight-backups/
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://govsight-documents/
```

### Configure Lifecycle Policies (Optional but Recommended)

Create a lifecycle policy file `lifecycle-90days.json`:

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
```

Apply to backup bucket:

```bash
gsutil lifecycle set lifecycle-90days.json gs://govsight-backups/
```

### Enable Versioning for Critical Buckets

```bash
gsutil versioning set on gs://govsight-reports/
gsutil versioning set on gs://govsight-backups/
```

## Step 5: Create BigQuery Dataset

```bash
bq mk -d \
    --location=US \
    --description="GovSight Financial Analytics Data Warehouse" \
    $PROJECT_ID:govsight_analytics
```

### Create Tables

The application will automatically create tables when the data pipeline runs for the first time. Tables include:

- `gl_transactions` - General ledger historical data
- `budget_data` - Multi-year budget allocations
- `audit_logs` - Security and compliance audit trail
- `payroll_summary` - Employee compensation data
- `utility_billing` - Utility service billing records

### Create Analytics Views

```sql
CREATE VIEW `govsight_analytics.revenue_trends` AS
SELECT 
    DATE_TRUNC(transaction_date, MONTH) as month,
    account_type,
    SUM(amount) as total_revenue,
    COUNT(*) as transaction_count
FROM `govsight_analytics.gl_transactions`
WHERE account_type = 'Revenue'
GROUP BY month, account_type
ORDER BY month DESC;

CREATE VIEW `govsight_analytics.expense_analysis` AS
SELECT 
    department,
    account_category,
    SUM(amount) as total_expenses,
    AVG(amount) as avg_transaction
FROM `govsight_analytics.gl_transactions`
WHERE account_type = 'Expense'
GROUP BY department, account_category;

CREATE VIEW `govsight_analytics.compliance_summary` AS
SELECT 
    DATE_TRUNC(timestamp, DAY) as date,
    event_type,
    severity,
    COUNT(*) as event_count
FROM `govsight_analytics.audit_logs`
GROUP BY date, event_type, severity
ORDER BY date DESC;
```

## Step 6: Configure Secret Manager

Store sensitive credentials in Secret Manager:

```bash
echo -n "your-admin-password" | gcloud secrets create ADMIN_PASSWORD \
    --data-file=- \
    --replication-policy="automatic"

echo -n "your-bls-api-key" | gcloud secrets create BLS_API_KEY \
    --data-file=- \
    --replication-policy="automatic"

echo -n "your-fred-api-key" | gcloud secrets create FRED_API_KEY \
    --data-file=- \
    --replication-policy="automatic"
```

Grant access to the service account:

```bash
gcloud secrets add-iam-policy-binding ADMIN_PASSWORD \
    --member="serviceAccount:govsight-app@govsight-production.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## Step 7: Configure Environment Variables

Set the required environment variable to enable GCP integration:

### For Replit
Add to Replit Secrets:
- `GOOGLE_CLOUD_PROJECT` = `govsight-production`
- `PREFER_GCP_SECRETS` = `true` (for production)

### For Local Development
Add to `.env` file:
```bash
GOOGLE_CLOUD_PROJECT=govsight-production
PREFER_GCP_SECRETS=false
```

### For Production Deployment
Set environment variables in your deployment platform:
```bash
export GOOGLE_CLOUD_PROJECT=govsight-production
export PREFER_GCP_SECRETS=true
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/govsight-key.json
```

## Step 8: Configure Vertex AI (Optional - For AI/ML Features)

Vertex AI enables deployment of custom AI/ML models for advanced municipal analytics, revenue forecasting, and predictive insights.

### Enable Vertex AI Model Deployment

The application automatically detects Vertex AI availability. No additional configuration is required beyond enabling the API and setting IAM permissions (completed in Steps 2-3).

### Vertex AI Features in MantisAI

When Vertex AI is configured, MantisAI gains three new capabilities:

1. **Deploy AI Models** - Upload and deploy custom ML models to Vertex AI endpoints
2. **List Models** - View all deployed models with their status and metadata
3. **Get Predictions** - Send prediction requests to deployed models

### Example: Deploy a Revenue Forecasting Model

```python
from modules.cloud_services.vertex_ai_connector import VertexAIConnector

vertex = VertexAIConnector(project_id="govsight-production", location="us-central1")

deployment = vertex.deploy_model(
    model_display_name="municipal_revenue_forecast",
    model_artifact_uri="gs://govsight-models/revenue_model/",
    serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-0:latest"
)

print(f"Model deployed to endpoint: {deployment['endpoint_name']}")
```

### Using Vertex AI Through MantisAI Chat

Once configured, users can interact with Vertex AI directly through the MantisAI chat interface:

```
User: "Deploy the revenue forecasting model from gs://govsight-models/revenue_model/"
MantisAI: [Deploys model and returns endpoint information]

User: "List all my AI models"
MantisAI: [Shows table of deployed models with status]

User: "Get a prediction for next quarter's sales tax revenue"
MantisAI: [Sends prediction request to deployed model and returns results]
```

## Step 9: Test the Integration

### Test GCS Connection

```python
from modules.cloud_services.gcs_connector import GCSConnector

connector = GCSConnector(project_id="govsight-production")
print(connector.test_connection())
```

### Test BigQuery Connection

```python
from modules.cloud_services.bigquery_connector import BigQueryConnector

bq = BigQueryConnector(project_id="govsight-production")
print(bq.test_connection())
```

### Test Vertex AI Connection

```python
from modules.cloud_services.vertex_ai_connector import VertexAIConnector

vertex = VertexAIConnector(project_id="govsight-production")
if vertex.is_configured():
    models = vertex.list_models()
    print(f"Found {len(models) if models else 0} models in Vertex AI")
else:
    print(f"Vertex AI not configured: {vertex.get_config_error()}")
```

### Test Archive API

Start the application and test the Archive API:

```bash
curl http://localhost:8000/archive/stats
```

Expected response:
```json
{
  "reports": {
    "total_files": 0,
    "total_size_bytes": 0,
    "bucket_name": "govsight-reports"
  },
  "exports": {
    "total_files": 0,
    "total_size_bytes": 0,
    "bucket_name": "govsight-exports"
  },
  ...
}
```

## Step 9: Run Initial Data Pipeline Sync

The data pipeline syncs operational databases to BigQuery:

```bash
cd /path/to/govsight
python -m modules.cloud_services.data_pipeline
```

This will:
1. Connect to all operational databases (GL, Payroll, Utility, Asset, Permits)
2. Extract data with proper schema mapping
3. Transform and clean data
4. Load into BigQuery tables
5. Create analytics views

Monitor the output for any errors.

## Step 10: Verify Data in BigQuery

```bash
bq query --use_legacy_sql=false \
'SELECT COUNT(*) as total_transactions FROM `govsight_analytics.gl_transactions`'

bq query --use_legacy_sql=false \
'SELECT * FROM `govsight_analytics.revenue_trends` LIMIT 10'
```

## Archive API Usage Examples

### Upload a Financial Report

```bash
curl -X POST "http://localhost:8000/archive/report" \
  -F "file=@balance_sheet_2024.pdf" \
  -F "report_type=balance_sheet" \
  -F 'metadata={"fiscal_year": "2024", "quarter": "Q1"}'
```

### Search Archives

```bash
curl "http://localhost:8000/archive/search?archive_type=reports&start_date=2024-01-01&end_date=2024-12-31"
```

### Generate Download URL

```bash
curl "http://localhost:8000/archive/download-url?archive_type=reports&blob_name=balance_sheet_2024.pdf&expiration_minutes=60"
```

### Get Storage Statistics

```bash
curl "http://localhost:8000/archive/stats"
```

## Monitoring and Maintenance

### Set Up Budget Alerts

```bash
gcloud billing budgets create \
    --billing-account=BILLING_ACCOUNT_ID \
    --display-name="GovSight Monthly Budget" \
    --budget-amount=100USD \
    --threshold-rule=percent=50 \
    --threshold-rule=percent=90
```

### Monitor Storage Usage

```bash
gsutil du -sh gs://govsight-reports/
gsutil du -sh gs://govsight-backups/
```

### Review BigQuery Costs

```sql
SELECT
  DATE(creation_time) as date,
  COUNT(*) as query_count,
  SUM(total_bytes_processed) / POW(10, 12) as total_tb_processed
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY date
ORDER BY date DESC;
```

### Automate Backups to GCS

Create a cron job to automatically archive database backups:

```bash
0 2 * * * /usr/bin/python3 /path/to/backup_and_archive.py
```

`backup_and_archive.py`:
```python
from modules.database.backup_manager import BackupManager
from modules.cloud_services.document_archive import DocumentArchive

backup_mgr = BackupManager()
archive = DocumentArchive()

backup_path = backup_mgr.create_backup("caselle_gl0_mock.db", backup_type="full")
archive.archive_database_backup(backup_path, "caselle_gl0", metadata={"automated": True})
```

## Troubleshooting

### Error: "GCP project ID not configured"

**Solution**: Set the `GOOGLE_CLOUD_PROJECT` environment variable:
```bash
export GOOGLE_CLOUD_PROJECT=govsight-production
```

### Error: "Permission denied"

**Solution**: Verify service account has required roles:
```bash
gcloud projects get-iam-policy govsight-production \
    --flatten="bindings[].members" \
    --format="table(bindings.role)" \
    --filter="bindings.members:govsight-app@govsight-production.iam.gserviceaccount.com"
```

### Error: "Bucket already exists"

**Solution**: Either use a different bucket name or verify you own the bucket:
```bash
gsutil ls -p govsight-production
```

### Data Pipeline Sync Failures

**Check logs**:
```bash
tail -f logs/data_pipeline.log
```

**Common issues**:
1. Database connection timeout - Check network connectivity
2. Schema mismatch - Review BigQuery table schemas
3. Rate limiting - Add exponential backoff

### BigQuery Query Errors

**View schema**:
```bash
bq show govsight_analytics.gl_transactions
```

**Check for duplicates**:
```sql
SELECT transaction_id, COUNT(*) as count
FROM `govsight_analytics.gl_transactions`
GROUP BY transaction_id
HAVING count > 1;
```

## Cost Optimization Tips

1. **Use lifecycle policies** to automatically delete old backups after 90 days
2. **Enable versioning** only for critical buckets (reports, backups)
3. **Use Standard storage class** for frequently accessed data
4. **Use Nearline/Coldline** for archives accessed less than once per month
5. **Partition BigQuery tables** by date for query cost reduction
6. **Use clustering** on frequently filtered columns (department, account_type)
7. **Schedule data pipeline** during off-peak hours to reduce concurrent usage costs
8. **Set up query result caching** in BigQuery
9. **Use streaming inserts** sparingly (batch inserts are cheaper)
10. **Monitor and set budget alerts** to avoid surprises

## Security Best Practices

1. **Use service accounts** with minimum required permissions
2. **Rotate service account keys** every 90 days
3. **Enable audit logging** for all GCS buckets and BigQuery datasets
4. **Use VPC Service Controls** for production environments
5. **Encrypt data at rest** using customer-managed encryption keys (CMEK)
6. **Use signed URLs** with short expiration times for file downloads
7. **Implement IAM conditions** for time-based or IP-based access
8. **Review access logs** regularly for suspicious activity
9. **Enable bucket versioning** to prevent accidental deletions
10. **Use Secret Manager** for all sensitive credentials

## Next Steps

1. Configure scheduled BigQuery queries for automated reporting
2. Set up Cloud Functions for event-driven processing
3. Integrate Cloud Monitoring for alerting
4. Configure Cloud Logging for centralized log management
5. Implement data retention policies for compliance
6. Set up Cloud Scheduler for automated data pipeline runs
7. Configure VPC Service Controls for enhanced security
8. Integrate Cloud DLP for sensitive data protection

## Support

For questions or issues:
- Review application logs in `logs/` directory
- Check GCP console for service status
- Review BigQuery job history for query failures
- Contact GCP support for infrastructure issues

## Additional Resources

- [Google Cloud Storage Documentation](https://cloud.google.com/storage/docs)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)
- [Cost Optimization Guide](https://cloud.google.com/cost-management/docs/best-practices)
