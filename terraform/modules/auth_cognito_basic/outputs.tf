output "user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "app_client_id" {
  value = aws_cognito_user_pool_client.this.id
}

output "issuer" {
  value = local.issuer
}

output "audiences" {
  value = local.audiences
}

output "guest_username" {
  value = var.guest_username
}

# output "domain_url" {
#   value = local.domain
# }
