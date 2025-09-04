import json
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from pydantic import ValidationError
from models.models import UserCreateModel

# DynamoDB table
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["USERS_TABLE"])

# Cognito client
cognito = boto3.client("cognito-idp")
USER_POOL_ID = os.environ["USER_POOL_ID"]


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))

        # Validate input
        try:
            user_data = UserCreateModel(**body)
        except ValidationError as ve:
            return {"statusCode": 400, "body": ve.json()}

        # Check if already exists in DynamoDB
        if user_exists_in_dynamodb(user_data.email):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "User already exists in DynamoDB"})
            }

        # --- Create Cognito user (manual only) ---
        user_id = None
        if user_data.auth_type == "manual":
            cognito_result = create_cognito_user(user_data)
            if "error" in cognito_result:
                return {
                    "statusCode": cognito_result.get("statusCode", 500),
                    "body": json.dumps({"error": cognito_result["error"]})
                }

            # fetch sub from Cognito
            resp = cognito.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=user_data.email
            )
            user_id = next(
                attr["Value"] for attr in resp["UserAttributes"] if attr["Name"] == "sub"
            )
        else:
            # placeholder for federated users – you'd get sub from IdP JWT
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Only manual auth_type supported now"})
            }

        now = datetime.utcnow().isoformat()

        # DynamoDB item
        item = {
            "user_id": user_id,
            "email": user_data.email,
            "auth_type": user_data.auth_type,
            "first_name": user_data.first_name,
            "surname": user_data.surname,
            "created_at": now,
            "updated_at": now
        }
        if user_data.address:
            item["address"] = user_data.address
        if user_data.phone:
            item["phone"] = user_data.phone

        table.put_item(Item=item)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "User created successfully", "user_id": user_id})
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def create_cognito_user(user_data):
    try:
        cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=user_data.email,
            UserAttributes=[
                {"Name": "email", "Value": user_data.email},
                {"Name": "email_verified", "Value": "True"},
                {"Name": "given_name", "Value": user_data.first_name},
                {"Name": "family_name", "Value": user_data.surname},
            ],
            TemporaryPassword=user_data.password,
            MessageAction="SUPPRESS"
        )
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=user_data.email,
            Password=user_data.password,
            Permanent=True
        )
        return {"success": True}

    except cognito.exceptions.UsernameExistsException:
        return {"error": "User already exists in Cognito", "statusCode": 400}
    except cognito.exceptions.InvalidParameterException as e:
        return {"error": "Invalid parameter: " + str(e), "statusCode": 400}
    except cognito.exceptions.InvalidPasswordException as e:
        return {"error": "Password does not meet policy: " + str(e), "statusCode": 400}
    except ClientError as e:
        return {"error": "Cognito service error: " + str(e), "statusCode": 500}


def user_exists_in_dynamodb(email):
    response = table.query(
        IndexName="email_index",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("email").eq(email)
    )
    return response.get("Count", 0) > 0
