import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Callable, List, Optional

import httpx

SEARCH_URL = "https://www.crecisp.gov.br/cidadao/buscaporcorretores"
RECAPTCHA_SITE_KEY = "6LfUMMgqAAAAABG4tjE8VkT2wKZlqmAvV2YsId7a"
RECAPTCHA_ACTION = "submit_broker_search"

CAPSOLVER_CREATE_URL = "https://api.capsolver.com/createTask"
CAPSOLVER_RESULT_URL = "https://api.capsolver.com/getTaskResult"
TWOCAPTCHA_CREATE_URL = "https://api.2captcha.com/createTask"
TWOCAPTCHA_RESULT_URL = "https://api.2captcha.com/getTaskResult"

logger = logging.getLogger(__name__)


@dataclass
class CaptchaSolution:
    token: str
    user_agent: Optional[str] = None


def _capsolver_key() -> Optional[str]:
    return os.getenv("CAPSOLVER_API_KEY")


def _twocaptcha_key() -> Optional[str]:
    return os.getenv("TWOCAPTCHA_API_KEY")


async def _poll_task_result(
    provider: str,
    client: httpx.AsyncClient,
    create_url: str,
    result_url: str,
    create_payload: dict,
    parse_solution: Callable[[dict], CaptchaSolution],
) -> CaptchaSolution:
    create_response = await client.post(create_url, json=create_payload)
    create_response.raise_for_status()
    create_data = create_response.json()

    if create_data.get("errorId"):
        raise RuntimeError(
            f"{provider} createTask falhou: {create_data.get('errorDescription')}"
        )

    task_id = create_data["taskId"]
    logger.info("%s task criada: %s", provider, task_id)

    client_key = create_payload["clientKey"]
    for attempt in range(30):
        await asyncio.sleep(3)
        result_response = await client.post(
            result_url,
            json={"clientKey": client_key, "taskId": task_id},
        )
        result_response.raise_for_status()
        result_data = result_response.json()

        if result_data.get("errorId"):
            raise RuntimeError(
                f"{provider} getTaskResult falhou: {result_data.get('errorDescription')}"
            )

        if result_data.get("status") == "ready":
            solution = parse_solution(result_data["solution"])
            logger.info("%s token obtido na tentativa %s", provider, attempt + 1)
            return solution

    raise RuntimeError(f"{provider} timeout aguardando token")


def _parse_capsolver_solution(solution: dict) -> CaptchaSolution:
    token = solution.get("gRecaptchaResponse") or solution.get("token")
    if not token:
        raise RuntimeError("CapSolver nao retornou token")
    return CaptchaSolution(
        token=token,
        user_agent=solution.get("userAgent"),
    )


def _parse_twocaptcha_solution(solution: dict) -> CaptchaSolution:
    return CaptchaSolution(token=solution["gRecaptchaResponse"])


async def _solve_with_capsolver_task(api_key: str, task: dict) -> CaptchaSolution:
    payload = {"clientKey": api_key, "task": task}
    async with httpx.AsyncClient(timeout=90) as client:
        return await _poll_task_result(
            provider=f"CapSolver({task['type']})",
            client=client,
            create_url=CAPSOLVER_CREATE_URL,
            result_url=CAPSOLVER_RESULT_URL,
            create_payload=payload,
            parse_solution=_parse_capsolver_solution,
        )


async def _solve_with_capsolver(api_key: str) -> CaptchaSolution:
    last_error: Optional[Exception] = None
    for task in _capsolver_tasks():
        try:
            return await _solve_with_capsolver_task(api_key, task)
        except Exception as exc:
            last_error = exc
            logger.warning("CapSolver falhou com %s: %s", task["type"], exc)

    raise RuntimeError(f"CapSolver nao conseguiu resolver captcha: {last_error}")


def _capsolver_tasks() -> list[dict]:
    return [
        {
            "type": "ReCaptchaV3EnterpriseTaskProxyLess",
            "websiteURL": SEARCH_URL,
            "websiteKey": RECAPTCHA_SITE_KEY,
            "pageAction": RECAPTCHA_ACTION,
        },
        {
            "type": "ReCaptchaV2EnterpriseTaskProxyLess",
            "websiteURL": SEARCH_URL,
            "websiteKey": RECAPTCHA_SITE_KEY,
            "isInvisible": True,
        },
        {
            "type": "ReCaptchaV2EnterpriseTaskProxyLess",
            "websiteURL": SEARCH_URL,
            "websiteKey": RECAPTCHA_SITE_KEY,
        },
    ]


async def iter_captcha_solutions():
    capsolver_key = _capsolver_key()
    if capsolver_key:
        for task in _capsolver_tasks():
            try:
                yield await _solve_with_capsolver_task(capsolver_key, task)
            except Exception as exc:
                logger.warning("CapSolver falhou com %s: %s", task["type"], exc)
        return

    twocaptcha_key = _twocaptcha_key()
    if twocaptcha_key:
        yield await _solve_with_twocaptcha(twocaptcha_key)
        return

    raise RuntimeError(
        "Configure CAPSOLVER_API_KEY ou TWOCAPTCHA_API_KEY nas variaveis de ambiente"
    )


async def _solve_with_twocaptcha(api_key: str) -> CaptchaSolution:
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

    async with httpx.AsyncClient(timeout=90) as client:
        return await _poll_task_result(
            provider="2Captcha",
            client=client,
            create_url=TWOCAPTCHA_CREATE_URL,
            result_url=TWOCAPTCHA_RESULT_URL,
            create_payload=payload,
            parse_solution=_parse_twocaptcha_solution,
        )


async def solve_recaptcha() -> CaptchaSolution:
    capsolver_key = _capsolver_key()
    if capsolver_key:
        return await _solve_with_capsolver(capsolver_key)

    twocaptcha_key = _twocaptcha_key()
    if twocaptcha_key:
        return await _solve_with_twocaptcha(twocaptcha_key)

    raise RuntimeError(
        "Configure CAPSOLVER_API_KEY ou TWOCAPTCHA_API_KEY nas variaveis de ambiente"
    )
