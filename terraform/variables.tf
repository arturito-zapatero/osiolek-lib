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

variable "enable_google" {
  type    = bool
  default = false
}

variable "google_client_id" {
  type    = string
  default = null
}

variable "google_client_secret" {
  type      = string
  default   = null
  sensitive = true
}