# GCP Integration Testing Plan

## Overview
This document provides end-to-end testing scenarios for Phase 3 Google Cloud Platform integration. Execute these tests after configuring GCP credentials to verify all cloud features work correctly.

## Prerequisites
Before testing, ensure:
1. `GOOGLE_CLOUD_PROJECT` environment variable is set
2. Google Cloud service account credentials are configured
3. Required GCP APIs are enabled (Storage, BigQuery)
4. Both workflows are running (GovSight App, PBB API Backend)

## Test Scenarios

### Scenario 1: Document Archive Upload & Retrieval

**Test 1.1: Upload Financial Report to GCS**
```bash
# Create sample report
echo "Monthly Financial Report - October 2025" > /tmp/monthly_report.pdf

# Upload via Archive API
curl -X POST "http://localhost:8000/api/archive/report?report_type=monthly_financial" \
  -F "file=@/tmp/monthly_report.pdf"

# Expected: 200 OK with upload confirmation
```

**Test 1.2: Upload Budget Export**
```bash
# Create sample CSV export
echo "Department,Budget,Actual\nPolice,500000,480000\nFire,400000,395000" > /tmp/budget_export.csv

# Upload via Archive API
curl -X POST "http://localhost:8000/api/archive/export?export_type=budget_analysis" \
  -F "file=@/tmp/budget_export.csv"

# Expected: 200 OK with upload confirmation
```

**Test 1.3: Search Archived Documents**
```bash
# Search reports archive
curl "http://localhost:8000/api/archive/search/reports"

# Expected: JSON array of uploaded documents with metadata
```

**Test 1.4: Retrieve Document**
```bash
# Get document by name (use actual blob name from search results)
curl "http://localhost:8000/api/archive/retrieve/reports?blob_name=monthly_report.pdf"

# Expected: File download
```

**Test 1.5: Generate Download URL**
```bash
# Create temporary signed URL
curl "http://localhost:8000/api/archive/download-url/reports?blob_name=monthly_report.pdf&expiration_minutes=30"

# Expected: JSON with temporary URL
```

**Test 1.6: Archive Statistics**
```bash
# Get archive stats
curl "http://localhost:8000/api/archive/stats"

# Expected: JSON with bucket statistics (file count, total size)
```

### Scenario 2: BigQuery Data Pipeline

**Test 2.1: Manual Pipeline Execution**
```python
# Run in Python environment
from modules.cloud_services.data_pipeline import MunicipalDataPipeline

pipeline = MunicipalDataPipeline()

# Sync GL transactions
result = pipeline.sync_gl_transactions(incremental=False)
print(f"GL Sync: {result}")

# Sync payroll data
result = pipeline.sync_payroll_data()
print(f"Payroll Sync: {result}")

# Sync audit logs
result = pipeline.sync_audit_logs()
print(f"Audit Sync: {result}")

# Expected: Success messages for each sync operation
```

**Test 2.2: Verify BigQuery Tables**
```python
from modules.cloud_services.bigquery_connector import BigQueryConnector

bq = BigQueryConnector()

# List tables
tables = bq.list_tables()
print("BigQuery Tables:", tables)

# Expected: gl_transactions, payroll_data, audit_logs, utility_records
```

**Test 2.3: Query Analytics Views**
```python
# Revenue trends
df = bq.execute_query("""
    SELECT * FROM `{project}.{dataset}.revenue_trends`
    ORDER BY month DESC
    LIMIT 10
""")
print("Revenue Trends:", df.head())

# Expense analysis
df = bq.execute_query("""
    SELECT * FROM `{project}.{dataset}.expense_analysis`
    WHERE month = FORMAT_DATE('%Y-%m', CURRENT_DATE())
""")
print("Expense Analysis:", df.head())

# Expected: Dataframes with analytics data
```

### Scenario 3: MantisAI Cloud Integration

**Test 3.1: Cloud Document Search via AI**
Open GovSight App → Navigate to Mantis module → Start chat:

```
User: "Search for financial reports uploaded in the last week"

Expected Response:
- MantisAI invokes search_cloud_documents tool
- Returns table of documents with names, sizes, dates
- Shows metadata about search results
```

**Test 3.2: BigQuery Analytics via AI**
```
User: "Show me revenue trends from BigQuery for the last quarter"

Expected Response:
- MantisAI invokes query_bigquery_analytics tool
- Returns chart/table with revenue trend data
- Includes analysis message with key insights
```

**Test 3.3: Combined Analysis**
```
User: "Compare my local budget data with BigQuery historical trends"

Expected Response:
- MantisAI uses both local database queries and BigQuery analytics
- Provides comparative analysis
- Charts showing trends
```

**Test 3.4: Document Discovery**
```
User: "Find all budget exports in cloud storage from 2024"

Expected Response:
- Searches exports archive with date filter
- Returns filtered list of documents
- Provides download guidance
```

### Scenario 4: Error Handling & Graceful Degradation

**Test 4.1: Invalid GCP Credentials**
```bash
# Temporarily set invalid project
export GOOGLE_CLOUD_PROJECT="invalid-project-id"

# Restart workflows
# Try archive upload
curl -X POST "http://localhost:8000/api/archive/report?report_type=test" \
  -F "file=@/tmp/test.pdf"

# Expected: 503 error with clear message about configuration
```

**Test 4.2: Network Failure**
```bash
# Simulate network issue (requires network tools)
# Try BigQuery query during outage

# Expected: Graceful error message, no application crash
```

**Test 4.3: No GCP Configuration**
```bash
# Unset GCP project
unset GOOGLE_CLOUD_PROJECT

# Restart workflows
# Check MantisAI tools

# Expected: GCP tools not registered, app works without cloud features
```

### Scenario 5: Performance & Scaling

**Test 5.1: Large File Upload**
```bash
# Create 10MB file
dd if=/dev/zero of=/tmp/large_report.pdf bs=1M count=10

# Upload to GCS
curl -X POST "http://localhost:8000/api/archive/report?report_type=annual_budget" \
  -F "file=@/tmp/large_report.pdf"

# Expected: Successful upload with reasonable time (<30s)
```

**Test 5.2: Bulk Data Sync**
```python
# Sync large dataset
pipeline = MunicipalDataPipeline()

# Full GL sync (all historical data)
result = pipeline.sync_gl_transactions(
    incremental=False,
    days_back=365
)

# Expected: Successful sync with progress logging
```

**Test 5.3: Concurrent BigQuery Queries**
```python
import concurrent.futures

def run_query(query_type):
    bq = BigQueryConnector()
    query = f"SELECT * FROM `{bq.project_id}.{bq.dataset_id}.{query_type}` LIMIT 100"
    return bq.execute_query(query)

# Run 5 queries concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(run_query, 'revenue_trends'),
        executor.submit(run_query, 'expense_analysis'),
        executor.submit(run_query, 'compliance_report'),
        executor.submit(run_query, 'gl_transactions'),
        executor.submit(run_query, 'audit_logs')
    ]
    results = [f.result() for f in futures]

# Expected: All queries succeed without conflicts
```

## Validation Checklist

After completing all scenarios, verify:

- [ ] All document types (reports, exports, backups) upload successfully
- [ ] Document search returns accurate results with metadata
- [ ] Signed URLs work and expire correctly
- [ ] BigQuery tables contain synced data from all databases
- [ ] Analytics views return meaningful insights
- [ ] MantisAI correctly invokes GCP tools when available
- [ ] Error messages are clear and actionable
- [ ] Application remains stable when GCP unavailable
- [ ] Performance meets expectations (<5s for queries, <30s for uploads)
- [ ] Audit logs capture all GCP operations

## Troubleshooting

### Issue: 503 errors for cloud features
**Solution**: Verify GOOGLE_CLOUD_PROJECT is set and credentials are valid

### Issue: BigQuery queries fail
**Solution**: 
1. Check dataset exists: `bq ls`
2. Verify tables: `bq ls municipal_analytics`
3. Run pipeline sync to populate data

### Issue: Document upload fails
**Solution**:
1. Check bucket exists in GCS console
2. Verify service account has Storage Admin role
3. Review PBB API Backend logs for errors

### Issue: MantisAI doesn't show cloud tools
**Solution**:
1. Verify GCP is configured (check logs for "GCP not configured")
2. Restart GovSight App workflow
3. Check MantisAI initialization logs

## Success Criteria

Phase 3 GCP integration is fully operational when:

1. **Document Archive**: Can upload, search, retrieve all document types
2. **BigQuery Analytics**: Pipeline syncs data, views return insights
3. **MantisAI Integration**: AI can query both GCS and BigQuery
4. **Graceful Degradation**: App works without GCP configuration
5. **Performance**: All operations complete within expected timeframes
6. **Reliability**: No crashes or data loss under normal/error conditions

## Next Steps After Testing

1. Configure production GCP project with appropriate quotas
2. Set up automated pipeline scheduling (hourly/daily syncs)
3. Configure backup retention policies
4. Enable BigQuery cost controls and query optimization
5. Deploy to production with monitored rollout
