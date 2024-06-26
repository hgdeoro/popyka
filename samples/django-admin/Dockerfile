FROM python:3.10-alpine3.19 as python

FROM python as python-build-stage

RUN apk add --no-cache librdkafka

RUN apk add build-base librdkafka-dev

# Requirements are installed here to ensure they will be cached.
COPY ./requirements.txt .

# Create Python Dependency and Sub-Dependency Wheels.
RUN pip wheel --wheel-dir /usr/src/app/wheels  \
  -r requirements.txt

FROM python as python-run-stage

RUN apk add --no-cache librdkafka

ARG APP_HOME=/app

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR ${APP_HOME}

COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/

COPY --chown=root:root ./sample_app ${APP_HOME}/sample_app
COPY --chown=root:root ./sample_project ${APP_HOME}/sample_project
COPY --chown=root:root ./manage.py ${APP_HOME}/manage.py

USER nobody
USER root

CMD ["/bin/sh", "-c", "python3 manage.py migrate && python3 manage.py runserver 0.0.0.0:8080"]
