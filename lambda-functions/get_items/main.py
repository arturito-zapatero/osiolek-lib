import os
from decimal import Decimal
import unicodedata
from rapidfuzz import process, fuzz
import boto3, json, traceback
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

def _norm_id(v) -> str:
    """Normalize ID_TOWARU to string for consistent set membership."""
    if isinstance(v, Decimal):
        v = int(v) if v % 1 == 0 else float(v)
    return str(v) if v is not None else ""

def _get_allowed_ids_for_warehouse(warehouse_id: str, limit: int = 5000) -> set:
    """Query akt_stan_mag GSI for items available in given warehouse."""
    print(json.dumps({
        "stage": "query_stock_start",
        "table": AKT_STAN_MAG_TABLE,
        "gsi": AKT_STAN_MAG_GSI,
        "warehouse_id": warehouse_id,
        "limit": limit
    }))
    allowed = set()
    try:
        kwargs = {
            "IndexName": AKT_STAN_MAG_GSI,
            "KeyConditionExpression": Key("ID_MAGAZYNU").eq(warehouse_id),
            "FilterExpression": Attr("ILOSC").gt(0),  # only in-stock
            "ProjectionExpression": "ID_TOWARU, ILOSC",
            "Limit": min(limit, 1000)  # page size
        }
        resp = stock_tbl.query(**kwargs)
        for it in resp.get("Items", []):
            allowed.add(_norm_id(it.get("ID_TOWARU")))
        while "LastEvaluatedKey" in resp and len(allowed) < limit:
            resp = stock_tbl.query(**kwargs, ExclusiveStartKey=resp["LastEvaluatedKey"])
            for it in resp.get("Items", []):
                allowed.add(_norm_id(it.get("ID_TOWARU")))
    except Exception as e:
        print(json.dumps({
            "stage": "query_stock_error",
            "error": str(e),
            "trace": traceback.format_exc()
        }))
        raise
    print(json.dumps({
        "stage": "query_stock_done",
        "allowed_count": len(allowed),
        "sample_ids": list(sorted(list(allowed))[:5])
    }))
    return allowed

def lambda_handler(event, context):
    try:
        qs = (event or {}).get("queryStringParameters") or {}
        headers = (event or {}).get("headers") or {}
        debug = str(qs.get("debug", "false")).lower() in ("1","true","yes")

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
        max_pages = int(qs.get("max_pages", MAX_SCAN_PAGES))
        max_ids   = int(qs.get("max_ids", 5000))

        if not term:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing 'query' parameter."}),
            }

        print(json.dumps({
            "stage": "input",
            "warehouse_id": warehouse_id,
            "term": term,
            "cutoff": cutoff,
            "limit": limit,
            "max_pages": max_pages,
            "max_ids": max_ids
        }))

        # 1) Get the set of allowed item IDs for this warehouse
        allowed_ids = _get_allowed_ids_for_warehouse(warehouse_id, max_ids)
        if not allowed_ids:
            payload = {"results": [], "next_cursor": None}
            if debug:
                payload["debug"] = {"allowed_ids_count": 0}
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps(payload),
            }

        # 2) Scan items table, but keep only allowed IDs (fast set check)
        items = []
        scan_kwargs = {"ProjectionExpression": PROJECTION}
        pages = 0
        total_scanned = 0
        while True:
            resp = items_tbl.scan(**scan_kwargs)
            batch = resp.get("Items", [])
            total_scanned += len(batch)

            # keep only items from this warehouse's stock
            kept_in_batch = 0
            for it in batch:
                if _norm_id(it.get("ID_TOWARU")) in allowed_ids:
                    items.append(it)
                    kept_in_batch += 1

            pages += 1
            print(json.dumps({
                "stage": "scan_items_page",
                "page": pages,
                "batch": len(batch),
                "kept_in_batch": kept_in_batch,
                "kept_total": len(items)
            }))

            if len(items) >= MAX_SCAN_ITEMS or pages >= max_pages:
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
        print(json.dumps({
            "stage": "pre_fuzzy",
            "candidates_count": sum(len(v) for v in name_to_items.values()),
            "unique_names": len(name_to_items)
        }))

        print(json.dumps({
            "stage": "candidate_names_sample",
            "sample": list(name_to_items.keys())[:10]
        }))

        # 4) Fuzzy match on the reduced candidate set (more tolerant + fallbacks)
        names = list(name_to_items.keys())

        def best_score(q, s):
            # try multiple strategies and take the max
            return max(
                fuzz.token_set_ratio(q, s),
                fuzz.token_sort_ratio(q, s),
                fuzz.partial_ratio(q, s),
            )

        # allow overriding cutoff via query; default softer 55
        effective_cutoff = int(qs.get("cutoff", cutoff if cutoff is not None else 55))
        scores = []
        for nm in names:
            sc = best_score(term_norm, nm)
            if sc >= effective_cutoff:
                scores.append((nm, sc))

        # If still nothing, do a simple substring fallback (accent/case normalized)
        if not scores:
            subs = [nm for nm in names if term_norm in nm]
            # as a second fallback, prefix match on tokens
            if not subs:
                subs = [
                    nm for nm in names
                    if any(tok.startswith(term_norm) for tok in nm.split())
                ]
            scores = [(nm, 100) for nm in subs]  # treat as strong matches

        # sort by score desc, then name
        scores.sort(key=lambda t: (-t[1], t[0]))
        # cap to 'limit'
        scores = scores[:limit]

        if debug:
            print(json.dumps({
                "stage": "post_match_scored",
                "matches_count": len(scores),
                "top5": scores[:5]
            }))

        # 5) Latest item per ID_TOWARU among matched names
        latest_by_id = {}
        for match_name, sc in scores:
            for it in name_to_items.get(match_name, []):
                id_towaru = _norm_id(it.get("ID_TOWARU"))
                dt = _parse_iso(it.get("DATA_UTWORZENIA", ""))
                cur = latest_by_id.get(id_towaru)
                if id_towaru and (cur is None or _parse_iso(cur.get("DATA_UTWORZENIA", "")) < dt):
                    latest_by_id[id_towaru] = it

        # 6) Format results
        seen = set()
        results = []
        for match_name, _ in scores:
            for it in name_to_items.get(match_name, []):
                id_t = _norm_id(it.get("ID_TOWARU"))
                if id_t in latest_by_id and id_t not in seen:
                    v = latest_by_id[id_t]
                    results.append({
                        "ID_TOWARU": v.get("ID_TOWARU"),
                        "NAZWA_TOWARU": v.get("NAZWA_TOWARU"),
                    })
                    seen.add(id_t)

        partial = pages >= max_pages or len(items) >= MAX_SCAN_ITEMS
        next_cursor = None  # not meaningful post-filter

        body = {"results": results, "next_cursor": next_cursor}
        if debug:
            body["debug"] = {
                "allowed_ids_count": len(allowed_ids),
                "items_kept": len(items),
                "total_scanned": total_scanned,
                "pages": pages,
                "unique_names": len(name_to_items),
                "matches_count": len(scores),
                "warehouse_id": warehouse_id
            }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "X-Partial-Results": "true" if partial else "false",
            },
            "body": json.dumps(body, default=_json_default),
        }

    except Exception as e:
        print(json.dumps({"stage":"exception","error":str(e),"trace":traceback.format_exc()}))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
