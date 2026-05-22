# DESIGN.md — Cost Janitor: Hardening, Scale & Production

## Multi-Cloud Reality

Adding GCP without rewriting the core requires a provider abstraction layer.

Module boundaries:
- core/models.py — Finding dataclass, provider-agnostic
- core/base_scanner.py — Abstract BaseScanner class
- providers/aws/scanner.py — AWSScanner using boto3
- providers/gcp/scanner.py — GCPScanner using google-cloud-compute
- providers/azure/scanner.py — AzureScanner, plug in later

Each provider maps its API response to a common Finding object.
Adding GCP means writing GCPScanner only, zero changes to core.

## Permissions

--dry-run IAM policy (read-only):

{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeVolumes",
      "ec2:DescribeInstances",
      "ec2:DescribeAddresses",
      "ec2:DescribeTags",
      "sts:GetCallerIdentity"
    ],
    "Resource": "*"
  }]
}

--delete mode adds ec2:DeleteVolume, ec2:TerminateInstances, ec2:ReleaseAddress scoped to tagged resources only.

## Safety Nets

Failure mode 1: Engineer stops instance at 11 PM for patching. Janitor runs at 2 AM and terminates it. Fix: require Janitor=approved tag before auto-termination. Send alert 24 hours before deletion.

Failure mode 2: DBA detaches EBS volume for snapshot. Janitor sees available state and deletes it. Data loss. Fix: never delete volume unattached less than 7 days. Skip if snapshot created in last 24 hours.

## Observability

Metric: OrphansFound — Source: Janitor scan — Alert: more than 0 for 3 consecutive scans
Metric: EstimatedMonthlyWasteUSD — Source: report.json — Alert: above 200 dollars
Metric: ScanDurationSeconds — Source: Janitor timing — Alert: above 120 seconds
Metric: DeleteActionsExecuted — Source: Janitor delete path — Alert: any value
Metric: ProtectedSkipCount — Source: Janitor delete path — Alert: spike above 10

All metrics published to CloudWatch under namespace CostJanitor.

## What I Did Not Build

Multi-account AWS Organizations support, GCP and Azure scanners, Slack notifications, historical trending with Athena, and Terraform state drift detection were left out to stay within scope. Module boundaries for multi-cloud are designed above and implementation is the next step.