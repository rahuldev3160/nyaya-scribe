# Portable container image for Nyaya Scribe.
#
# Reproduces what Railway's Nixpacks builder + railway.toml already do today, so this
# app can be built and run identically on any Docker host (a VPS, AWS, etc.) whenever
# Rahul decides to move off Railway. This does NOT change how Railway deploys the app
# (Railway still uses NIXPACKS per railway.toml, not this file) -- it's a portability
# package that sits alongside the existing Railway setup, ready to use later.
#
# Build:
#   docker build -t nyaya-scribe .
#
# Run (mount a restored data backup as the volume -- never point this at Railway's
# live volume directly):
#   docker run -p 8080:8080 \
#     -v /path/to/restored/data:/app/data \
#     -e ANTHROPIC_API_KEY=... \
#     -e ARENA_SERVICE_API_KEY=... \
#     nyaya-scribe

FROM python:3.11-slim

# matplotlib/pillow (requirements.txt) sometimes need these at build time on
# platforms without prebuilt wheels -- cheap to include, avoids a silent build failure
# on a new host's architecture.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg-dev \
        zlib1g-dev \
        libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The 7 real SQLite DB files (ies.db, rbi.db, upsc.db, upsc_eco_opt.db, nyaya.db,
# english.db, upsc_gs.db) live here. Matches Railway's volume mount path exactly
# (see railway.toml's comment) so a restored backup can be bind-mounted straight in.
# Never baked into the image -- see .dockerignore.
VOLUME /app/data

# Railway injects $PORT; default to 8080 for standalone/local use.
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python3 -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/healthz', timeout=5)" || exit 1

# Same startCommand as railway.toml's [deploy] section -- migrations run once before
# gunicorn boots. sh -c so $PORT expands at container start, not build time.
CMD sh -c "python3 scripts/migrate.py && gunicorn --chdir web 'wsgi:app' --bind 0.0.0.0:$PORT --workers 2 --timeout 120"
