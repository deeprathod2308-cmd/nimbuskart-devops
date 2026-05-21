import os
import json
import argparse
import boto3
from botocore.exceptions import ClientError

def get_boto3_client(service_name, endpoint_url=None, region_name="us-east-1"):
    return boto3.client(
        service_name,
        region_name=region_name,
        endpoint_url=endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )

def scan_orphan_ebs_volumes(ec2_client):
    findings = []
    try:
        volumes = ec2_client.describe_volumes()
        for volume in volumes.get('Volumes', []):
            if not volume.get('Attachments'):
                vol_id = volume['VolumeId']
                size = volume['Size']
                # Est. cost: $0.08 per GB per month for gp3
                monthly_cost = size * 0.08
                
                findings.append({
                    "resource_id": vol_id,
                    "resource_type": "EBS Volume",
                    "status": "Unattached (Orphan)",
                    "monthly_cost_impact": monthly_cost,
                    "reason": f"Volume of size {size}GB is not attached to any EC2 instance."
                })
    except ClientError as e:
        print(f"Error scanning EBS volumes: {e}")
    return findings

def generate_reports(findings, output_dir="janitor"):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. JSON Report
    json_path = os.path.join(output_dir, "report.json")
    with open(json_path, "w") as f:
        json.dump(findings, f, indent=2)
        
    # 2. Markdown Report
    md_path = os.path.join(output_dir, "report.md")
    with open(md_path, "w") as f:
        f.write("# Cost Janitor - Scan Report\n\n")
        if not findings:
            f.write("## No orphan resources found. Infrastructure is clean! 🎉\n")
            return
            
        total_waste = sum(item['monthly_cost_impact'] for item in findings)
        f.write(f"###  Total Potential Monthly Savings: ${total_waste:.2f}\n\n")
        f.write("| Resource ID | Type | Status | Monthly Cost | Reason |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for item in findings:
            f.write(f"| {item['resource_id']} | {item['resource_type']} | {item['status']} | ${item['monthly_cost_impact']:.2f} | {item['reason']} |\n")

def main():
    parser = argparse.ArgumentParser(description="NimbusKart Cost Janitor Script")
    parser.add_name_or_flag = parser.add_argument("--endpoint-url", help="LocalStack endpoint URL")
    args = parser.parse_args()

    print("Starting Cloud Infrastructure Scan...")
    ec2_client = get_boto3_client("ec2", endpoint_url=args.endpoint_url)
    
    findings = []
    findings.extend(scan_orphan_ebs_volumes(ec2_client))
    
    print(f"Scan complete. Found {len(findings)} orphan resources.")
    generate_reports(findings)
    print("Reports generated successfully in 'janitor/' folder.")

if __name__ == "__main__":
    main()