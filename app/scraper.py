import asyncio
import logging
import os
import re

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

SEARCH_URL = "https://www.crecisp.gov.br/cidadao/buscaporcorretores"
RESULTS_URL = "https://www.crecisp.gov.br/cidadao/listadecorretores"
RECAPTCHA_SITE_KEY = "6LfUMMgqAAAAABG4tjE8VkT2wKZlqmAvV2YsId7a"
RECAPTCHA_ACTION = "submit_broker_search"
NAME_SELECTOR = ".main-container h6:not(.dropdown-header)"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_browser_lock = asyncio.Lock()
logger = logging.getLogger(__name__)


def normalize_cpf(cpf: str) -> str:
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11:
        raise ValueError("CPF deve conter 11 dígitos")
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def _max_attempts() -> int:
    return max(1, int(os.getenv("SCRAPER_MAX_ATTEMPTS", "3")))


def _browser_launch_options(headless: bool) -> dict:
    options = {"headless": headless}
    channel = os.getenv("PLAYWRIGHT_CHANNEL")
    if channel:
        options["channel"] = channel

    proxy = os.getenv("PLAYWRIGHT_PROXY")
    if proxy:
        options["proxy"] = {"server": proxy}

    if os.getenv("DOCKER", "false").lower() == "true":
        options["args"] = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--window-size=1280,720",
        ]

    return options


def _default_headless() -> bool:
    return os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"


async def _attempt_search(page, formatted_cpf: str) -> dict:
    await page.goto(SEARCH_URL, wait_until="networkidle", timeout=45000)
    await page.fill("#CPF", formatted_cpf)

    await page.wait_for_function(
        'typeof grecaptcha !== "undefined" && grecaptcha.enterprise',
        timeout=20000,
    )

    token = await page.evaluate(
        """async ([siteKey, action]) => {
            return await grecaptcha.enterprise.execute(siteKey, { action });
        }""",
        [RECAPTCHA_SITE_KEY, RECAPTCHA_ACTION],
    )

    if not token or len(token) < 100:
        logger.warning("Token reCAPTCHA invalido ou vazio")
        return {"found": False, "reason": "recaptcha_token_invalid"}

    async with page.expect_navigation(timeout=45000):
        await page.evaluate(
            """(token) => {
                if (typeof onSubmit === "function") {
                    onSubmit(token);
                    return;
                }
                document.getElementById("ReCAPTCHAToken").value = token;
                document.getElementById("IsFinding").value = "True";
                document.getElementById("buscaCorretoresForm").submit();
            }""",
            token,
        )

    await page.wait_for_load_state("networkidle", timeout=45000)

    if RESULTS_URL not in page.url:
        logger.warning("Nao redirecionou para lista. URL atual: %s", page.url)
        return {"found": False, "reason": "no_results_page"}

    names = [
        name.strip()
        for name in await page.locator(NAME_SELECTOR).all_text_contents()
        if name.strip()
    ]

    if not names:
        logger.warning("Pagina de resultados sem nomes")
        return {"found": False, "reason": "empty_results"}

    return {
        "found": True,
        "cpf": formatted_cpf,
        "nome": names[0],
        "message": "Corretor encontrado",
    }


async def _run_single_attempt(
    playwright,
    formatted_cpf: str,
    headless: bool,
) -> dict:
    browser = await playwright.chromium.launch(**_browser_launch_options(headless))
    context = await browser.new_context(
        user_agent=USER_AGENT,
        locale="pt-BR",
        viewport={"width": 1280, "height": 720},
    )
    await context.add_init_script(
        'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
    )
    page = await context.new_page()

    try:
        return await _attempt_search(page, formatted_cpf)
    finally:
        await context.close()
        await browser.close()


async def search_broker_by_cpf(cpf: str) -> dict:
    formatted_cpf = normalize_cpf(cpf)
    headless_modes = [_default_headless()]
    if headless_modes[0]:
        headless_modes.append(False)
    else:
        headless_modes.append(True)

    async with _browser_lock:
        async with async_playwright() as playwright:
            last_result = {
                "found": False,
                "cpf": formatted_cpf,
                "nome": None,
                "message": "Nenhum corretor encontrado para este CPF",
            }

            for attempt in range(1, _max_attempts() + 1):
                headless = headless_modes[(attempt - 1) % len(headless_modes)]
                logger.info(
                    "Tentativa %s/%s (headless=%s) para CPF %s",
                    attempt,
                    _max_attempts(),
                    headless,
                    formatted_cpf,
                )

                try:
                    result = await _run_single_attempt(
                        playwright,
                        formatted_cpf,
                        headless=headless,
                    )
                except PlaywrightTimeoutError as exc:
                    logger.warning("Timeout na tentativa %s: %s", attempt, exc)
                    continue
                except Exception as exc:
                    logger.warning("Erro na tentativa %s: %s", attempt, exc)
                    continue

                if result.get("found"):
                    return result

                last_result = {
                    "found": False,
                    "cpf": formatted_cpf,
                    "nome": None,
                    "message": "Nenhum corretor encontrado para este CPF",
                }

                if attempt < _max_attempts():
                    await asyncio.sleep(attempt * 2)

            return last_result
