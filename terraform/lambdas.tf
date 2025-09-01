locals {
  lambdas = {
    get_items = {
      handler      = "main.lambda_handler"
      runtime      = "python3.12"
      memory_size  = 512
      timeout      = 300
      architecture = "x86_64"
      environment = {
        TABLE_NAME   = module.towary_table.table_name   # <-- was USERS_TABLE
        USER_POOL_ID = module.auth.user_pool_id
      }
      attach_dynamodb_policy = true
      dynamodb_table_arn     = module.towary_table.table_arn
      layers = [
        #"arn:aws:lambda:eu-central-1:389251923599:layer:common_deps:1"
        aws_lambda_layer_version.common_deps.arn
      ]
      vpc_subnet_ids = []
      vpc_security_group_ids = []
    }

    create_user = {
      handler      = "main.lambda_handler"
      runtime      = "python3.12"
      memory_size  = 512
      timeout      = 300
      architecture = "x86_64"
      environment = {
        USERS_TABLE   = module.users_table.table_name  # for DynamoDB
        USER_POOL_ID  = module.auth.user_pool_id       # Cognito User Pool ID
      }
      attach_dynamodb_policy = true
      dynamodb_table_arn     = module.users_table.table_arn
      layers = [
        aws_lambda_layer_version.common_deps.arn
      ]
      vpc_subnet_ids = []
      vpc_security_group_ids = []
    }

    update_user = {
      handler      = "main.lambda_handler"
      runtime      = "python3.12"
      memory_size  = 512
      timeout      = 300
      architecture = "x86_64"
      environment = { TABLE_NAME = module.users_table.table_name }
      attach_dynamodb_policy = true
      dynamodb_table_arn     = module.users_table.table_arn
      layers = [
        aws_lambda_layer_version.common_deps.arn
      ]
      vpc_subnet_ids = []
      vpc_security_group_ids = []
    }

    pre_signup_link = {
      handler      = "main.lambda_handler"
      runtime      = "python3.12"
      memory_size  = 256
      timeout      = 10
      architecture = "x86_64"
      environment = {
        USER_POOL_ID = module.auth.user_pool_id
      }
      attach_dynamodb_policy = false
      dynamodb_table_arn     = ""
      layers                 = [aws_lambda_layer_version.common_deps.arn]
      vpc_subnet_ids         = []
      vpc_security_group_ids = []
    }

    post_confirmation_profile = {
      handler      = "main.lambda_handler"
      runtime      = "python3.12"
      memory_size  = 256
      timeout      = 10
      architecture = "x86_64"
      environment = {
        USERS_TABLE = module.users_table.table_name
      }
      attach_dynamodb_policy = true
      dynamodb_table_arn     = module.users_table.table_arn
      layers                 = [aws_lambda_layer_version.common_deps.arn]
      vpc_subnet_ids         = []
      vpc_security_group_ids = []
    }

    get_times = {
      handler      = "main.lambda_handler"
      runtime      = "python3.12"
      memory_size  = 512
      timeout      = 300
      architecture = "x86_64"
      environment = {
        WAREHOUSE_TABLE    = module.magazyny_table.table_name
        AKT_STAN_MAG_TABLE = module.akt_stan_mag_table.table_name
        AKT_STAN_MAG_GSI   = "id_magazynu_index"
      }
      # built-in single-table policy isn't enough; we need 2 tables + index
      attach_dynamodb_policy = false
      dynamodb_table_arn     = ""
      layers                 = [aws_lambda_layer_version.common_deps.arn]
      vpc_subnet_ids         = []
      vpc_security_group_ids = []
    }
  }
}

############################################################
# Copy common Pydantic models to each Lambda function
############################################################
resource "null_resource" "copy_common_models" {
  for_each = local.lambdas

  provisioner "local-exec" {
    command = <<PY
python - <<END
import shutil, os
src = os.path.join("${path.module}", "..", "lambda-functions", "common", "models.py")
dst_dir = os.path.join("${path.module}", "..", "lambda-functions", "${each.key}", "models")
os.makedirs(dst_dir, exist_ok=True)
shutil.copy(src, os.path.join(dst_dir, "models.py"))
END
PY
  }

  triggers = {
    lambda_name   = each.key
    models_sha256 = filemd5("${path.module}/../lambda-functions/common/models.py")
  }
}

resource "aws_lambda_layer_version" "common_deps" {
  filename            = "../lambda_layers/layer.zip" # this must exist already
  layer_name          = "common_deps"
  compatible_runtimes = ["python3.12"]
  source_code_hash    = filebase64sha256("../lambda_layers/layer.zip")
}
############################################################
# Archive each Lambda function into ZIP (no dependencies in function folder now)
############################################################
data "archive_file" "lambda_zip" {
  for_each   = local.lambdas
  type       = "zip"
  source_dir = "${path.module}/../lambda-functions/${each.key}"
  output_path = "${path.module}/${each.key}.zip"

  depends_on = [null_resource.copy_common_models]
}

# Create Lambda modules
module "lambdas" {
  for_each     = local.lambdas
  source       = "./modules/lambda_function"

  function_name           = each.key
  handler                 = each.value.handler
  runtime                 = each.value.runtime
  memory_size             = each.value.memory_size
  timeout                 = each.value.timeout
  architecture            = each.value.architecture
  source_zip              = abspath(data.archive_file.lambda_zip[each.key].output_path)

  # 🔽 ADD THIS LINE
  source_code_hash        = data.archive_file.lambda_zip[each.key].output_base64sha256

  environment             = each.value.environment
  attach_dynamodb_policy  = each.value.attach_dynamodb_policy
  dynamodb_table_arn      = each.value.dynamodb_table_arn
  layers                  = each.value.layers
  vpc_subnet_ids          = each.value.vpc_subnet_ids
  vpc_security_group_ids  = each.value.vpc_security_group_ids
  log_retention_in_days   = 14
  tags                    = local.tags
  region       = var.aws_region
  user_pool_id = module.auth.user_pool_id
}

# IAM for get_times: scan magazyny, query akt_stan_mag + its GSI
resource "aws_iam_role_policy" "get_times_dynamodb" {
  role = module.lambdas["get_times"].role_name
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = ["dynamodb:Scan"],
        Resource = module.magazyny_table.table_arn
      },
      {
        Effect = "Allow",
        Action = ["dynamodb:Query"],
        Resource = [
          module.akt_stan_mag_table.table_arn,
          "${module.akt_stan_mag_table.table_arn}/index/id_magazynu_index"
        ]
      }
    ]
  })
}