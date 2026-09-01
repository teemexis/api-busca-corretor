import asyncio
import logging
import os

import httpx

SEARCH_URL = "https://www.crecisp.gov.br/cidadao/buscaporcorretores"
RESULTS_URL = "https://www.crecisp.gov.br/cidadao/listadecorretores"
RECAPTCHA_SITE_KEY = "6LfUMMgqAAAAABG4tjE8VkT2wKZlqmAvV2YsId7a"
RECAPTCHA_ACTION = "submit_broker_search"
CREATE_TASK_URL = "https://api.2captcha.com/createTask"
GET_TASK_URL = "https://api.2captcha.com/getTaskResult"

logger = logging.getLogger(__name__)


async def solve_recaptcha_token() -> str:
    api_key = os.getenv("TWOCAPTCHA_API_KEY")
    if not api_key:
        raise RuntimeError("TWOCAPTCHA_API_KEY nao configurada")

    payload = {
        "clientKey": api_key,
        "task": {
            "type": "RecaptchaV3TaskProxyless",
            "websiteURL": SEARCH_URL,
            "websiteKey": RECAPTCHA_SITE_KEY,
            "minScore": 0.9,
            "pageAction": RECAPTCHA_ACTION,
            "isEnterprise": True,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        create_response = await client.post(CREATE_TASK_URL, json=payload)
        create_response.raise_for_status()
        create_data = create_response.json()

        if create_data.get("errorId"):
            raise RuntimeError(
                f"2Captcha createTask falhou: {create_data.get('errorDescription')}"
            )

        task_id = create_data["taskId"]
        logger.info("2Captcha task criada: %s", task_id)

        for attempt in range(24):
            await asyncio.sleep(5)
            result_response = await client.post(
                GET_TASK_URL,
                json={"clientKey": api_key, "taskId": task_id},
            )
            result_response.raise_for_status()
            result_data = result_response.json()

            if result_data.get("errorId"):
                raise RuntimeError(
                    f"2Captcha getTaskResult falhou: {result_data.get('errorDescription')}"
                )

            if result_data.get("status") == "ready":
                token = result_data["solution"]["gRecaptchaResponse"]
                logger.info("2Captcha token obtido na tentativa %s", attempt + 1)
                return token

        raise RuntimeError("2Captcha timeout aguardando token")
