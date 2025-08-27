# lambda-functions/get_items/main.py
import os
from decimal import Decimal
import unicodedata
from rapidfuzz import process, fuzz
import boto3, json
from datetime import datetime
from models.models import GetItemsQueryModel  # <- Pydantic model

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

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

def lambda_handler(event, context):
    try:
        qs = (event or {}).get("queryStringParameters") or {}

        # Validate query params via Pydantic
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

        # Scan DynamoDB
        items = []
        scan_kwargs = {"ProjectionExpression": PROJECTION}
        pages = 0
        while True:
            resp = table.scan(**scan_kwargs)
            batch = resp.get("Items", [])
            items.extend(batch)

            pages += 1
            if len(items) >= MAX_SCAN_ITEMS or pages >= MAX_SCAN_PAGES:
                break

            lek = resp.get("LastEvaluatedKey")
            if not lek:
                break
            scan_kwargs["ExclusiveStartKey"] = lek

        # Build lookup by normalized name
        name_to_items = {}
        for it in items:
            name_norm = _strip_accents((it.get("NAZWA_TOWARU") or "").strip())
            if not name_norm:
                continue
            name_to_items.setdefault(name_norm, []).append(it)

        term_norm = _strip_accents(term)

        # Fuzzy match
        matches = process.extract(
            term_norm,
            list(name_to_items.keys()),
            scorer=fuzz.token_set_ratio,
            score_cutoff=max(0, min(cutoff, 100)),
            limit=limit,
        ) if name_to_items else []

        # Latest item per ID_TOWARU
        latest_by_id = {}
        for match_name, score, _ in matches:
            for it in name_to_items.get(match_name, []):
                id_towaru = it.get("ID_TOWARU")
                dt = _parse_iso(it.get("DATA_UTWORZENIA", ""))
                cur = latest_by_id.get(id_towaru)
                if id_towaru and (cur is None or _parse_iso(cur.get("DATA_UTWORZENIA", "")) < dt):
                    latest_by_id[id_towaru] = it

        # Format results
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
        next_cursor = resp.get("LastEvaluatedKey") if partial else None

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
