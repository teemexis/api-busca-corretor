import logging

from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.captcha import RESULTS_URL, SEARCH_URL, solve_recaptcha_token

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://www.crecisp.gov.br",
    "Referer": SEARCH_URL,
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


async def search_broker_by_cpf_http(
    formatted_cpf: str, token: Optional[str] = None
) -> dict:
    captcha_token = token or await solve_recaptcha_token()

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

    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=60,
    ) as client:
        await client.get(SEARCH_URL)
        response = await client.post(SEARCH_URL, data=form_data)

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
