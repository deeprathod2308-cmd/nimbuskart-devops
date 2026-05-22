# Submission — DevOps Engineer Assignment

**Candidate name:** Dipsinh Rathod
**Email:** deeprathod2308@gmail.com
**Date submitted:** 22-05-2026
**Hours spent (approximate):** 8

## Deliverables checklist

- [x] Part A: Terraform code under /terraform applies cleanly on LocalStack
- [x] Part A: terraform validate and terraform fmt -check both pass
- [x] Part B: Janitor script runs in --dry-run mode and produces report.json
- [x] Part B: GitHub Actions workflow runs green on a fresh PR
- [x] Part B: --delete mode respects Protected=true tag
- [x] Part C: DESIGN.md is present and within 2 pages

## Walkthrough video

Link: https://www.loom.com/share/c222040233144bd8bfd51d8eab311a68
Length: 5 minutes

## Sample report

Path: samples/report.example.json

## Known limitations

- EIP age shown as 0 because AWS does not expose allocation timestamp
- Multi-account scanning not implemented
- GCP and Azure providers designed but not implemented

## AI usage disclosure

Used Claude to scaffold boilerplate Terraform module structure and GitHub Actions YAML syntax. Claude initially suggested terraform-local in CI without pinning the pip version which caused a flaky install. Fixed by adding explicit version pin. Wrote janitor.py core scanning logic manually because EC2 StateTransitionReason parsing is quirky and I wanted to own that logic and test it directly.