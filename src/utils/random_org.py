import base64
import json
import urllib.parse
from random import randrange
import httpx
from pydantic import BaseModel
from src.config import RANDOM_ORG_API_KEY
from src.utils.db import utc_now_ts, log_error_to_db
from src.db import get_session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def b64e(s: str) -> str:
    sample_string = s
    sample_string_bytes = sample_string.encode("utf-8")
    base64_bytes = base64.b64encode(sample_string_bytes)
    base64_string = base64_bytes.decode("utf-8")
    return base64_string


class RandomResult(BaseModel):
    is_random_org_result: bool
    random_org_check_form: str | None
    data: list[int]
    random_org_response: str | None


async def get_random_numbers(
    num: int, min_val: int, max_val: int, player_id: int
) -> RandomResult:
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

            quoted_signature = urllib.parse.quote_plus(signature)
            data_string = json.dumps(random_data, separators=(",", ":"))
            b64_encoded_data = b64e(data_string)
            quoted_data = urllib.parse.quote_plus(b64_encoded_data)

            random_org_check_form = f"https://api.random.org/signatures/form?format=json&random={quoted_data}&signature={quoted_signature}"

            result = RandomResult(
                is_random_org_result=True,
                random_org_check_form=random_org_check_form,
                data=random_data["data"],
                random_org_response=json.dumps(response_data),
            )

            return result
        else:
            error_message = f"Random.org API error: status_code={response.status_code}, has_signature={'signature' in response.text}"
            logger.error(error_message)

            try:
                async with get_session() as session:
                    error = Exception(error_message)
                    await log_error_to_db(
                        session=session,
                        error=error,
                        function_name="get_random_numbers",
                        player_id=player_id,
                        context=f"num={num}, min_val={min_val}, max_val={max_val}, response_text={response.text[:200] if response else 'None'}",
                    )
            except Exception as db_error:
                logger.error(f"Failed to log error to database: {db_error}")

            data = [randrange(min_val, max_val + 1) for _ in range(num)]
            result = RandomResult(
                is_random_org_result=False,
                random_org_check_form=None,
                data=data,
                random_org_response=response.text if response else None,
            )
            return result

    except Exception as e:
        logger.error(f"Dice roll exception: {e}")

        try:
            async with get_session() as session:
                await log_error_to_db(
                    session=session,
                    error=e,
                    function_name="get_random_numbers",
                    player_id=player_id,
                    context=f"num={num}, min_val={min_val}, max_val={max_val}",
                )
        except Exception as db_error:
            logger.error(f"Failed to log error to database: {db_error}")

        data = [randrange(min_val, max_val + 1) for _ in range(num)]
        result = RandomResult(
            is_random_org_result=False,
            random_org_check_form=None,
            data=data,
            random_org_response=None,
        )
        return result
