##############################################
# User Pool
##############################################
resource "aws_cognito_user_pool" "this" {
  name = var.pool_name

  password_policy {
    minimum_length    = var.password_min_length
    require_lowercase = false
    require_numbers   = false
    require_symbols   = false
    require_uppercase = false
  }

  # Keep existing behavior; you can set ["email"] later if you want auto-verify
  auto_verified_attributes = []

  tags = var.tags
}

#############################################
# Google Identity Provider (optional via flag)
##############################################
resource "aws_cognito_identity_provider" "google" {
  count         = var.enable_google ? 1 : 0
  user_pool_id  = aws_cognito_user_pool.this.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
    authorize_scopes = "openid email profile"
  }

  attribute_mapping = {
    email       = "email"
    given_name  = "given_name"
    family_name = "family_name"
    name        = "name"
    picture     = "picture"
  }
}

##############################################
# App Client (manual auth + OAuth code+PKCE)
##############################################
# Supported IdPs list depends on enable_google
locals {
  supported_idps = var.enable_google ? ["COGNITO", "Google"] : ["COGNITO"]
}

resource "aws_cognito_user_pool_client" "this" {
  name            = var.app_client_name
  user_pool_id    = aws_cognito_user_pool.this.id
  generate_secret = false  # public client (PKCE)

  # Keep your existing manual login via SDK (InitiateAuth)
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  # Enable Hosted UI OAuth Authorization Code (PKCE on client side)
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]  # , "offline_access"
  supported_identity_providers         = local.supported_idps

  # Where Cognito redirects back to (Postman + your app)
  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  # Dev-friendly lifetimes (kept from your config)
  access_token_validity  = 60   # minutes
  id_token_validity      = 60   # minutes
  refresh_token_validity = 30   # days
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  prevent_user_existence_errors = "ENABLED"

  # Ensure the app client is created/updated after Google IdP (when enabled)
  depends_on = [
    aws_cognito_identity_provider.google
  ]
}

##############################################
# Optional dev 'guest' user (unchanged)
##############################################
resource "aws_cognito_user" "guest" {
  count          = var.create_guest_user ? 1 : 0
  user_pool_id   = aws_cognito_user_pool.this.id
  username       = var.guest_username
  password       = var.guest_password
  enabled        = true
  message_action = "SUPPRESS"
}

##############################################
# Useful locals/outputs source
##############################################
locals {
  issuer    = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
  audiences = [aws_cognito_user_pool_client.this.id]
  # domain    = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${var.aws_region}.amazoncognito.com"
}