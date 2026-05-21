terraform {
  required_version = ">= 1.3.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    ec2 = "http://localhost:4566"
    s3  = "http://localhost:4566"
    iam = "http://localhost:4566"
  }
}

module "network" {
  source             = "./modules/network"
  vpc_cidr           = var.vpc_cidr
  subnet_cidrs       = ["10.20.1.0/24", "10.20.2.0/24"]
  availability_zones = ["${var.region}a", "${var.region}b"]
  ssh_allowed_cidr   = var.ssh_allowed_cidr
  
  tags = {
    Environment = var.environment
    Project     = var.project
    Owner       = var.owner
  }
}

resource "aws_s3_bucket" "app_logs" {
  bucket        = var.log_bucket_name
  force_destroy = true

  tags = {
    Name        = "${var.project}-${var.environment}-app-logs"
    Environment = var.environment
    Project     = var.project
  }
}

resource "aws_instance" "web" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = module.network.public_subnet_ids[0]
  vpc_security_group_ids = [module.network.web_security_group_id]

  tags = {
    Name        = "${var.project}-${var.environment}-web-server"
    Environment = var.environment
    Project     = var.project
  }
}

resource "aws_ebs_volume" "orphan_volume" {
  availability_zone = "${var.region}a"
  size              = 20
  type              = "gp3"

  tags = {
    Name        = "${var.project}-${var.environment}-orphan-vol"
    Environment = var.environment
    Project     = var.project
  }
}