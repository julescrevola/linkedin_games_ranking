FROM python:3.11-slim

# Set working directory
WORKDIR /linkedin_games_ranking

# Copy app files to the container
COPY . /linkedin_games_ranking/

# Install dependencies
RUN pip install -r requirements.txt

# Expose the port Streamlit runs on
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "ranking_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
