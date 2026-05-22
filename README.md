# NimbusKart DevOps Assignment

## Overview

This project provisions NimbusKart staging infrastructure on LocalStack using Terraform, includes a Python Cost Janitor script that detects orphaned AWS resources, and a GitHub Actions workflow that runs cost hygiene checks on every pull request.

## How to run locally

git clone https://github.com/deeprathod2308-cmd/nimbuskart-devops.git
cd nimbuskart-devops
docker run --rm -d -p 4566:4566 --name localstack localstack/localstack:3.4
pip install terraform-local
cd terraform
tflocal init
tflocal apply -auto-approve
cd ..
pip install -r janitor/requirements.txt
python janitor/janitor.py --dry-run --endpoint-url http://localhost:4566

## Architecture

LocalStack (Docker) → tflocal apply → VPC, EC2 x2, S3, orphan EBS → janitor.py --dry-run → report.json + report.md → GitHub Actions uploads artifacts

Terraform layout:
terraform/main.tf
terraform/variables.tf
terraform/outputs.tf
terraform/modules/network/

Janitor scans:
EBS volumes in available state
EC2 instances stopped more than 14 days
Elastic IPs not associated with any instance
Resources missing required tags

## Decisions and deviations

- SSH CIDR changed from 0.0.0.0/0 to 10.0.0.0/8 because exposing SSH globally is a critical security risk
- Added S3 public access block because logs bucket should never be publicly readable
- dry-run is default flag because destructive default would be dangerous
- EIP age reported as 0 because AWS does not return allocation timestamp in describe-addresses

## Trade-offs

With one more week I would add multi-account AWS Organizations support, GCP provider, Slack notifications, historical trending with S3 and Athena, and Terraform state drift detection.

## AI usage disclosure

Used Claude to scaffold boilerplate Terraform module structure and GitHub Actions YAML syntax. Claude initially suggested terraform-local in CI without pinning the pip version which caused a flaky install. Fixed by adding explicit version pin. Wrote janitor.py core scanning logic manually because EC2 StateTransitionReason parsing is quirky and I wanted to own that logic and test it directly.

 . .