import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.captcha import CaptchaSolution, SEARCH_URL, solve_recaptcha

RESULTS_URL = "https://www.crecisp.gov.br/cidadao/listadecorretores"

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _headers(user_agent: str) -> dict:
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.crecisp.gov.br",
        "Referer": SEARCH_URL,
        "Cache-Control": "max-age=0",
    }


def _extract_names(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    names = []
    for heading in soup.select(".main-container h6"):
        if "dropdown-header" in (heading.get("class") or []):
            continue
        text = heading.get_text(strip=True)
        if text:
            names.append(text)
    return names


async def _submit_search(
    client: httpx.AsyncClient,
    formatted_cpf: str,
    captcha_token: str,
) -> httpx.Response:
    form_data = {
        "IsFinding": "True",
        "RegisterNumber": "",
        "CPF": formatted_cpf,
        "Name": "",
        "Area": "",
        "City": "",
        "Language": "",
        "Avaliador": "",
        "ReCAPTCHAToken": captcha_token,
    }
    response = await client.post(SEARCH_URL, data=form_data)

    if response.status_code in (301, 302, 303, 307, 308):
        location = response.headers.get("location", "")
        if location.startswith("/"):
            location = f"https://www.crecisp.gov.br{location}"
        if location:
            response = await client.get(location)

    return response


async def search_broker_by_cpf_http(
    formatted_cpf: str,
    solution: Optional[CaptchaSolution] = None,
) -> dict:
    captcha = solution or await solve_recaptcha()
    user_agent = captcha.user_agent or DEFAULT_USER_AGENT

    async with httpx.AsyncClient(
        headers=_headers(user_agent),
        follow_redirects=True,
        timeout=60,
    ) as client:
        await client.get(SEARCH_URL)
        response = await _submit_search(client, formatted_cpf, captcha.token)

    logger.info("HTTP search status=%s url=%s", response.status_code, response.url)

    if RESULTS_URL not in str(response.url):
        logger.warning("HTTP nao redirecionou para lista de corretores")
        return {
            "found": False,
            "cpf": formatted_cpf,
            "nome": None,
            "message": "Nenhum corretor encontrado para este CPF",
        }

    names = _extract_names(response.text)
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
