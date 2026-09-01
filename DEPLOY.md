# Deploy no EasyPanel (VPS)

Guia para publicar esta API em uma VPS usando [EasyPanel](https://easypanel.io/) com deploy via GitHub.

## Requisitos da VPS

- Ubuntu 22.04+ (recomendado)
- Mínimo: **2 vCPU** e **4 GB RAM**
- Docker instalado (EasyPanel já gerencia isso)
- Porta 80/443 liberadas para o domínio

## 1. Subir o projeto no GitHub

```bash
cd "API busca corretor"
git init
git add .
git commit -m "API busca corretor CRECISP com deploy Docker"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/api-busca-corretor.git
git push -u origin main
```

Substitua `SEU_USUARIO/api-busca-corretor` pelo seu repositório.

## 2. Criar app no EasyPanel

1. Acesse o painel do EasyPanel na sua VPS
2. Crie um **novo projeto** (ex: `corretor`)
3. Clique em **Add Service** → **App**
4. Escolha **GitHub** como fonte
5. Conecte/autorize sua conta GitHub
6. Selecione o repositório `api-busca-corretor`
7. Branch: `main`

## 3. Configurar build

| Campo | Valor |
|---|---|
| Build method | **Dockerfile** |
| Dockerfile path | `Dockerfile` |
| Port | `8000` |

O EasyPanel detecta o `Dockerfile` na raiz do repositório.

## 4. Variáveis de ambiente

No EasyPanel, adicione:

```env
PORT=8000
DISPLAY=:99
DOCKER=true
PLAYWRIGHT_HEADLESS=false
```

Copie de `.env.example` se preferir.

## 5. Recursos do container

Recomendado no EasyPanel:

- **Memory limit:** 2 GB (ideal 4 GB)
- **Shared memory (shm):** se houver opção, use `1gb`
  - No `docker-compose.yml` local já está `shm_size: 1gb`

Se o EasyPanel usar apenas Dockerfile (sem compose), o Chromium ainda funciona com `--disable-dev-shm-usage` (já configurado no código).

## 6. Domínio e HTTPS

1. No serviço, vá em **Domínios**
2. Adicione seu domínio (ex: `api.seudominio.com.br`)
3. Configure a **porta alvo (target port): `8000`**
4. Ative **HTTPS** (Let's Encrypt automático no EasyPanel)
5. Aponte o DNS (A record) para o IP da VPS

> Se a porta alvo não for `8000`, o EasyPanel fica em loop:
> `Waiting for service ... to start`

## 7. Deploy

1. Clique em **Deploy**
2. Aguarde o build (primeira vez pode levar 3–5 minutos)
3. Verifique os logs até aparecer: `Application startup complete`

## 8. Testar

```bash
curl "https://api.seudominio.com.br/health"
# {"status":"ok"}

curl "https://api.seudominio.com.br/buscar-corretor?cpf=386.875.748-19"
# "THIAGO MACHADO XAVIER" ou false
```

Documentação interativa: `https://api.seudominio.com.br/docs`

## Deploy alternativo com Docker Compose

Se preferir subir manualmente na VPS:

```bash
git clone https://github.com/SEU_USUARIO/api-busca-corretor.git
cd api-busca-corretor
cp .env.example .env
docker compose up -d --build
```

API disponível em `http://IP_DA_VPS:8000`.

## Como funciona no container

```text
start.sh
  ├── inicia Xvfb (display virtual :99)
  └── inicia Uvicorn na porta 8000
        └── Playwright abre Chromium "visível" via Xvfb
              └── consulta o site do CRECISP
```

## Troubleshooting

### Build falha por memória
- Aumente RAM da VPS ou limite de memória do serviço para 4 GB

### API retorna 502 / timeout
- Verifique logs do container no EasyPanel
- Confirme `PLAYWRIGHT_HEADLESS=false` e `DISPLAY=:99`
- reCAPTCHA pode bloquear IP de datacenter — tente redeploy ou outro horário

### Container reinicia sozinho
- Chromium consome bastante RAM; aumente limite para 2–4 GB

### Health check falhando
- Aguarde ~60s após deploy (start period do healthcheck)
- Teste manualmente: `curl http://localhost:8000/health` dentro do container

## Atualizações

Após push no GitHub:

1. EasyPanel → seu serviço → **Deploy** (ou redeploy automático se configurado)
2. O painel rebuilda a imagem e reinicia o container

## Estrutura de deploy

```text
.
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── scripts/start.sh
└── app/
    ├── main.py
    └── scraper.py
```
