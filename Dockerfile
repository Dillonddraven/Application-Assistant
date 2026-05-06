FROM python:3.13-slim

WORKDIR /app

# System deps for Playwright (PDF rendering + JS-rendered ATS fallback)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY profile/samples ./profile/samples
COPY .env.example ./.env.example

RUN pip install --no-cache-dir -e ".[ui]" \
    && playwright install --with-deps chromium

EXPOSE 8501

# Streamlit needs a writable home for its config
ENV HOME=/tmp \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "src/job_apply/ui/streamlit_app.py", \
     "--server.address=0.0.0.0", "--server.port=8501"]
