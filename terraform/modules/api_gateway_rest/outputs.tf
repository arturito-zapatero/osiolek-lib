output "api_id" {
  value = aws_api_gateway_rest_api.this.id
}

output "execution_arn" {
  value = aws_api_gateway_rest_api.this.execution_arn
}

output "stage_name" {
  value = aws_api_gateway_stage.this.stage_name
}

output "invoke_url" {
  value = "https://${aws_api_gateway_rest_api.this.id}.execute-api.${var.aws_region}.amazonaws.com/${aws_api_gateway_stage.this.stage_name}"
}

# Path ARNs map (useful if you need to grant method-level perms later)
output "resource_ids" {
  value = { for p, r in aws_api_gateway_resource.paths : p => r.id }
}
