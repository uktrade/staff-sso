FROM python:3.6
MAINTAINER tools@digital.trade.gov.uk
RUN apt-get update && apt-get install -qq build-essential \
                                          libpq-dev \
                                          python3-dev \
                                          libffi-dev \
                                          libssl-dev \
                                          xmlsec1 \
                                          git \
                                          postgresql-client
WORKDIR /app
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
RUN pip install honcho
COPY . .
CMD honcho start