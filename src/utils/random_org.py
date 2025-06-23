import base64
import json
import urllib.parse
from random import randrange
from typing import Dict, Any
import httpx
from src.config import RANDOM_ORG_API_KEY
from src.utils.db import utc_now_ts


def b64e(s: str) -> str:
    sample_string = s
    sample_string_bytes = sample_string.encode("utf-8")
    base64_bytes = base64.b64encode(sample_string_bytes)
    base64_string = base64_bytes.decode("utf-8")
    return base64_string


async def get_random_numbers(
    num: int, min_val: int, max_val: int, player_id: int
) -> Dict[str, Any]:
    url = "https://api.random.org/json-rpc/4/invoke"

    metadata = f"player_id={player_id}&timestamp={utc_now_ts()}"

    payload = {
        "jsonrpc": "2.0",
        "method": "generateSignedIntegers",
        "params": {
            "apiKey": RANDOM_ORG_API_KEY,
            "n": num,
            "min": min_val,
            "max": max_val,
            "replacement": True,
            "pregeneratedRandomization": {"id": metadata},
        },
        "id": 1,
    }

    headers = {
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code == 200 and "signature" in response.text:
            response_data = response.json()
            random_data = response_data["result"]["random"]
            signature = response_data["result"]["signature"]

            random_org_check_form = (
                "https://api.random.org/signatures/form?format=json&random="
                + urllib.parse.quote_plus(
                    b64e(json.dumps(random_data, separators=(",", ":")))
                )
                + "&signature="
                + urllib.parse.quote_plus(signature)
            )

            result = {
                "is_random_org_result": True,
                "random_org_check_form": random_org_check_form,
                "data": random_data["data"],
                "random_org_result": json.dumps(response_data),
            }

            return result
        else:
            # Fallback
            data = [randrange(min_val, max_val + 1) for _ in range(num)]
            result = {
                "is_random_org_result": False,
                "random_org_check_form": None,
                "data": data,
                "random_org_result": response.text if response else None,
            }
            return result

    except Exception:
        # Fallback
        data = [randrange(min_val, max_val + 1) for _ in range(num)]
        result = {
            "is_random_org_result": False,
            "random_org_check_form": None,
            "data": data,
            "random_org_result": None,
        }
        return result
