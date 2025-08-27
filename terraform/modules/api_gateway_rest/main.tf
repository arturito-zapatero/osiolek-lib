resource "aws_api_gateway_rest_api" "this" {
  name = var.api_name
  tags = var.tags
}

# One resource per route (single-segment path). If multiple routes share the same path_part,
# they will refer to the same resource thanks to for_each keying.
locals {
  # Build a deduped map of path parts -> anything (bool) just to create unique resources
  path_parts = { for k, r in var.routes : r.path_part => true }
}

resource "aws_api_gateway_resource" "paths" {
  for_each   = local.path_parts
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = each.key
}

# Methods per route
resource "aws_api_gateway_method" "methods" {
  for_each     = var.routes
  rest_api_id  = aws_api_gateway_rest_api.this.id
  resource_id  = aws_api_gateway_resource.paths[each.value.path_part].id
  http_method  = upper(each.value.http_method)
  authorization = each.value.authorization
}

# Proxy integrations per route
resource "aws_api_gateway_integration" "integrations" {
  for_each                = var.routes
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.paths[each.value.path_part].id
  http_method             = aws_api_gateway_method.methods[each.key].http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri = "arn:aws:apigateway:${var.aws_region}:lambda:path/2015-03-31/functions/${each.value.lambda_arn}/invocations"
}

# Lambda permissions per route
resource "aws_lambda_permission" "apigw_perms" {
  for_each     = var.routes
  statement_id  = "AllowAPIGatewayInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.lambda_name
  principal     = "apigateway.amazonaws.com"
  # Allow any method and any stage under this API
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*"
}

# Deployment (forces re-deploy when methods/integrations change)
resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  description = "Auto deployment for routes"

  depends_on = [
    aws_api_gateway_integration.integrations,
    aws_api_gateway_method.methods
  ]

  triggers = {
    redeploy = sha1(jsonencode({
      routes = var.routes
    }))
  }
}

resource "aws_api_gateway_stage" "this" {
  stage_name    = var.stage_name
  rest_api_id   = aws_api_gateway_rest_api.this.id
  deployment_id = aws_api_gateway_deployment.this.id
  tags          = var.tags
}
