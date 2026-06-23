# LinkedIn Games Ranking

Ranking friends' scores on LinkedIn games, taking as input the `_chat.txt` extract of the WhatsApp chat in which we share results.
Find the app [here](https://linkedin-games-ranking.com).

Total scores are computed by awarding the following points, per game per day:
- 5 points for the best player
- 3 points for the second-best player
- 1 point for the third-best player

The sum of points must always be 9, so draws are dealt with in the following way:
- If the ranking is 1-1-1, then each player gets (5+3+1)/3 = 3
- If the ranking is 1-1-3, then the first two players get (5+3)/2 = 4 each, the third gets 1
- If the ranking is 1-2-2, then the first player gets 5 and the next two players get (3+1)/2 = 2 each
- If the ranking is 1-2-2-2, then the first player gets 5 and the next players get (3+1)/3 = 1.33 each

And so on.

## Project Structure

```
├── src/                    # Python backend (FastAPI)
│   ├── api/                # API routes (leaderboard, head-to-head, upload)
│   │   ├── routes/
│   │   └── services/
│   └── linkedin_games_parser.py  # WhatsApp chat parser
├── frontend/               # React + Vite + TailwindCSS frontend
│   └── src/
│       ├── components/     # DataTable, WinBar, WinOverTimeChart
│       └── pages/          # LeaderboardPage, HeadToHeadPage
├── nginx/                  # Nginx reverse proxy + Let's Encrypt
│   └── conf.d/             # app.conf (HTTPS), init-letsencrypt.conf
├── azure/                  # Azure DevOps pipeline
├── .github/workflows/      # GitHub Actions CI/CD
├── kubernetes/             # AKS deployment manifests
├── docker-compose.yml      # API container
├── Dockerfile              # Python API image
└── cli-aliases.sh          # All deployment & dev helper commands
```

## Clone repo

You can clone this repo running:
```bash
git clone https://github.com/julescrevola/linkedin_games_ranking.git
```

## Set up coding environment

To use this repo, first [install uv](https://docs.astral.sh/uv/getting-started/installation/).
Then, run:
```bash
source cli-aliases.sh
```
This loads helper bash functions in your terminal.

You can then install the environment with:
```bash
envc
```

And when coming back to the code later, you can reactivate the environment with:
```bash
enva
```

To deactivate the environment, run:
```bash
deactivate
```

To install pre-commit hooks, run:
```bash
pre-commit install
```

## Run locally

Start the FastAPI backend:
```bash
dev_api
```

In a separate terminal, start the React frontend:
```bash
dev_frontend
```

The API runs on `http://localhost:8000` and the frontend on `http://localhost:5173`.

## Deploy to Scaleway VPS

The app is currently deployed on a Scaleway instance with Docker, nginx as reverse proxy, and Let's Encrypt for SSL.

### First-time server setup

```bash
source cli-aliases.sh
setup_scaleway
```

This installs Docker on the server and clones the repo.

### Deploy

```bash
deploy_scaleway
```

This builds and pushes the Docker image, then SSHes into the server to pull and restart containers.

### Manual deployment on the server

```bash
docker_host
```

This runs directly on the server: creates the Docker network, starts the API, handles SSL cert issuance via certbot, and starts nginx.

### DNS Setup

Point your domain's A record to the Scaleway instance's public IP. The certbot step in `docker_host` will obtain the SSL certificate automatically.

## Deploy to your own Kubernetes cluster or Azure Container App

**This repo is using an [Azure Container App](https://learn.microsoft.com/fr-fr/azure/container-apps/) or a Kubernetes cluster deployed in Azure with [Azure Kubernetes Services](https://learn.microsoft.com/en-us/azure/aks/), feel free to provision a cluster with another method and change the code accordingly for your usage.**

First, [install Docker Engine](https://docs.docker.com/engine/install/) if you are on Linux, or [install Docker Desktop](https://docs.docker.com/desktop/) if you are on Windows or Mac.
Provision ACA or AKS in Azure, either manually in the Azure Portal or with Azure CLI.

Load helpers with:
```bash
source cli-aliases.sh
```
Make sure Docker is running, then run:
- `deploy_aca` for Azure Container Apps
- `deploy_aks` for AKS

These commands build and push the Docker image, then create or update the target deployment.

You can then go to the URL displayed in the terminal when the deployment is done and you will see your app.

### Connect to your domain

If you have bought a domain name (I got mine on [GoDaddy](https://www.godaddy.com/)), you can connect to it so that you use HTTPS instead of HTTP.

**Make sure to rename `.env.example` to `.env`, fill in required variables, and load them with `source .env`.**

First, provision an Azure DNS Zone with:
```bash
az network dns zone create --resource-group $DNS_ZONE_RG --name $DNS_ZONE_NAME
```
Then, go to your domain provider, and in Name Servers, add the following 4 URLs (remove all the others):
```txt
ns1-01.azure-dns.com
ns2-01.azure-dns.net
ns3-01.azure-dns.org
ns4-01.azure-dns.info
```
This will ensure that DNS is dealt with by Azure directly.

Make sure helpers are loaded with `source cli-aliases.sh`, then run:
- `host_aks` for AKS
- `host_aca` for ACA

For reference, I helped myself with these for AKS:
- https://dev.to/aadarsh-nagrath/setting-up-https-on-kubernetes-with-cert-manager-and-lets-encrypt-45e6
- https://dev.to/peterj/expose-a-kubernetes-service-on-your-own-custom-domain-52dd


## CI/CD

Both pipelines trigger on push to `main`: build Docker image → push to Docker Hub → deploy to Scaleway/AKS/ACA.

- **GitHub Actions**: `.github/workflows/ci-cd.yml`
- **Azure DevOps**: `azure/azure-pipelines.yml`

**You are ready to create your own ranking!**
