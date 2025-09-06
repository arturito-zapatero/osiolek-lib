import os, json, boto3

dynamodb = boto3.resource("dynamodb")
cart_tbl  = dynamodb.Table(os.environ["KOSZYK_TABLE"])

def _resolve_cart_id(event):
    claims = (event.get("requestContext") or {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    if claims.get("sub"): return claims["sub"]
    headers = { (k or "").lower(): v for k, v in (event.get("headers") or {}).items() }
    return headers.get("x-cart-id")

def lambda_handler(event, ctx):
    cart_id = _resolve_cart_id(event)
    if not cart_id:
        return {"statusCode": 400, "body": json.dumps({"error": "No cart context"})}

    to_delete, resp = [], cart_tbl.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("CART_ID").eq(cart_id)
    )
    to_delete.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = cart_tbl.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("CART_ID").eq(cart_id),
            ExclusiveStartKey=resp["LastEvaluatedKey"])
        to_delete.extend(resp.get("Items", []))

    # Batch delete in chunks of 25
    with cart_tbl.batch_writer() as batch:
        for it in to_delete:
            batch.delete_item(Key={"CART_ID": it["CART_ID"], "ITEM_KEY": it["ITEM_KEY"]})

    return {"statusCode": 200, "body": json.dumps({"ok": True, "deleted": len(to_delete)})}
