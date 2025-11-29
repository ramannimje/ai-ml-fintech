output "alb_dns_name" {
  value = aws_lb.api_alb.dns_name
}

output "s3_bucket_name" {
  value = aws_s3_bucket.models_bucket.bucket
}
