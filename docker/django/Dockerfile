FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app


FROM base AS build-stage

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# сopy requirements & install dependencies
COPY ./backend/requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip wheel \
    && python -m pip wheel --no-cache-dir --wheel-dir /wheels \
    -r /app/requirements.txt


FROM base AS runtime-deps-stage

# install runtime dependencies, PostgreSQL and Redis clients for health checks
RUN apt-get update && apt-get install --no-install-recommends -y \
    libpq5 \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build-stage /wheels /wheels
COPY --from=build-stage /app/requirements.txt /app/requirements.txt

RUN python -m pip install --no-index --find-links=/wheels \
    -r /app/requirements.txt \
    && rm -rf /wheels /app/requirements.txt


FROM runtime-deps-stage AS staticfiles-stage

# copy application files & collect static files
COPY ./backend/ /app/

ENV BUILD_TIME=1

ENV DJANGO_SETTINGS_MODULE=conf.settings \
    SECRET_KEY=unsafe-build-time-secret-do-not-use-in-production

RUN python manage.py collectstatic --noinput


FROM runtime-deps-stage AS run-stage

# create user with limited permissions
RUN addgroup --gid 10001 --system django && \
    adduser --no-create-home --shell /bin/false \
    --disabled-password --uid 10001 --system --group django

# copy application files
COPY --chown=django:django ./backend/ /app/
COPY --from=staticfiles-stage --chown=django:django /app/staticfiles /app/staticfiles

# copy entrypoint
COPY --chown=django:django ./docker/django/entrypoint.sh /entrypoint.sh
RUN sed -i "s/\r$//g" /entrypoint.sh

# copy prod start script
COPY --chown=django:django ./docker/django/start-web.sh /start-web.sh
RUN sed -i "s/\r$//g" /start-web.sh

# copy dev start script
COPY --chown=django:django ./docker/django/start-web-dev.sh /start-web-dev.sh
RUN sed -i "s/\r$//g" /start-web-dev.sh

# change scripts permissions
RUN chmod 555 /entrypoint.sh /start-web.sh /start-web-dev.sh

# switch to created user
USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]

CMD ["/start-web.sh"]