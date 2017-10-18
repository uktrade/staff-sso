FROM python:3.6-slim

MAINTAINER tools@digital.trade.gov.uk

RUN apt-get update && apt-get install -qq build-essential libpq-dev python3-dev libffi-dev libssl-dev xmlsec1

WORKDIR /app
ADD requirements*.txt /app/
ADD requirements*.in /app/

RUN pip install -U pip pip-tools && pip-sync requirements.txt requirements-dev.txt && pip install honcho
ADD . /app
CMD honcho start

