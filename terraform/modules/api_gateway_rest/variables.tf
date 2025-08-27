variable "api_name" {
  description = "Name of the REST API"
  type        = string
}

variable "aws_region" {
  description = "AWS region (used to build integration URI & output)"
  type        = string
}

variable "stage_name" {
  description = "Stage name (e.g., v1)"
  type        = string
  default     = "v1"
}

# Map of routes; one entry per path/method pairing (single-segment path_part).
# Example:
# routes = {
#   towary_get = {
#     path_part    = "towary"
#     http_method  = "GET"
#     lambda_arn   = module.lambdas["get_items"].lambda_arn
#     lambda_name  = module.lambdas["get_items"].lambda_name
#     authorization = "NONE"
#   }
# }
variable "routes" {
  type = map(object({
    path_part     : string
    http_method   : string
    lambda_arn    : string
    lambda_name   : string
    authorization : string  # NONE | AWS_IAM | CUSTOM | COGNITO_USER_POOLS
  }))
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to taggable API resources"
}
