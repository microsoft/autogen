FROM python:3.11 AS build

WORKDIR /app

COPY . .

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
   && apt-get upgrade -y  \
   && apt-get -y install --no-install-recommends build-essential npm rsync \
   && apt-get autoremove -y \
   && apt-get clean -y \
   && rm -rf /var/lib/apt/lists/*
ENV DEBIAN_FRONTEND=dialog

# For docs
RUN npm install --global yarn
RUN npm install --global gatsby-cli
RUN pip install --upgrade pip

# Install global npm packages
RUN gatsby telemetry --disable
RUN apt-get clean -y \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Install Python packages using venv
RUN python -m venv autogen-venv
ENV PATH="/app/autogen-venv/bin:$PATH"
RUN pip install -e . --trusted-host pypi.org --trusted-host files.pythonhosted.org
RUN pip install gunicorn

# Build frontend
WORKDIR /app/frontend
RUN yarn install --ignore-engines
RUN yarn build

# --- FINAL STAGE ---
FROM python:3.11-slim

WORKDIR /app

# Copy only necessary files from the build stage
COPY --from=build /app /app
RUN chmod u+x ./entrypoint.sh

ENV PATH="/app/autogen-venv/bin:$PATH"

CMD gunicorn -w $((2 * $(getconf _NPROCESSORS_ONLN) + 1)) --timeout 12600 -k uvicorn.workers.UvicornWorker autogenstudio.web.app:app --bind "0.0.0.0:8081"
