<?php
/**
 * SAML 2.0 remote SP metadata for SimpleSAMLphp.
 *
 * See: https://simplesamlphp.org/docs/stable/simplesamlphp-reference-sp-remote
 */

 $metadata[getenv('SIMPLESAMLPHP_SP_ENTITY_ID')] = array (
   'entityid' => getenv('SIMPLESAMLPHP_SP_ENTITY_ID'),
   'contacts' => array (),
   'metadata-set' => 'saml20-sp-remote',
   'expire' => 9496157643,
   'AssertionConsumerService' => array (
     0 => array (
       'Binding' => 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
       'Location' => 'http://localhost:8000/saml2/acs/',
       'index' => 1,
     ),
   ),
   'SingleLogoutService' => array (
     0 => array (
        'Binding' => 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
        'Location' => 'http://localhost:8000/saml2/ls/post/',
      ),
   ),
   'NameIDFormat' => 'urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified',
   'keys' => array (
     0 => array (
       'encryption' => false,
       'signing' => true,
       'type' => 'X509Certificate',
       'X509Certificate' => 'MIIDXTCCAkWgAwIBAgIJAKOmSubYLfehMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
 BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
 aWRnaXRzIFB0eSBMdGQwHhcNMTcwMjEzMTYwMDA5WhcNMjcwMjEzMTYwMDA5WjBF
 MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
 ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
 CgKCAQEAsC+lQjKowa9TuWBGxXa65YzhDTKqRjR3+SGywkwMN8TreQQo5h7RZnvF
 RmadjZcI/0qjPYbUSvPCE85hZm5E1eoCxPO09fbnBWgl6Lhu2+b524R5R5vJnApp
 AVMxkh7scVaSr8dNcSPRJQagmIyRR04q2vSk63CS7TkFmfhWlIoCoqsvvuxk7n/E
 3umpmFjE6zpb8ZgP2qtYFwIuXUFgLePbjWCEW00wwRsAJTEP9R+v2Pxtsu6VVQCa
 1tRKT2VapK0TMZ8e8b0nCRI72i0MKlyCxra9YQ1zAp/ENl1M4ocoDJ7G/exWrq+y
 AhMAWEwf+7QI6Zel6y6ukDaicIR1UwIDAQABo1AwTjAdBgNVHQ4EFgQUOhrQhJLM
 V2DaUMYbOVXZ2QWqvvswHwYDVR0jBBgwFoAUOhrQhJLMV2DaUMYbOVXZ2QWqvvsw
 DAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAPQdwmTJDBBzWJqdWXpJ5
 +vsMWvIqLpTaa+aDd/np3KJz04WnXibsSo9wIzxJ44lbodpZ1uwKF5UihWg+aEFL
 LPOdr0IHlS5ojbdvAioEU/Dke2fkJtQ+MtOFXDKhzWtqJB/dHPcjNn0ETUW+xXOX
 9FYYGvq9E+TNiWUTQ+VAvazV8BGnv9EGnn3uDrc7YINFXRdvCo4oYD645FOyGvwB
 mfiASPRAILhvaavy8mh/WBHs/FKZGXc/RgJJ78GJavuCAbVDmAIUIqoi8ZpeaxWl
 a5rzxcZZfTeVuKTiS1l87jf1jXIFbBvByHisiohmeWYPU0xvcwXf8w2KldIzcjMr
 WQ==
 ',
     ),
     1 =>
     array (
       'encryption' => true,
       'signing' => false,
       'type' => 'X509Certificate',
       'X509Certificate' => 'MIIDXTCCAkWgAwIBAgIJAKOmSubYLfehMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV
 BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
 aWRnaXRzIFB0eSBMdGQwHhcNMTcwMjEzMTYwMDA5WhcNMjcwMjEzMTYwMDA5WjBF
 MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50
 ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB
 CgKCAQEAsC+lQjKowa9TuWBGxXa65YzhDTKqRjR3+SGywkwMN8TreQQo5h7RZnvF
 RmadjZcI/0qjPYbUSvPCE85hZm5E1eoCxPO09fbnBWgl6Lhu2+b524R5R5vJnApp
 AVMxkh7scVaSr8dNcSPRJQagmIyRR04q2vSk63CS7TkFmfhWlIoCoqsvvuxk7n/E
 3umpmFjE6zpb8ZgP2qtYFwIuXUFgLePbjWCEW00wwRsAJTEP9R+v2Pxtsu6VVQCa
 1tRKT2VapK0TMZ8e8b0nCRI72i0MKlyCxra9YQ1zAp/ENl1M4ocoDJ7G/exWrq+y
 AhMAWEwf+7QI6Zel6y6ukDaicIR1UwIDAQABo1AwTjAdBgNVHQ4EFgQUOhrQhJLM
 V2DaUMYbOVXZ2QWqvvswHwYDVR0jBBgwFoAUOhrQhJLMV2DaUMYbOVXZ2QWqvvsw
 DAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAPQdwmTJDBBzWJqdWXpJ5
 +vsMWvIqLpTaa+aDd/np3KJz04WnXibsSo9wIzxJ44lbodpZ1uwKF5UihWg+aEFL
 LPOdr0IHlS5ojbdvAioEU/Dke2fkJtQ+MtOFXDKhzWtqJB/dHPcjNn0ETUW+xXOX
 9FYYGvq9E+TNiWUTQ+VAvazV8BGnv9EGnn3uDrc7YINFXRdvCo4oYD645FOyGvwB
 mfiASPRAILhvaavy8mh/WBHs/FKZGXc/RgJJ78GJavuCAbVDmAIUIqoi8ZpeaxWl
 a5rzxcZZfTeVuKTiS1l87jf1jXIFbBvByHisiohmeWYPU0xvcwXf8w2KldIzcjMr
 WQ==
 ',
     ),
   ),
   'validate.authnrequest' => true,
   'saml20.sign.assertion' => true,
 );
