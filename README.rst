=========
Staff SSO
=========

Staff SSO (also known as Authbroker / ABC) provides integration between applications
and identify providers.

Fine grained permissions are down to each app, SSO points users to apps.


Dependencies
------------

- Python 3.6
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

#. Create the db (variant: local postgres installed)::

    psql -p5432
    create database "staff-sso";

#. Create the db (variant: docker based)::

    docker run -p 5432:5432 -e POSTGRES_USER=`whoami` -e POSTGRES_DB=staff-sso postgres

#. Configure and populate the db::

    ./manage.py migrate
    ./manage.py createsuperuser

#. Start the server::

    ./manage.py runserver

#. You will now need to `create an OAuth application <http://localhost:8000/admin/oauth2/application/add/>`_ with::

    Client type: Confidential
    Grant type: Authorization code
    Skip authorization: checked
    Redirect urls: <values you want to be able to redirect to>

#. To run the SAML IdP test server, open a new tab and::

    cd extras/saml-idp-test

    docker build -tsi .

    docker run \
    -p 8080:80 \
    -p 8443:443 \
    -e SIMPLESAMLPHP_SP_ENTITY_ID=https://sso.staff.service.trade.gov.uk/sp \
    -e SIMPLESAMLPHP_SECRET_SALT=secret-salt \
    si
    

====================
Minimal Installation
====================

To run all of the above (if you are developing an app against ABC, instead of developing on ABC itself) then::

 docker-compose up -d
 docker-compose run web python ./manage.py

This will start postgres, Django and the sample idp. You can then follow the instructions above.


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


=====================
User Settings Storage
=====================

This is s a sub-service of Staff SSO where all integrated services have access to and can store and manipulate user specific settings for features such as personalisation that can be shared globally.

Schema
------

user_id
    UUID,
    Readonly,
    Context: ``view``.

app_slug
    Used for identifying the application the ``user_id`` is on.
    Context: ``create``, ``view``, ``edit``, ``delete``.

settings
    JSON,
    Context: ``create``, ``view``, ``edit``, ``delete``.


Create Settings
---------------

- Context
    A service can store any settings in JSON format.
    To store application specific settings, client needs to pass ``@``.
    To store global settings, qwhich can be shared to any other service, client needs to pass ``global``.::

        {
            "@": {
                "lorem": "ipsum"
            },
            "global": {
                "sit": "dolor"
            }
        }

- Definition
    POST /api/v1/user-settings/

- Example Request::

        $ curl -X POST -H "Content-Type: application/json" -d '{"@": {"lorem": "ipsum"},"global": {"sit": "dolor"}}' http://localhost:8080/api/v1/user-settings/


List Settings
-------------

- Context
    A service can access the settings stored for that particular service, and also the ``global`` settings.
    For applications that need to display all the settings, then this feature needs to be enabled from the Application admin panel.

    To get all the settings recorded to all applications associated to a user, client needs to pass in the request the following.::

        {
            "match_all":{}
        }

- Definition
    GET /api/v1/user-settings/

- Example Request::

        $ curl -X GET -H http://localhost:8080/api/v1/user-settings/


Update Settings
---------------

- Context
    To update specific settings, client needs to pass in the request the following::

        {
            "@":{
                "path": {
                    "to": {
                        "desired_setting_to_be_updated": {}
                    }
                }
                "another_path": {
                    "to": {
                        "desired_setting_to_be_updated": {}
                    }
                }
            }
        }

    If the setting doesn't exist, a new record will be created.
    If the update setting doesn't match the existing structure, it will return ``400``


- Definition
    POST /api/v1/user-settings/

- Example Request::

        $ curl -X POST -H "Content-Type: application/json" -d '{"@": "path":{ "to": {"desired_setting_to_be_updated": {}}}, "another_path":{ "to": {"desired_setting_to_be_updated": {}}}}' http://localhost:8080/api/v1/user-settings/



Delete Settings
---------------

- Context
    To delete specific settings, client needs to pass in the request the following::

        {
            "@":{
                "path": {
                    "to": {
                        "desired_setting_to_be_deleted": {}
                    }
                }
            }
        }

- Definition
    DELETE /api/v1/user-settings/

- Example Request::

        $ curl -X DELETE -H "Content-Type: application/json" -d '{"@": "path":{ "to": {"desired_setting_to_be_deleted": {} } }}' http://localhost:8080/api/v1/user-settings/

