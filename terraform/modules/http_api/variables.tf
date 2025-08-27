variable "api_name" {
  description = "Name of the HTTP API"
  type        = string
}

variable "stage_name" {
  description = "Stage name"
  type        = string
  default     = "v1"
}

variable "cors" {
  description = "CORS configuration (null to disable)"
  type = object({
    allow_origins     = list(string)
    allow_methods     = list(string)
    allow_headers     = list(string)
    expose_headers    = list(string)
    max_age           = number
    allow_credentials = bool
  })
  default = null
}

variable "jwt_authorizer" {
  description = "JWT authorizer (Cognito) config; null to disable"
  type = object({
    name      = string
    issuer    = string       # e.g. https://cognito-idp.<region>.amazonaws.com/<userPoolId>
    audiences = list(string) # e.g. app client IDs
  })
  default = null
}

variable "routes" {
  description = "HTTP routes map"
  type = map(object({
    method      = string            # GET | POST | ...
    path        = string            # starts with '/'
    lambda_arn  = string
    lambda_name = string
    auth_type   = string            # 'NONE' | 'JWT'
    scopes      = list(string)      # [] if not using scopes
  }))
}

variable "tags" {
  description = "Tags for API resources"
  type        = map(string)
  default     = {}
}
