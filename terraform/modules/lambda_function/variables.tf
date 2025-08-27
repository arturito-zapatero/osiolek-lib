# variable "function_name" {
#   type = string
# }
#
# variable "handler" {
#   type = string
# }
#
# variable "runtime" {
#   type    = string
#   default = "python3.12"
# }
#
# variable "timeout" {
#   type    = number
#   default = 300
# }
#
# variable "memory_size" {
#   type    = number
#   default = 512
# }
#
# variable "architecture" {
#   type    = string
#   default = "x86_64"
# }
#
# variable "source_zip" {
#   type = string
# }
#
# variable "environment" {
#   type    = map(string)
#   default = {}
# }
#
# variable "dynamodb_table_arn" {
#   type    = string
#   default = ""   # empty string means "do not attach DynamoDB policy"
# }
#
# variable "dynamodb_actions" {
#   type    = list(string)
#   default = ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:Scan"]
# }
#
# variable "additional_policy_arns" {
#   type    = list(string)
#   default = []
# }
#
# variable "layers" {
#   type    = list(string)
#   default = []
# }
#
# variable "vpc_subnet_ids" {
#   type    = list(string)
#   default = []
# }
#
# variable "vpc_security_group_ids" {
#   type    = list(string)
#   default = []
# }
#
# variable "tags" {
#   type    = map(string)
#   default = {}
# }
#
# variable "log_retention_in_days" {
#   type    = number
#   default = 14
# }
# variable "attach_dynamodb_policy" {
#   type    = bool
#   default = false
# }
#
# variable "lambda_role_arn" {
#   type        = string
#   description = "ARN of the Lambda execution role"
# }
#
# # modules/lambda_function/variables.tf
# variable "lambda_name" {
#   type = string
# }
#
# # List of DynamoDB tables with optional actions per table
# variable "dynamodb_tables" {
#   type = list(object({
#     table_arn = string
#     actions   = list(string)
#   }))
#   default = []
# }
variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "handler" {
  description = "Lambda handler"
  type        = string
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 128
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "architecture" {
  description = "CPU architecture for the Lambda"
  type        = string
  default     = "x86_64"
}

variable "source_zip" {
  description = "Path to Lambda ZIP file"
  type        = string
}

variable "environment" {
  description = "Lambda environment variables"
  type        = map(string)
  default     = {}
}

variable "attach_dynamodb_policy" {
  description = "Attach least-privilege DynamoDB policy?"
  type        = bool
  default     = false
}

variable "dynamodb_table_arn" {
  description = "ARN of DynamoDB table (if attach_dynamodb_policy is true)"
  type        = string
  default     = ""
}

variable "dynamodb_actions" {
  description = "List of DynamoDB actions"
  type        = list(string)
  default     = ["dynamodb:GetItem","dynamodb:PutItem","dynamodb:UpdateItem","dynamodb:Query","dynamodb:Scan"]
}

variable "layers" {
  description = "Lambda layers"
  type        = list(string)
  default     = []
}

variable "vpc_subnet_ids" {
  description = "VPC subnet IDs"
  type        = list(string)
  default     = []
}

variable "vpc_security_group_ids" {
  description = "VPC security group IDs"
  type        = list(string)
  default     = []
}

variable "log_retention_in_days" {
  description = "CloudWatch log retention days"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags for Lambda and resources"
  type        = map(string)
  default     = {}
}
variable "source_code_hash" {
  type = string
}

variable "region" {
  type = string
}

variable "user_pool_id" {
  type    = string
  default = null
}