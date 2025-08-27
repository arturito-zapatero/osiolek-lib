resource "aws_apigatewayv2_api" "this" {
  name          = var.api_name
  protocol_type = "HTTP"

  dynamic "cors_configuration" {
    for_each = var.cors == null ? [] : [var.cors]
    content {
      allow_credentials = cors_configuration.value.allow_credentials
      allow_headers     = cors_configuration.value.allow_headers
      allow_methods     = cors_configuration.value.allow_methods
      allow_origins     = cors_configuration.value.allow_origins
      expose_headers    = cors_configuration.value.expose_headers
      max_age           = cors_configuration.value.max_age
    }
  }

  tags = var.tags
}

# Optional JWT authorizer
resource "aws_apigatewayv2_authorizer" "jwt" {
  count        = var.jwt_authorizer == null ? 0 : 1
  api_id       = aws_apigatewayv2_api.this.id
  authorizer_type = "JWT"
  name         = var.jwt_authorizer.name
  identity_sources = ["$request.header.Authorization"]
  jwt_configuration {
    audience = var.jwt_authorizer.audiences
    issuer   = var.jwt_authorizer.issuer
  }
}

# Integration per route
resource "aws_apigatewayv2_integration" "lambda" {
  for_each           = var.routes
  api_id             = aws_apigatewayv2_api.this.id
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
  integration_uri    = each.value.lambda_arn
  payload_format_version = "2.0"
}

# Route per item
resource "aws_apigatewayv2_route" "routes" {
  for_each = var.routes
  api_id   = aws_apigatewayv2_api.this.id
  route_key = "${upper(each.value.method)} ${each.value.path}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda[each.key].id}"

  authorizer_id = (
    each.value.auth_type == "JWT" && length(aws_apigatewayv2_authorizer.jwt) > 0
    ? aws_apigatewayv2_authorizer.jwt[0].id
    : null
  )

  authorization_type = (
    each.value.auth_type == "JWT" ? "JWT" : "NONE"
  )

  authorization_scopes = (
    each.value.auth_type == "JWT" ? coalesce(each.value.scopes, []) : null
  )
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = var.stage_name
  auto_deploy = true
  tags        = var.tags
}

# Lambda permissions (per route)
resource "aws_lambda_permission" "allow_invoke" {
  for_each      = var.routes
  statement_id  = "AllowHttpApiInvoke-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
