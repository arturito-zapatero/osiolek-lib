
data "aws_caller_identity" "current" {}

# Allow this HTTP API (all stages, all methods, all routes) to invoke get_items
resource "aws_lambda_permission" "allow_httpapi_all_routes" {
  statement_id  = "AllowInvokeFromHttpApiAllRoutes"
  action        = "lambda:InvokeFunction"
  function_name = module.lambdas["get_items"].lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${module.api_http.execution_arn}/*/*"
  depends_on    = [module.api_http]
}
# allow API to invoke get_times (separate from get_items)
resource "aws_lambda_permission" "allow_httpapi_get_times" {
  statement_id  = "AllowInvokeFromHttpApiGetTimes"
  action        = "lambda:InvokeFunction"
  function_name = module.lambdas["get_times"].lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${module.api_http.execution_arn}/*/*"
  depends_on    = [module.api_http]
}

module "api_http" {
  source     = "./modules/http_api"
  api_name   = local.api_name
  stage_name = "v1"

  cors = {
    allow_origins     = ["*"]
    allow_methods     = ["GET","POST","PUT","OPTIONS"]
    allow_headers     = ["Authorization","Content-Type"]
    expose_headers    = []
    max_age           = 3600
    allow_credentials = false
  }

  # your Cognito authorizer (from module.auth outputs)
  jwt_authorizer = {
    name      = "${local.api_name}-jwt"
    issuer    = module.auth.issuer
    audiences = module.auth.audiences
  }

    routes = merge(
    {
      towary_public = {
        method      = "GET"
        path        = "/towary"
        auth_type   = "NONE"
        scopes      = []
        lambda_arn  = module.lambdas["get_items"].lambda_arn
        lambda_name = module.lambdas["get_items"].lambda_name
      }
      towary_secure = {
        method      = "GET"
        path        = "/towary-auth"
        auth_type   = "JWT"
        scopes      = []
        lambda_arn  = module.lambdas["get_items"].lambda_arn
        lambda_name = module.lambdas["get_items"].lambda_name
      }
      # NEW: closest-warehouse endpoints (public + auth)
      times_public = {
        method      = "GET"
        path        = "/times"
        auth_type   = "NONE"
        scopes      = []
        lambda_arn  = module.lambdas["get_times"].lambda_arn
        lambda_name = module.lambdas["get_times"].lambda_name
      }
      times_auth = {
        method      = "GET"
        path        = "/auth/times"
        auth_type   = "JWT"
        scopes      = []
        lambda_arn  = module.lambdas["get_times"].lambda_arn
        lambda_name = module.lambdas["get_times"].lambda_name
      }
    }
  )

  tags = local.tags
}

output "api_invoke_url" {
  value = module.api_http.invoke_url
}



