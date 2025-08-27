variable "pool_name" {
  type        = string
  default     = "osiolek-users"
  description = "Cognito User Pool name"
}

variable "app_client_name" {
  type        = string
  default     = "osiolek-app"
  description = "Cognito App Client name (no secret)"
}

variable "password_min_length" {
  type        = number
  default     = 6
  description = "Dev-friendly password minimum length"
}

variable "create_guest_user" {
  type        = bool
  default     = true
  description = "Create a shared 'guest' user (dev only)"
}

variable "guest_username" {
  type        = string
  default     = "guest"
  description = "Username for the shared dev user"
}

variable "guest_password" {
  type        = string
  sensitive   = true
  default     = ""
  description = "Password for the shared dev user (store in tfvars)"
}

variable "tags" {
  type        = map(string)
  default     = {}
}
variable "aws_region" {
  type        = string
  description = "AWS region for issuer URL"
}