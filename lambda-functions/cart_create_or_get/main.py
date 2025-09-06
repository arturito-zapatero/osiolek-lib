import os, json, uuid, boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource("dynamodb")
cart_tbl  = dynamodb.Table(os.environ["KOSZYK_TABLE"])

TTL_DAYS = int(os.environ.get("CART_TTL_DAYS", "7"))

def _now(): return datetime.utcnow().isoformat()
def _ttl(): return int((datetime.utcnow() + timedelta(days=TTL_DAYS)).timestamp())

def lambda_handler(event, ctx):
    claims = (event.get("requestContext") or {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    headers = {"Content-Type":"application/json", "Access-Control-Allow-Origin":"*"}
    if claims.get("sub"):
        cart_id = claims["sub"]
        # ensure META exists (no warehouse binding here)
        meta = cart_tbl.get_item(Key={"CART_ID": cart_id, "ITEM_KEY": "META"}).get("Item")
        if not meta:
            cart_tbl.put_item(Item={
                "CART_ID": cart_id, "ITEM_KEY": "META", "USER_ID": cart_id, "UPDATED_AT": _now(), "TTL": _ttl()
            })
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"cart_id": cart_id, "logged": True})}

    # guest (optional)
    cart_id = str(uuid.uuid4())
    cart_tbl.put_item(Item={"CART_ID": cart_id, "ITEM_KEY": "META", "UPDATED_AT": _now(), "TTL": _ttl()})
    headers["Set-Cookie"] = f"cart_id={cart_id}; Path=/; Max-Age={TTL_DAYS*86400}; SameSite=Lax"
    return {"statusCode": 200, "headers": headers, "body": json.dumps({"cart_id": cart_id, "logged": False})}
