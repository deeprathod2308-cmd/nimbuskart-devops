import os
import json
import sys
import argparse
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from constants import (
    EBS_GP3_PER_GB_MONTH,
    EBS_GP2_PER_GB_MONTH,
    EBS_DEFAULT_SIZE_GB,
    EIP_UNATTACHED_PER_MONTH,
    EC2_DEFAULT_WASTE_PER_MONTH,
    UNTAGGED_WASTE_PER_MONTH,
    REQUIRED_TAGS,
)

def get_client(service, endpoint_url=None, region="us-east-1"):
    return boto3.client(
        service,
        region_name=region,
        endpoint_url=endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )

def tags_as_dict(tag_list):
    if not tag_list:
        return {}
    return {t["Key"]: t["Value"] for t in tag_list}

def is_protected(tags):
    return tags.get("Protected", "").lower() == "true"

def age_days(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days

def scan_unattached_ebs(ec2):
    findings = []
    try:
        response = ec2.describe_volumes(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )
        for vol in response.get("Volumes", []):
            tags = tags_as_dict(vol.get("Tags"))
            size = vol.get("Size", EBS_DEFAULT_SIZE_GB)
            vol_type = vol.get("VolumeType", "gp3")
            price = EBS_GP2_PER_GB_MONTH if vol_type == "gp2" else EBS_GP3_PER_GB_MONTH
            cost = round(size * price, 2)
            created = vol.get("CreateTime", datetime.now(timezone.utc))
            findings.append({
                "resource_id": vol["VolumeId"],
                "resource_type": "ebs_volume",
                "reason": "unattached",
                "age_days": age_days(created),
                "estimated_monthly_cost_usd": cost,
                "tags": {t: tags.get(t) for t in REQUIRED_TAGS},
                "suggested_action": "delete",
                "safe_to_auto_delete": not is_protected(tags),
                "_protected": is_protected(tags),
                "_raw_tags": tags,
            })
    except ClientError as e:
        print(f"Error scanning EBS: {e}")
    return findings

def scan_stopped_ec2(ec2, stopped_days):
    findings = []
    try:
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
        )
        for r in response.get("Reservations", []):
            for inst in r.get("Instances", []):
                tags = tags_as_dict(inst.get("Tags"))
                stopped_for = _parse_stop_days(inst.get("StateTransitionReason", ""))
                if stopped_for < stopped_days:
                    continue
                findings.append({
                    "resource_id": inst["InstanceId"],
                    "resource_type": "ec2_instance",
                    "reason": f"stopped for {stopped_for} days",
                    "age_days": stopped_for,
                    "estimated_monthly_cost_usd": EC2_DEFAULT_WASTE_PER_MONTH,
                    "tags": {t: tags.get(t) for t in REQUIRED_TAGS},
                    "suggested_action": "terminate",
                    "safe_to_auto_delete": not is_protected(tags),
                    "_protected": is_protected(tags),
                    "_raw_tags": tags,
                })
    except ClientError as e:
        print(f"Error scanning EC2: {e}")
    return findings

def scan_unassociated_eips(ec2):
    findings = []
    try:
        response = ec2.describe_addresses()
        for addr in response.get("Addresses", []):
            if addr.get("AssociationId"):
                continue
            tags = tags_as_dict(addr.get("Tags"))
            findings.append({
                "resource_id": addr.get("AllocationId", addr.get("PublicIp", "unknown")),
                "resource_type": "elastic_ip",
                "reason": "not associated with any instance",
                "age_days": 0,
                "estimated_monthly_cost_usd": EIP_UNATTACHED_PER_MONTH,
                "tags": {t: tags.get(t) for t in REQUIRED_TAGS},
                "suggested_action": "release",
                "safe_to_auto_delete": not is_protected(tags),
                "_protected": is_protected(tags),
                "_raw_tags": tags,
            })
    except ClientError as e:
        print(f"Error scanning EIPs: {e}")
    return findings

def scan_untagged(ec2):
    findings = []
    try:
        response = ec2.describe_instances()
        for r in response.get("Reservations", []):
            for inst in r.get("Instances", []):
                if inst["State"]["Name"] == "terminated":
                    continue
                tags = tags_as_dict(inst.get("Tags"))
                missing = [t for t in REQUIRED_TAGS if not tags.get(t)]
                if missing:
                    findings.append({
                        "resource_id": inst["InstanceId"],
                        "resource_type": "ec2_instance",
                        "reason": f"missing tags: {', '.join(missing)}",
                        "age_days": 0,
                        "estimated_monthly_cost_usd": UNTAGGED_WASTE_PER_MONTH,
                        "tags": {t: tags.get(t) for t in REQUIRED_TAGS},
                        "suggested_action": "tag",
                        "safe_to_auto_delete": False,
                        "_protected": is_protected(tags),
                        "_raw_tags": tags,
                    })
    except ClientError as e:
        print(f"Error scanning untagged: {e}")
    return findings

def delete_finding(ec2, finding):
    if finding["_protected"]:
        return "SKIPPED (Protected=true)"
    rid = finding["resource_id"]
    rtype = finding["resource_type"]
    try:
        if rtype == "ebs_volume" and finding["reason"] == "unattached":
            ec2.delete_volume(VolumeId=rid)
            return "DELETED"
        elif rtype == "ec2_instance" and "stopped" in finding["reason"]:
            ec2.terminate_instances(InstanceIds=[rid])
            return "TERMINATED"
        elif rtype == "elastic_ip":
            ec2.release_address(AllocationId=rid)
            return "RELEASED"
        else:
            return "SKIPPED"
    except Exception as e:
        return f"ERROR: {e}"

def build_report(findings, account_id, region):
    total_waste = round(sum(f["estimated_monthly_cost_usd"] for f in findings), 2)
    clean = [{k: v for k, v in f.items() if not k.startswith("_")} for f in findings]
    return {
        "scan_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account_id": account_id,
        "region": region,
        "summary": {
            "total_orphans": len(findings),
            "estimated_monthly_waste_usd": total_waste,
        },
        "findings": clean,
    }

def write_markdown(report, path):
    lines = [
        "# Cost Janitor Report",
        "",
        f"**Scan time:** {report['scan_timestamp']}",
        f"**Account:** {report['account_id']}",
        f"**Region:** {report['region']}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total orphans | {report['summary']['total_orphans']} |",
        f"| Monthly waste | ${report['summary']['estimated_monthly_waste_usd']:.2f} |",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("No orphans found!")
    else:
        lines.append("| Resource ID | Type | Reason | Age | Cost/mo |")
        lines.append("|-------------|------|--------|-----|---------|")
        for f in report["findings"]:
            lines.append(
                f"| `{f['resource_id']}` | {f['resource_type']} | {f['reason']} | {f['age_days']} | ${f['estimated_monthly_cost_usd']:.2f} |"
            )
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")

def _parse_stop_days(reason):
    import re
    match = re.search(r"\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} GMT)\)", reason)
    if not match:
        return 0
    try:
        dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S GMT").replace(tzinfo=timezone.utc)
        return age_days(dt)
    except ValueError:
        return 0

def main():
    parser = argparse.ArgumentParser(description="NimbusKart Cost Janitor")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True)
    mode.add_argument("--delete", action="store_true", default=False)
    parser.add_argument("--stopped-days", type=int, default=14)
    parser.add_argument("--endpoint-url", type=str, default=None)
    parser.add_argument("--region", type=str, default="us-east-1")
    parser.add_argument("--output", type=str, default="report.json")
    parser.add_argument("--output-md", type=str, default="report.md")
    args = parser.parse_args()

    ec2 = get_client("ec2", args.endpoint_url, args.region)

    print("[janitor] Scanning...")
    findings = []
    findings += scan_unattached_ebs(ec2)
    findings += scan_stopped_ec2(ec2, args.stopped_days)
    findings += scan_unassociated_eips(ec2)
    findings += scan_untagged(ec2)

    seen = set()
    unique = []
    for f in findings:
        key = (f["resource_id"], f["reason"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    findings = unique

    if args.delete:
        for f in findings:
            result = delete_finding(ec2, f)
            print(f"  {f['resource_id']}: {result}")

    report = build_report(findings, "000000000000", args.region)

    with open(args.output, "w") as fh:
        json.dump(report, fh, indent=2)
    print(f"[janitor] Report: {args.output}")

    write_markdown(report, args.output_md)
    print(f"[janitor] Markdown: {args.output_md}")

    total = report["summary"]["total_orphans"]
    print(f"[janitor] Found {total} orphan(s)")

    if not args.delete and total > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()