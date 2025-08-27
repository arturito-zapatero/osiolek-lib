# Get current AWS account ID
data "aws_caller_identity" "current" {}

# IAM role for Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.function_name}_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# CloudWatch logs policy
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Optional DynamoDB least-privilege policy
resource "aws_iam_role_policy" "lambda_dynamodb" {
  count = var.attach_dynamodb_policy ? 1 : 0
  name  = "${var.function_name}_dynamodb_policy"
  role  = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = var.dynamodb_actions
      Resource = [
        var.dynamodb_table_arn,
        "${var.dynamodb_table_arn}/index/*"
      ]
    }]
  })
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda_exec_role.arn
}

# Optional Cognito policy for create_user Lambda
resource "aws_iam_role_policy" "lambda_cognito" {
  count = var.function_name == "create_user" ? 1 : 0
  name  = "${var.function_name}_cognito_policy"
  role  = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "cognito-idp:AdminCreateUser",
          "cognito-idp:AdminSetUserPassword",
          "cognito-idp:AdminUpdateUserAttributes",
          "cognito-idp:AdminGetUser",
          "cognito-idp:ListUsers",
          "cognito-idp:AdminAddUserToGroup"
        ]
        Resource = "arn:aws:cognito-idp:${var.region}:${data.aws_caller_identity.current.account_id}:userpool/${var.user_pool_id}"
      }
    ]
  })
}