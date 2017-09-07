=========
Staff SSO
=========


Dependencies
------------

- Python 3.6.1
- Postgres (tested on 9.5+)

Installation
------------

#. Clone the repository::

    git git@github.com:uktrade/staff-sso.git
    cd staff-sso

#. Install ``virtualenv`` if you don’t have it already::

    pip install virtualenv

#. Create and activate the virtualenv::

    virtualenv --python=python3 env
    source env/bin/activate
    pip install -U pip pip-tools

#. Install the dependencies::

    pip-sync requirements-dev.txt

#. Install `xmlsec1 <https://www.aleksey.com/xmlsec/>`_, its installation is platform specific

#. Create an ``.env`` file (it’s gitignored by default)::

    cp sample.env .env

#. Create the db::

    psql -p5432
    create database staff-sso;

#. Configure and populate the db::

    ./manage.py migrate
    ./manage.py createsuperuser

#. Start the server::

    ./manage.py runserver


#. You will now need to `create an OAuth application <http://localhost:8000/admin/oauth2_provider/application/add/>`_ with::

    Client type: Confidential
    Grant type: Authorization code
    Skip authorization: checked

#. To run the SAML IdP test server, open a new tab and::

    cd extras/saml-idp-test

    docker build -tsi .

    docker run \
    -p 8080:80 \
    -p 8443:443 \
    -e SIMPLESAMLPHP_SP_ENTITY_ID=https://sso.staff.service.trade.gov.uk/sp \
    -e SIMPLESAMLPHP_SECRET_SALT=secret-salt \
    tsi

Cache
-----

Currently the *cache-control* header for all the responses is set by default to *no-cache*.

This is enforced by the ``sso.core.middleware.NeverCacheMiddleware``.


Requirements
------------

If you need to add/change a production library::

    add/change the lib in requirements.in
    pip-compile requirements.in
    pip-compile -o requirements-dev.txt requirements-dev.in
    pip-sync requirements-dev.txt


If we have to add/change a dev library::

    add/change the lib in requirements-dev.in
    pip-compile -o requirements-dev.txt requirements-dev.in
    pip-sync requirements-dev.txt
