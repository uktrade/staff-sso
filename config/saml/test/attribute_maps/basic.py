# See http://technet.microsoft.com/en-us/library/ee913589(v=ws.10).aspx
# for information regarding the default claim types supported by
# Microsoft ADFS v2.0.

MAP = {
    "identifier": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
    "fro": {
        "email": "email",
        "firstname": "first_name",
        "lastname": "last_name",
    },
    "to": {
        "email": "email",
        "first_name": "firstname",
        "last_name": "lastname",
    },
}
