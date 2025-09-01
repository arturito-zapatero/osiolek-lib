import json, math, os, boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
WAREHOUSE_TABLE    = os.environ.get("WAREHOUSE_TABLE", "magazyny")
AKT_STAN_MAG_TABLE = os.environ.get("AKT_STAN_MAG_TABLE", "akt_stan_mag")
AKT_STAN_MAG_GSI   = os.environ.get("AKT_STAN_MAG_GSI", "id_magazynu_index")

_cached_magazyny = None

def _to_float(v):
    return float(v) if isinstance(v, Decimal) else v

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def get_active_magazyny():
    global _cached_magazyny
    if _cached_magazyny is not None:
        return _cached_magazyny
    table = dynamodb.Table(WAREHOUSE_TABLE)
    items, resp = [], table.scan()
    items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp:
        resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    # keep only AKTYWNY == true
    out = []
    for it in items:
        if it.get("AKTYWNY") in (True, "true", "True", "TRUE", 1, "1"):
            out.append({
                "ID_MAGAZYNU": it["ID_MAGAZYNU"],
                "NAZWA": it.get("NAZWA"),
                "LAT_MAGAZYNU": _to_float(it.get("LAT_MAGAZYNU")),
                "LON_MAGAZYNU": _to_float(it.get("LON_MAGAZYNU")),
                "MIASTO": it.get("MIASTO"),
                "REGION": it.get("REGION")
            })
    _cached_magazyny = out
    return _cached_magazyny

def pick_closest(lat, lon):
    mags = get_active_magazyny()
    if not mags:
        return None
    best = min(
        mags,
        key=lambda m: haversine_km(lat, lon, m["LAT_MAGAZYNU"], m["LON_MAGAZYNU"])
    )
    return best

def query_items_for_magazyn(id_magazynu, only_in_stock=True, limit=100):
    table = dynamodb.Table(AKT_STAN_MAG_TABLE)
    # Query the GSI by ID_MAGAZYNU
    kwargs = {
        "IndexName": AKT_STAN_MAG_GSI,
        "KeyConditionExpression": Key("ID_MAGAZYNU").eq(id_magazynu),
        "Limit": limit
    }
    if only_in_stock:
        kwargs["FilterExpression"] = Attr("ILOSC").gt(0)
    items, resp = [], table.query(**kwargs)
    items.extend(resp.get("Items", []))
    while "LastEvaluatedKey" in resp and len(items) < limit:
        resp = table.query(**kwargs, ExclusiveStartKey=resp["LastEvaluatedKey"])
        items.extend(resp.get("Items", []))
    # sanitize Decimals
    def san(o):
        if isinstance(o, Decimal): return float(o)
        if isinstance(o, dict): return {k: san(v) for k, v in o.items()}
        if isinstance(o, list): return [san(v) for v in o]
        return o
    return san(items[:limit])

def lambda_handler(event, context):
    params = event.get("queryStringParameters") or {}
    if not params and event.get("body"):
        try:
            params = json.loads(event["body"])
        except Exception:
            params = {}

    try:
        lat = float(params["lat"])
        lon = float(params["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError()
    except Exception:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Provide valid lat & lon"})
        }

    closest = pick_closest(lat, lon)
    if not closest:
        return {"statusCode": 503, "body": json.dumps({"error": "No active warehouses"})}

    # Example: fetch items available in that warehouse
    items = query_items_for_magazyn(closest["ID_MAGAZYNU"], only_in_stock=True, limit=200)

    response = {
        "closest_warehouse": {
            **closest,
            "distance_km": round(
                haversine_km(lat, lon, closest["LAT_MAGAZYNU"], closest["LON_MAGAZYNU"]), 1
            )
        },
        "items": items
    }
    return {"statusCode": 200, "body": json.dumps(response)}
