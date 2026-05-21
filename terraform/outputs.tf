output "vpc_id" {
  description = "VPC ID"
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.network.public_subnet_ids
}

output "bucket_name" {
  description = "Application logs S3 bucket name"
  value       = aws_s3_bucket.app_logs.id
}