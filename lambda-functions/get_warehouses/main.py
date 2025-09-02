import json, math, os, boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
WAREHOUSE_TABLE = os.environ.get("WAREHOUSE_TABLE", "magazyny")
DEFAULT_LIMIT = int(os.environ.get("NEARBY_LIMIT", "3"))


def _f(v): return float(v) if isinstance(v, Decimal) else float(v)


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    from math import radians, sin, cos, atan2, sqrt
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return R * (2 * atan2(sqrt(a), sqrt(1 - a)))


def _scan_magazyny():
    t = dynamodb.Table(WAREHOUSE_TABLE)
    items, resp = [], t.scan()
    items += resp.get("Items", [])
    while "LastEvaluatedKey" in resp:
        resp = t.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
        items += resp.get("Items", [])
    return [i for i in items if str(i.get("AKTYWNY")).lower() in ("true", "1")]


def lambda_handler(event, ctx):
    qs = (event or {}).get("queryStringParameters") or {}
    try:
        lat = float(qs["lat"]);
        lon = float(qs["lon"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError()
    except Exception:
        return {"statusCode": 400, "body": json.dumps({"error": "Provide valid lat & lon"})}

    limit = int(qs.get("limit", DEFAULT_LIMIT))
    mags = _scan_magazyny()
    ranked = []
    for m in mags:
        d = haversine_km(lat, lon, _f(m["LAT_MAGAZYNU"]), _f(m["LON_MAGAZYNU"]))
        ranked.append({
            "ID_MAGAZYNU": m["ID_MAGAZYNU"],
            "NAZWA": m.get("NAZWA"),
            "MIASTO": m.get("MIASTO"),
            "REGION": m.get("REGION"),
            "LAT_MAGAZYNU": _f(m["LAT_MAGAZYNU"]),
            "LON_MAGAZYNU": _f(m["LON_MAGAZYNU"]),
            "distance_km": round(d, 1)
        })
    ranked.sort(key=lambda x: x["distance_km"])
    return {"statusCode": 200, "body": json.dumps({"warehouses": ranked[:max(1, limit)]})}
