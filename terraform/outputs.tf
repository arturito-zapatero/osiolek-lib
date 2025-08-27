output "lambda_region" {
  value = var.aws_region
}

#output "api_url" {
#  value = "https://${aws_api_gateway_rest_api.this.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_deployment.this.stage_name}/towary"
#}
