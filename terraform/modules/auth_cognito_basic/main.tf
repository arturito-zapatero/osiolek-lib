resource "aws_cognito_user_pool" "this" {
  name = var.pool_name

  password_policy {
    minimum_length    = var.password_min_length
    require_lowercase = false
    require_numbers   = false
    require_symbols   = false
    require_uppercase = false
  }

  auto_verified_attributes = []

  tags = var.tags
}

resource "aws_cognito_user_pool_client" "this" {
  name            = var.app_client_name
  user_pool_id    = aws_cognito_user_pool.this.id
  generate_secret = false

  # username/password + refresh, no hosted UI needed
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Dev-friendly lifetimes
  access_token_validity  = 60   # minutes
  id_token_validity      = 60   # minutes
  refresh_token_validity = 30   # days
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

# Optional shared 'guest' user (dev only)
resource "aws_cognito_user" "guest" {
  count         = var.create_guest_user ? 1 : 0
  user_pool_id  = aws_cognito_user_pool.this.id
  username      = var.guest_username
  password      = var.guest_password
  enabled       = true
  message_action = "SUPPRESS"
}

locals {
  issuer    = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
  audiences = [aws_cognito_user_pool_client.this.id]
}