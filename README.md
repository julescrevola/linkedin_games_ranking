# LinkedIn Games Ranking

Ranking friends' scores on LinkedIn games, taking as input the `_chat.txt` extract of the WhatsApp chat in which we share results.
Find the published Streamlit app [here](https://linkedin-games-ranking.streamlit.app/).

## Clone repo

You can clone this repo running:
```bash
git clone https://github.com/julescrevola/linkedin_games_ranking.git
```

## Set up coding environment

To use this repo, first run:
```bash
source cli-aliases.sh
```
This will make sure that the aliases are loaded in your bash terminal.

You can then install the environment with:
```bash
envc
```
And you can update it with:
```bash
envu
```

To install pre-commit hooks, run:
```bash
pre-commit install
```

## Run the scripts

### In local:

To run the scripts, you have 2 options:
- If you wish, you can first run the parser script from `src/` with (make sure that the input and output data paths are the right ones)
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

Run in your terminal:
```bash
streamlit run src/ranking_app.py
```

**You are ready to create your own ranking!**
