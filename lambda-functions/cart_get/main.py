# lambda-functions/cart_get/main.py
import os, json, boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
cart_tbl  = dynamodb.Table(os.environ["KOSZYK_TABLE"])

def _json_default(o):
    if isinstance(o, Decimal):
        # keep integers as int, others as float
        return int(o) if o % 1 == 0 else float(o)
    raise TypeError

def _resolve_cart_id(event):
    claims = (event.get("requestContext") or {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    if claims.get("sub"): return claims["sub"]
    headers = { (k or "").lower(): v for k, v in (event.get("headers") or {}).items() }
    cid = headers.get("x-cart-id")
    if cid: return cid
    cookie = headers.get("cookie", "")
    for p in cookie.split(";"):
        k, v = (p.strip().split("=",1)+[""])[:2]
        if k == "cart_id": return v
    return None

def lambda_handler(event, ctx):
    cart_id = _resolve_cart_id(event)
    payload = {"cart": {"meta": None, "items": []}}

    if cart_id:
        items = []
        resp = cart_tbl.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("CART_ID").eq(cart_id)
        )
        items.extend(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = cart_tbl.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key("CART_ID").eq(cart_id),
                ExclusiveStartKey=resp["LastEvaluatedKey"]
            )
            items.extend(resp.get("Items", []))

        meta  = next((i for i in items if i["ITEM_KEY"] == "META"), None)
        lines = [i for i in items if i["ITEM_KEY"].startswith("ITEM#")]
        payload["cart"]["meta"]  = meta
        payload["cart"]["items"] = lines

    return {
        "statusCode": 200,
        "headers": {"Content-Type":"application/json","Access-Control-Allow-Origin":"*"},
        "body": json.dumps(payload, default=_json_default),  # <-- key change
    }
