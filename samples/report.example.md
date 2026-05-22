# Cost Janitor Report

**Scan time:** 2026-01-15T10:00:00Z
**Account:** 000000000000
**Region:** us-east-1

## Summary

| Metric | Value |
|--------|-------|
| Total orphans found | 3 |
| Estimated monthly waste | $19.24 |

## Findings

| Resource ID | Type | Reason | Age (days) | Est. Cost/mo |
|-------------|------|--------|-----------|-------------|
| vol-0abc123def456 | ebs_volume | unattached | 21 | $1.60 |
| i-0def789abc123 | ec2_instance | stopped for 18 days | 18 | $7.59 |
| eipalloc-0123456abc | elastic_ip | not associated with any instance | 0 | $3.65 |