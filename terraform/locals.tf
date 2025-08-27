locals {
  lambda_name  = "towary-matching-lambda"
  runtime      = "python3.12"
  api_name     = "towary-api"
  tags = {
    Project = "osiolek"
    Env     = var.environment
  }

  # Add new functions by adding a new key here and a folder under ../lambda-functions/<key>

}
