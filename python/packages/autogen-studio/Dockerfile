FROM python:3.10-slim

# 1. Install build-tools if you have any compiled deps
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

# 2. Create and switch to a non-root user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    AUTOGENSTUDIO_APPDIR=/home/user/app

# 3. Copy your local package metadata first (for caching)
WORKDIR $HOME/app
COPY --chown=user . .

# 4. Install Gunicorn (in case your CLI/UI entrypoint uses it)
RUN pip install --upgrade pip \
 && pip install --user gunicorn uvicorn

# 5. Install your package in editable mode
RUN pip install --user -e .

# 6. Expose port and set the default CMD
EXPOSE 8081
CMD ["python", "-m", "gunicorn", \
     "-w", "4", \
     "--timeout", "12600", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "autogenstudio.web.app:app", \
     "--bind", "0.0.0.0:8081"]