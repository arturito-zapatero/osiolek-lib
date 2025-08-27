# lambda-functions/update_user/main.py
import json
import os
import time
import boto3
from models.models import UserUpdateModel  # Pydantic

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["USERS_TABLE"])

cognito = boto3.client("cognito-idp")
USER_POOL_ID = os.environ.get("USER_POOL_ID")


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))

        # Validate input
        try:
            update_data = UserUpdateModel(**body)
        except Exception as ve:
            return {
                "statusCode": 400,
                "body": ve.json() if hasattr(ve, "json") else str(ve)
            }

        user_id = update_data.user_id
        if not user_id:
            return {"statusCode": 400, "body": "Missing user_id"}

        # --- DynamoDB update ---
        update_expr = []
        expr_attr_values = {}

        for key in ["first_name", "surname", "address", "phone"]:
            value = getattr(update_data, key, None)
            if value is not None:
                update_expr.append(f"{key} = :{key}")
                expr_attr_values[f":{key}"] = value

        update_expr.append("updated_at = :updated_at")
        expr_attr_values[":updated_at"] = str(int(time.time()))

        if not update_expr:
            return {"statusCode": 400, "body": "Nothing to update"}

        update_expression = "SET " + ", ".join(update_expr)

        table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expr_attr_values
        )

        # --- Cognito update for manual users ---
        # Fetch current user to know auth_type and email
        resp = table.get_item(Key={"user_id": user_id})
        item = resp.get("Item")
        if item and item.get("auth_type") == "manual":
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
                    # Safe fallback if Cognito user is missing
                    pass

        return {"statusCode": 200, "body": f"User {user_id} updated"}

    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
