variable "table_name" {
  description = "Name of the DynamoDB table"
  type        = string
}

variable "hash_key" {
  description = "Partition key of the DynamoDB table"
  type        = string
}

variable "range_key" {
  description = "Sort key of the DynamoDB table (optional)"
  type        = string
  default     = null
}

variable "attributes" {
  description = "List of attributes (columns) with their types"
  type = list(object({
    name = string
    type = string
  }))
}

variable "global_secondary_indexes" {
  description = "List of global secondary indexes (GSIs)"
  type = list(map(string))
  default = []
}
