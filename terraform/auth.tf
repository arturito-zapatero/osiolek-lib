module "auth" {
  source            = "./modules/auth_cognito_basic"
  aws_region        = var.aws_region

  pool_name         = "osiolek-users"
  app_client_name   = "osiolek-app"

  create_guest_user = true
  guest_username    = "guest"
  guest_password    = var.guest_password

  # ⬇️ new for Hosted UI + Google
  enable_google        = false # we need GCP account for this
  google_client_id     = var.google_client_id
  google_client_secret = var.google_client_secret
  callback_urls        = ["https://oauth.pstmn.io/v1/callback"]  # add your app URL later
  logout_urls          = []

  tags = local.tags
}
resource "aws_cognito_user_pool_domain" "this" {
  domain       = "osiolek-app-users"   # must be unique globally
  user_pool_id = module.auth.user_pool_id
}

output "cognito_user_pool_id"  {
  value = module.auth.user_pool_id
}
output "cognito_app_client_id" {
  value = module.auth.app_client_id
}
output "cognito_issuer"        {
  value = module.auth.issuer
}

output "cognito_domain" {
  value = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${var.aws_region}.amazoncognito.com"
}

