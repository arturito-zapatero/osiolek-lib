import json
import os
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from models.models import UserUpdateModel  # Pydantic

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["USERS_TABLE"])

cognito = boto3.client("cognito-idp")
USER_POOL_ID = os.environ.get("USER_POOL_ID")


def lambda_handler(event, context):
    try:
        # path param from /users/{user_id}
        user_id = (event.get("pathParameters") or {}).get("user_id")

        body = json.loads(event.get("body") or "{}")

        # merge path param into model validation
        try:
            update_data = UserUpdateModel(user_id=user_id, **body)
        except Exception as ve:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": ve.json() if hasattr(ve, "json") else str(ve)
            }

        if not update_data.user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing user_id"})
            }

        # --- DynamoDB update ---
        update_expr = []
        expr_attr_values = {}

        for key in ["first_name", "surname", "address", "phone"]:
            value = getattr(update_data, key, None)
            if value is not None:
                update_expr.append(f"{key} = :{key}")
                expr_attr_values[f":{key}"] = value

        if not update_expr:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Nothing to update"})
            }

        update_expr.append("updated_at = :updated_at")
        expr_attr_values[":updated_at"] = datetime.utcnow().isoformat()

        update_expression = "SET " + ", ".join(update_expr)

        table.update_item(
            Key={"user_id": update_data.user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expr_attr_values
        )

        # --- Cognito update for manual users ---
        resp = table.get_item(Key={"user_id": update_data.user_id})
        item = resp.get("Item", {})
        if item.get("auth_type") == "manual":
            username = item.get("email")
            cognito_attrs = []
            if update_data.first_name is not None:
                cognito_attrs.append({"Name": "given_name", "Value": update_data.first_name})
            if update_data.surname is not None:
                cognito_attrs.append({"Name": "family_name", "Value": update_data.surname})

            if cognito_attrs:
                try:
                    cognito.admin_update_user_attributes(
                        UserPoolId=USER_POOL_ID,
                        Username=username,
                        UserAttributes=cognito_attrs
                    )
                except cognito.exceptions.UserNotFoundException:
                    print(f"Cognito user {username} not found, skipping update.")
                except ClientError as e:
                    print(f"Cognito error updating {username}: {str(e)}")

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "User updated successfully",
                "user_id": update_data.user_id
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
