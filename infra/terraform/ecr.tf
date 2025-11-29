resource "aws_ecr_repository" "api_repo" {
  name = "${var.project_name}-api"
}

output "api_ecr_url" {
  value = aws_ecr_repository.api_repo.repository_url
}
