# this is created specifically to match Core's ADFS IdP response
MAP = {
    'identifier': 'urn:oasis:names:tc:SAML:2.0:attrname-format:uri',
    'fro': {
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress': 'email',
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname': 'givenname',
        'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname': 'surname',
        'http://schemas.xmlsoap.org/claims/Group': 'group',
    },
    'to': {
        'email': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress',
        'givenname': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname',
        'surname': 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname',
        'group': 'http://schemas.xmlsoap.org/claims/Group',
    }
}
