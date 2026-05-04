[![Supabase](https://supabase.com/badge-made-with-supabase-dark.svg)](https://supabase.com)

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# LinkedIn Games Ranking

Ranking friends' scores on LinkedIn games, taking as input the `_chat.txt` extract of the WhatsApp chat in which we share results.
Find the Streamlit app [here](http://20.103.37.32:80).

Total score are computed by awarding the following points, per game per day:
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
This will make sure that the aliases are loaded in your bash terminal.

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

### In local:

To run the scripts, you have 2 options:
- If you wish, you can first run the parser script with (make sure that the input and output data paths are the right ones)
```bash
python linkedin_games_parser.py
```
This way, you can see what the parsed data looks like.

Then, you have 2 ways to run the `ranking.py` file and extract rankings:
- Create leaderboards for each game for the whole chat history:
```bash
python ranking.py
```
- Create leaderboards for each game for a specific day (**make sure to input the date in the format YYYY-MM-DD**):
```bash
python ranking.py --day <YYYY-MM-DD>
```
### As a Streamlit app

First, set up the file `.streamlit/secrets.toml`, in which you put your SUPABASE_URL and SUPABASE_KEY from your Supabase account. To do so, you can copy `.streamlit.secrets.example.toml` and rename it, then change the values inside.

Run in your terminal:
```bash
streamlit run ranking_app.py
```

### Deploy to your own Kubernetes cluster

**This repo is using a Kubernetes cluster deployed in Azure with [Azure Kubernetes Services](https://learn.microsoft.com/en-us/azure/aks/), feel free to provision a cluster with other method and change the code accordingly for your usage.**

First, [install Docker Engine](https://docs.docker.com/engine/install/) if you are on Linux, or [install Docker Desktop](https://docs.docker.com/desktop/) if you are on Windows or Mac.
Provision the AKS in Azure, either manually on your Azure Portal or [with the Azure CLI](https://learn.microsoft.com/en-us/azure/aks/learn/quick-windows-container-deploy-cli#create-an-aks-cluster).

Remember to load aliases with:
```bash
source cli-aliases.sh
```
Then run `deploy`. It will create a new deployment names *linkedin-games-ranking* in your AKS cluster if it is the first time you set it up, or it will update it if it already exists.

You can then go to the URL displayed in the terminal when the deployment is done and you will see your app.

### Connect to your domain

If you have bought a domain name (I got mine on [GoDaddy](https://www.godaddy.com/)), you can connect to it so that you use HTTPS instead of HTTP.

**Make sure to rename `.env.example` to `.env`, fill in the empty variables and load them in your terminal with `source .env`.**

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

Make sure that you still have aliases loaded in the terminal with `source cli_aliases.sh`, then run the command `host` in your terminal.

For reference, I helped myself with these:
- https://dev.to/aadarsh-nagrath/setting-up-https-on-kubernetes-with-cert-manager-and-lets-encrypt-45e6
- https://dev.to/peterj/expose-a-kubernetes-service-on-your-own-custom-domain-52dd

**You are ready to create your own ranking!**
