provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

resource "aws_s3_bucket" "csv_upload" {
  bucket        = "sqlserver-export-csvs"
  force_destroy = true

  tags = {
    Environment = "dev"
  }
}

# DynamoDB tables moved to dynamodb.tf
