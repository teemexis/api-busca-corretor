import asyncio
import os
import re

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

SEARCH_URL = "https://www.crecisp.gov.br/cidadao/buscaporcorretores"
RESULTS_URL = "https://www.crecisp.gov.br/cidadao/listadecorretores"
RECAPTCHA_SITE_KEY = "6LfUMMgqAAAAABG4tjE8VkT2wKZlqmAvV2YsId7a"
RECAPTCHA_ACTION = "submit_broker_search"
NAME_SELECTOR = ".main-container h6:not(.dropdown-header)"

_browser_lock = asyncio.Lock()


def normalize_cpf(cpf: str) -> str:
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11:
        raise ValueError("CPF deve conter 11 dígitos")
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def _browser_launch_options() -> dict:
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
    channel = os.getenv("PLAYWRIGHT_CHANNEL")
    options = {"headless": headless}
    if channel:
        options["channel"] = channel
    if os.getenv("DOCKER", "false").lower() == "true":
        options["args"] = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ]
    return options


async def search_broker_by_cpf(cpf: str) -> dict:
    formatted_cpf = normalize_cpf(cpf)

    async with _browser_lock:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**_browser_launch_options())
            page = await browser.new_page()

            try:
                await page.goto(SEARCH_URL, wait_until="networkidle")
                await page.fill("#CPF", formatted_cpf)

                await page.wait_for_function(
                    'typeof grecaptcha !== "undefined" && grecaptcha.enterprise',
                    timeout=15000,
                )

                token = await page.evaluate(
                    """async ([siteKey, action]) => {
                        return await grecaptcha.enterprise.execute(siteKey, { action });
                    }""",
                    [RECAPTCHA_SITE_KEY, RECAPTCHA_ACTION],
                )

                async with page.expect_navigation(timeout=30000):
                    await page.evaluate(
                        """(token) => {
                            document.getElementById('ReCAPTCHAToken').value = token;
                            document.getElementById('IsFinding').value = 'True';
                            document.getElementById('buscaCorretoresForm').submit();
                        }""",
                        token,
                    )

                await page.wait_for_load_state("networkidle")

                if RESULTS_URL not in page.url:
                    return {
                        "found": False,
                        "cpf": formatted_cpf,
                        "nome": None,
                        "message": "Nenhum corretor encontrado para este CPF",
                    }

                names = [
                    name.strip()
                    for name in await page.locator(NAME_SELECTOR).all_text_contents()
                    if name.strip()
                ]

                if not names:
                    return {
                        "found": False,
                        "cpf": formatted_cpf,
                        "nome": None,
                        "message": "Nenhum corretor encontrado para este CPF",
                    }

                return {
                    "found": True,
                    "cpf": formatted_cpf,
                    "nome": names[0],
                    "message": "Corretor encontrado",
                }
            except PlaywrightTimeoutError as exc:
                raise RuntimeError(
                    "Tempo esgotado ao consultar o site do CRECISP"
                ) from exc
            finally:
                await browser.close()
