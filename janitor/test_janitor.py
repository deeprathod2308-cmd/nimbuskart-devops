import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from moto import mock_aws
import boto3
import janitor as j

@pytest.fixture
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

@mock_aws
def test_scan_unattached_ebs(aws_credentials):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vol = ec2.create_volume(
        AvailabilityZone="us-east-1a",
        Size=20,
        VolumeType="gp3"
    )
    findings = j.scan_unattached_ebs(ec2)
    assert any(f["resource_id"] == vol["VolumeId"] for f in findings)

@mock_aws
def test_protected_volume_skipped(aws_credentials):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vol = ec2.create_volume(
        AvailabilityZone="us-east-1a",
        Size=20,
        VolumeType="gp3",
        TagSpecifications=[{
            "ResourceType": "volume",
            "Tags": [{"Key": "Protected", "Value": "true"}]
        }]
    )
    findings = j.scan_unattached_ebs(ec2)
    protected = [f for f in findings if f["resource_id"] == vol["VolumeId"]]
    assert protected[0]["safe_to_auto_delete"] is False

@mock_aws
def test_scan_unassociated_eip(aws_credentials):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.allocate_address(Domain="vpc")
    findings = j.scan_unassociated_eips(ec2)
    assert len(findings) >= 1

@mock_aws
def test_report_schema(aws_credentials):
    ec2 = boto3.client("ec2", region_name="us-east-1")
    ec2.create_volume(AvailabilityZone="us-east-1a", Size=10, VolumeType="gp3")
    findings = j.scan_unattached_ebs(ec2)
    report = j.build_report(findings, "000000000000", "us-east-1")
    assert "scan_timestamp" in report
    assert "account_id" in report
    assert "region" in report
    assert "summary" in report
    assert "findings" in report