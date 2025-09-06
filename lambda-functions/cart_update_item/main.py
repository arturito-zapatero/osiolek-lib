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

    item_id = (event.get("pathParameters") or {}).get("item_id")
    if not item_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing item_id in path"})}

    body = json.loads(event.get("body") or "{}")
    qty = int(body.get("qty", -1))
    if qty < 0:
        return {"statusCode": 400, "body": json.dumps({"error": "qty required and must be >= 0"})}

    if qty == 0:
        cart_tbl.delete_item(Key={"CART_ID": cart_id, "ITEM_KEY": f"ITEM#{item_id}"})
        return {"statusCode": 200, "body": json.dumps({"ok": True, "removed": item_id})}

    cart_tbl.update_item(
        Key={"CART_ID": cart_id, "ITEM_KEY": f"ITEM#{item_id}"},
        UpdateExpression="SET ILOSC=:q",
        ExpressionAttributeValues={":q": qty}
    )
    return {"statusCode": 200, "body": json.dumps({"ok": True, "item_id": item_id, "qty": qty})}
