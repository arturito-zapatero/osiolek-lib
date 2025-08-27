variable "aws_region" {
  default = "eu-central-1"
}

variable "aws_profile" {
  default = "artur-admin"
}

variable "table_name" {
  type        = string
  description = "DynamoDB table name"
  default     = "towary"
}

variable "environment" {
  type        = string
  description = "environment"
  default     = "dev"
}

variable "guest_password" {
  type      = string
  sensitive = true
}

