resource "aws_dynamodb_table" "this" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = var.hash_key
  range_key    = var.range_key != null ? var.range_key : null

  dynamic "attribute" {
    for_each = var.attributes
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  dynamic "global_secondary_index" {
    for_each = var.global_secondary_indexes
      content {
        name            = global_secondary_index.value.name
        hash_key        = global_secondary_index.value.hash_key
        projection_type = global_secondary_index.value.projection_type

        range_key = contains(keys(global_secondary_index.value), "range_key") ? global_secondary_index.value.range_key : null
      }
  }

  ttl {
    attribute_name = "TTL"
    enabled        = true
  }
}
