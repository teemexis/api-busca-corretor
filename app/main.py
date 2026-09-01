from typing import Union

import logging

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app.scraper import normalize_cpf, search_broker_by_cpf

app = FastAPI(
    title="API Busca Corretor CRECISP",
    description="Consulta corretores de imóveis no site do CRECISP por CPF",
    version="1.0.0",
)

logging.basicConfig(level=logging.INFO)


class BrokerSearchRequest(BaseModel):
    cpf: str = Field(..., examples=["386.875.748-19"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/buscar-corretor", response_model=Union[str, bool])
async def buscar_corretor_get(cpf: str = Query(..., description="CPF do corretor")):
    return await _search(cpf)


@app.post("/buscar-corretor", response_model=Union[str, bool])
async def buscar_corretor_post(body: BrokerSearchRequest):
    return await _search(body.cpf)


async def _search(cpf: str) -> Union[str, bool]:
    try:
        normalize_cpf(cpf)
    except ValueError:
        return False

    try:
        result = await search_broker_by_cpf(cpf)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao consultar o site do CRECISP: {exc}",
        ) from exc

    if result["found"]:
        return result["nome"]

    return False
