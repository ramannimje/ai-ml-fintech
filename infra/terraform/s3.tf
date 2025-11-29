resource "aws_s3_bucket" "models_bucket" {
  bucket = "${var.project_name}-models"

  tags = {
    Name = "${var.project_name}-models"
  }
}
