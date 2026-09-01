# API Busca Corretor CRECISP

API em FastAPI que consulta corretores de imóveis no site do [CRECISP](https://www.crecisp.gov.br/cidadao/buscaporcorretores) por CPF.

## Resposta da API

| Situação | Retorno |
|---|---|
| Corretor encontrado | `"NOME DO CORRETOR"` |
| CPF inválido | `false` |
| CPF não encontrado na base | `false` |

## Endpoints

- `GET /health`
- `GET /buscar-corretor?cpf=386.875.748-19`
- `POST /buscar-corretor` com body `{"cpf":"386.875.748-19"}`
- `GET /docs` — Swagger

## Deploy na VPS (EasyPanel + GitHub)

Guia completo: **[DEPLOY.md](./DEPLOY.md)**

Resumo:

1. Suba este repositório no GitHub
2. No EasyPanel: **Add Service → App → GitHub**
3. Build: **Dockerfile** | Porta: **8000**
4. Variáveis de ambiente:

```env
PORT=8000
DISPLAY=:99
DOCKER=true
PLAYWRIGHT_HEADLESS=false
```

5. Deploy e configure domínio com HTTPS

## Desenvolvimento local

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Teste:

```bash
curl "http://localhost:8000/buscar-corretor?cpf=386.875.748-19"
```

## Docker local

```bash
docker compose up -d --build
curl "http://localhost:8000/health"
```

## Observação sobre reCAPTCHA

O site usa Google reCAPTCHA Enterprise. A automação roda com navegador visível via Xvfb no Docker (`PLAYWRIGHT_HEADLESS=false`).

Em VPS com IP de datacenter, o reCAPTCHA pode falhar ocasionalmente.

## Requisitos recomendados (VPS)

- 2 vCPU / 4 GB RAM
- Ubuntu 22.04+
- Docker
