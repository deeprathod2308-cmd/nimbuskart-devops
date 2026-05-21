variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "staging"
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "NimbusKart"
}

variable "owner" {
  description = "Team or person responsible"
  type        = string
  default     = "platform-team"
}
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed for SSH. Do NOT use 0.0.0.0/0 in production."
  type        = string
  default     = "10.0.0.0/8"
}
variable "instance_type" {
  description = "EC2 instance type for web tier"
  type        = string
  default     = "t3.micro"
}

variable "ami_id" {
  description = "AMI ID for EC2 instances"
  type        = string
  default     = "ami-0c55b159cbfafe1f0"
}

variable "log_bucket_name" {
  description = "Name for the S3 application logs bucket"
  type        = string
  default     = "nimbuskart-app-logs-staging"
}