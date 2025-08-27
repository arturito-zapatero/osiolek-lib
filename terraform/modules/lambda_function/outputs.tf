output "lambda_name" { value = aws_lambda_function.this.function_name }
output "lambda_arn"  { value = aws_lambda_function.this.arn }

output "role_arn"    { value = aws_iam_role.lambda_exec_role.arn }
