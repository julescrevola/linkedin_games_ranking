[<img src="https://github.com/kubernetes/kubernetes/raw/master/logo/logo.png" width="50">](https://kubernetes.io/) [<img src="https://user-images.githubusercontent.com/7164864/217935870-c0bc60a3-6fc0-4047-b011-7b4c59488c91.png" alt="Streamlit logo" style="margin-top:50px"></img>](https://streamlit.io/)

[![Supabase](https://supabase.com/badge-made-with-supabase-dark.svg)](https://supabase.com)

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# LinkedIn Games Ranking

Ranking friends' scores on LinkedIn games, taking as input the `_chat.txt` extract of the WhatsApp chat in which we share results.
Find the Streamlit app [here](https://linkedin-games-ranking.com).

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

## Run the scripts

### Locally

To run the scripts, you have 2 options:
- If you wish, you can first run the parser script with (make sure that the input and output data paths are the right ones)
```bash
python linkedin_games_parser.py
```
This way, you can see what the parsed data looks like.

Then, you have 2 ways to run `ranking.py` and extract rankings:
- Create leaderboards for each game for the whole chat history:
```bash
python ranking.py
```
- Create leaderboards for each game for a specific day (**make sure to input the date in the format YYYY-MM-DD**):
```bash
python ranking.py --day <YYYY-MM-DD>
```
### As a Streamlit app

Configure Supabase credentials by copying `.streamlit/secrets.example.toml` and renaming it to `.streamlit/secrets.toml`, then filling in `SUPABASE_URL` and `SUPABASE_KEY` (for AKS) and/or `supabase-url` and `supabase-key` (for ACA).

Run in your terminal:
```bash
streamlit run ranking_app.py
```

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

## Connect to your domain

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

**You are ready to create your own ranking!**
