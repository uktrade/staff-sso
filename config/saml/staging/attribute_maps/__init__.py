# this is created specifically to match Core's ADFS IdP response
MAP = {
    'identifier': 'urn:oasis:names:tc:SAML:2.0:attrname-format:uri',
    'fro': {
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress': 'email',
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname': 'first_name',
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname': 'last_name',
        'http://schemas.xmlsoap.org/claims/Group': 'group',
        'first_name': 'first_name',
        'last_name': 'last_name',
        'email': 'email'
    },
    'to': {
        'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
        'first_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
        'last_name': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
        'group': 'http://schemas.xmlsoap.org/claims/Group',
    }
}
