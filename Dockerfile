FROM python:3.8-slim as base

LABEL maintainer "Arnaud Rocher <arnaud.roche3@gmail.com>"

ENV PYTHONUNBUFFERED 1

RUN useradd --user-group --system --create-home --no-log-init pythonapp \
    && mkdir /app \
    && chown pythonapp:pythonapp /app
WORKDIR /app

FROM base as builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        wget

USER pythonapp

RUN wget -q -O /tmp/get-poetry.py \
        https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py \
    && python /tmp/get-poetry.py --version=1.0.5

ENV PATH "/home/pythonapp/.poetry/bin:$PATH"

COPY --chown=pythonapp:pythonapp pyproject.toml poetry.lock ./

# hadolint ignore=SC1091
RUN python -m venv .venv \
    && . .venv/bin/activate \
    && poetry install --no-dev --no-interaction

COPY --chown=pythonapp:pythonapp . ./

FROM base

USER pythonapp

COPY --from=builder /app /app

CMD [".venv/bin/python", "-m", "opcua_webhmi_bridge"]
