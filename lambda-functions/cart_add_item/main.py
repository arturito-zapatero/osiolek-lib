# lambda-functions/cart_add_item/main.py
import os, json, uuid, boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
cart_tbl  = dynamodb.Table(os.environ["KOSZYK_TABLE"])
stock_tbl = dynamodb.Table(os.environ["AKT_STAN_MAG_TABLE"])

TTL_DAYS = int(os.environ.get("CART_TTL_DAYS", "7"))

def _now(): return datetime.utcnow().isoformat()
def _ttl(): return int((datetime.utcnow() + timedelta(days=TTL_DAYS)).timestamp())

def _resolve_user_and_cart(event):
    claims = (event.get("requestContext") or {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    sub = claims.get("sub")
    if sub:
        return sub, sub, True  # user_id, cart_id, is_logged
    headers = { (k or "").lower(): v for k, v in (event.get("headers") or {}).items() }
    guest_id = headers.get("x-cart-id") or str(uuid.uuid4())
    return None, guest_id, False

def lambda_handler(event, ctx):
    try:
        body = json.loads(event.get("body") or "{}")
        warehouse_id = body.get("warehouse_id")
        item_id_raw  = body.get("item_id")
        qty          = int(body.get("qty", 1))

        if not warehouse_id or item_id_raw is None or qty <= 0:
            return {"statusCode": 400, "body": json.dumps({"error": "warehouse_id, item_id and qty>0 required"})}

        # Normalize item_id to int if possible (matches akt_stan_mag PK type)
        try:
            item_id = int(item_id_raw)
        except (TypeError, ValueError):
            return {"statusCode": 400, "body": json.dumps({"error": "item_id must be integer-compatible"})}

        user_id, cart_id, is_logged = _resolve_user_and_cart(event)

        # 1) Ensure META exists (create minimal if missing)
        meta = cart_tbl.get_item(Key={"CART_ID": cart_id, "ITEM_KEY": "META"}).get("Item")
        if not meta:
            cart_tbl.put_item(Item={
                "CART_ID": cart_id,
                "ITEM_KEY": "META",
                "USER_ID": user_id,
                # no ID_MAGAZYNU yet; we'll bind below atomically
                "UPDATED_AT": _now(),
                "TTL": _ttl()
            })

        # 2) Bind cart to warehouse if not yet bound, or verify it matches
        #    This is atomic: either set if missing OR require equality.
        try:
            cart_tbl.update_item(
                Key={"CART_ID": cart_id, "ITEM_KEY": "META"},
                UpdateExpression="SET ID_MAGAZYNU = if_not_exists(ID_MAGAZYNU, :wh), UPDATED_AT = :ts, #ttl = :ttl",
                ConditionExpression="attribute_not_exists(ID_MAGAZYNU) OR ID_MAGAZYNU = :wh",
                ExpressionAttributeValues={
                    ":wh": warehouse_id, ":ts": _now(), ":ttl": _ttl()
                },
                ExpressionAttributeNames={
                    "#ttl": "TTL"
                }
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                # Already bound to a different warehouse
                # Fetch to include which one:
                bound = cart_tbl.get_item(Key={"CART_ID": cart_id, "ITEM_KEY": "META"}).get("Item") or {}
                return {
                    "statusCode": 409,
                    "body": json.dumps({
                        "error": "Cart is bound to a different warehouse",
                        "cart_warehouse_id": bound.get("ID_MAGAZYNU")
                    })
                }
            raise

        # 3) Optional stock check in akt_stan_mag (PK=ID_TOWARU(N), SK=ID_MAGAZYNU(S))
        stock = stock_tbl.get_item(Key={"ID_TOWARU": item_id, "ID_MAGAZYNU": warehouse_id}).get("Item")
        if not stock or int(stock.get("ILOSC", 0)) <= 0:
            return {"statusCode": 400, "body": json.dumps({"error": "Out of stock in this warehouse"})}

        # 4) Upsert/increment line item atomically
        cart_tbl.update_item(
            Key={"CART_ID": cart_id, "ITEM_KEY": f"ITEM#{item_id}"},
            UpdateExpression=(
                "SET ID_TOWARU=:it, ID_MAGAZYNU=:wh, "
                "ILOSC = if_not_exists(ILOSC, :z) + :inc, "
                "ADDED_AT = if_not_exists(ADDED_AT, :ts)"
            ),
            ExpressionAttributeValues={
                ":it": item_id, ":wh": warehouse_id, ":z": 0, ":inc": qty, ":ts": _now()
            }
        )

        # 5) Touch META (roll TTL)
        cart_tbl.update_item(
            Key={"CART_ID": cart_id, "ITEM_KEY": "META"},
            UpdateExpression="SET UPDATED_AT = :ts, #ttl = :ttl",
            ExpressionAttributeValues={":ts": _now(), ":ttl": _ttl()},
            ExpressionAttributeNames={"#ttl": "TTL"}
        )

        headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
        if not is_logged:
            headers["Set-Cookie"] = f"cart_id={cart_id}; Path=/; Max-Age={TTL_DAYS*86400}; SameSite=Lax"
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"ok": True, "cart_id": cart_id})}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
