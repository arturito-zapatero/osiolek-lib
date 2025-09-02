import os
from decimal import Decimal
import unicodedata
from rapidfuzz import process, fuzz
import boto3, json
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from models.models import GetItemsQueryModel  # <- Pydantic model

dynamodb = boto3.resource("dynamodb")

# Items/catalog table (same as before)
ITEMS_TABLE = os.environ["TABLE_NAME"]
items_tbl = dynamodb.Table(ITEMS_TABLE)

# Warehouse stock table + GSI (NEW)
AKT_STAN_MAG_TABLE = os.environ.get("AKT_STAN_MAG_TABLE", "akt_stan_mag")
AKT_STAN_MAG_GSI   = os.environ.get("AKT_STAN_MAG_GSI", "id_magazynu_index")
stock_tbl = dynamodb.Table(AKT_STAN_MAG_TABLE)

PROJECTION = "ID_TOWARU, NAZWA_TOWARU, DATA_UTWORZENIA"
MAX_SCAN_PAGES = int(os.environ.get("SCAN_PAGE_LIMIT", "3"))
MAX_SCAN_ITEMS = int(os.environ.get("SCAN_ITEM_LIMIT", "8000"))

def _json_default(o):
    if isinstance(o, Decimal):
        return int(o) if o % 1 == 0 else float(o)
    raise TypeError

def _strip_accents(s: str) -> str:
    if not s:
        return ""
    return "".join(ch for ch in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(ch)).lower()

def _parse_iso(dt: str):
    if not dt:
        return None
    dt = dt.replace("Z", "+00:00").replace(" ", "T")
    try:
        return datetime.fromisoformat(dt)
    except Exception:
        return None

def _get_allowed_ids_for_warehouse(warehouse_id: str, limit: int = 5000) -> set:
    """Query akt_stan_mag GSI for items available in given warehouse."""
    kwargs = {
        "IndexName": AKT_STAN_MAG_GSI,
        "KeyConditionExpression": Key("ID_MAGAZYNU").eq(warehouse_id),
        "FilterExpression": Attr("ILOSC").gt(0),  # only in-stock
        "ProjectionExpression": "ID_TOWARU, ILOSC",
        "Limit": min(limit, 1000)  # page size
    }
    allowed = set()
    resp = stock_tbl.query(**kwargs)
    for it in resp.get("Items", []):
        if "ID_TOWARU" in it:
            allowed.add(it["ID_TOWARU"])
    while "LastEvaluatedKey" in resp and len(allowed) < limit:
        resp = stock_tbl.query(**kwargs, ExclusiveStartKey=resp["LastEvaluatedKey"])
        for it in resp.get("Items", []):
            if "ID_TOWARU" in it:
                allowed.add(it["ID_TOWARU"])
    return allowed

def lambda_handler(event, context):
    try:
        qs = (event or {}).get("queryStringParameters") or {}
        headers = (event or {}).get("headers") or {}

        # NEW: warehouse_id is required (query or header)
        warehouse_id = qs.get("warehouse_id") or headers.get("X-Warehouse-Id")
        if not warehouse_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing 'warehouse_id'."}),
            }

        # Validate query params via Pydantic (still validates: query, cutoff, limit)
        try:
            query_model = GetItemsQueryModel(**qs)
        except Exception as ve:
            return {
                "statusCode": 400,
                "body": ve.json() if hasattr(ve, "json") else str(ve)
            }

        term = query_model.query.strip().lower()
        cutoff = query_model.cutoff
        limit = query_model.limit

        if not term:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing 'query' parameter."}),
            }

        # 1) Get the set of allowed item IDs for this warehouse
        allowed_ids = _get_allowed_ids_for_warehouse(warehouse_id)
        if not allowed_ids:
            # No stock in this warehouse — return empty result quickly
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                },
                "body": json.dumps({"results": [], "next_cursor": None}),
            }

        # 2) Scan items table, but keep only allowed IDs (fast set check)
        items = []
        scan_kwargs = {"ProjectionExpression": PROJECTION}
        pages = 0
        while True:
            resp = items_tbl.scan(**scan_kwargs)
            batch = resp.get("Items", [])

            # keep only items from this warehouse's stock
            for it in batch:
                if it.get("ID_TOWARU") in allowed_ids:
                    items.append(it)

            pages += 1
            if len(items) >= MAX_SCAN_ITEMS or pages >= MAX_SCAN_PAGES:
                break

            lek = resp.get("LastEvaluatedKey")
            if not lek:
                break
            scan_kwargs["ExclusiveStartKey"] = lek

        # 3) Build lookup by normalized name from filtered items
        name_to_items = {}
        for it in items:
            name_norm = _strip_accents((it.get("NAZWA_TOWARU") or "").strip())
            if not name_norm:
                continue
            name_to_items.setdefault(name_norm, []).append(it)

        term_norm = _strip_accents(term)

        # 4) Fuzzy match on the reduced candidate set
        matches = process.extract(
            term_norm,
            list(name_to_items.keys()),
            scorer=fuzz.token_set_ratio,
            score_cutoff=max(0, min(cutoff, 100)),
            limit=limit,
        ) if name_to_items else []

        # 5) For each matched name, pick latest by DATA_UTWORZENIA per ID_TOWARU
        latest_by_id = {}
        for match_name, score, _ in matches:
            for it in name_to_items.get(match_name, []):
                id_towaru = it.get("ID_TOWARU")
                dt = _parse_iso(it.get("DATA_UTWORZENIA", ""))
                cur = latest_by_id.get(id_towaru)
                if id_towaru and (cur is None or _parse_iso(cur.get("DATA_UTWORZENIA", "")) < dt):
                    latest_by_id[id_towaru] = it

        # 6) Format results (unique by ID_TOWARU)
        seen = set()
        results = []
        for match_name, _, _ in matches:
            for it in name_to_items.get(match_name, []):
                id_t = it.get("ID_TOWARU")
                if id_t in latest_by_id and id_t not in seen:
                    v = latest_by_id[id_t]
                    results.append({
                        "ID_TOWARU": v.get("ID_TOWARU"),
                        "NAZWA_TOWARU": v.get("NAZWA_TOWARU"),
                    })
                    seen.add(id_t)

        partial = pages >= MAX_SCAN_PAGES or len(items) >= MAX_SCAN_ITEMS
        next_cursor = None  # scan cursor doesn’t map cleanly once we filter; omit

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "X-Partial-Results": "true" if partial else "false",
            },
            "body": json.dumps({
                "results": results,
                "next_cursor": next_cursor
            }, default=_json_default),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
