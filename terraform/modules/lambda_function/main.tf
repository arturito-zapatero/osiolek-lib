locals {
  use_vpc = length(var.vpc_subnet_ids) > 0 && length(var.vpc_security_group_ids) > 0
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_in_days
  tags              = var.tags
}

# Lambda function
resource "aws_lambda_function" "this" {
  function_name    = var.function_name
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = var.handler
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory_size
  architectures    = [var.architecture]
  filename         = var.source_zip

  source_code_hash = var.source_code_hash
  #source_code_hash = filebase64sha256(var.source_zip)

  dynamic "environment" {
    for_each = length(var.environment) > 0 ? [1] : []
    content {
      variables = var.environment
    }
  }

  dynamic "vpc_config" {
    for_each = local.use_vpc ? [1] : []
    content {
      subnet_ids         = var.vpc_subnet_ids
      security_group_ids = var.vpc_security_group_ids
    }
  }

  layers     = var.layers
  tags       = var.tags
  depends_on = [aws_cloudwatch_log_group.this]

  lifecycle {
    ignore_changes = [last_modified]
  }
}


