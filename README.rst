
Installation
============

pip install echo_api

Configuration
=============

Secrets
=======

``echo_api`` is configured to take credentials from a file named
``secrets.json`` that is expected by default in your working directory.
``secrets.json`` should look like:

{
    "USERNAME": "Username",
    "PASSWORD": "P4ssw0rd123",
    "WSDL_LOCATION": "wsdl.xml",
    "ENDPOINT": "https://cloud.echooneappcloud.com/yourorganization/OneAppWebService"
}

If you want ``secrets.json`` to be somewhere other than your project
directory, you will need to set it in a ``Settings`` object and make
reference to it in your ``Connection``. More on that below.

Note that you must have credentials for a user that has access to the
API before you can proceed.

API Definition
==============

Due to the possibility of some configuration issues on Echo's side, you
will need to manually inspect the XML describing the API and ensure that
the endpoint definition is correct. Copy and paste this into the address
bar on your browser (you will need to change it to be your
organization):

https://cloud.echooneappcloud.com/yourorganization/OneAppWebService.svc?singleWsdl

Copy and paste the XML response into an XML file (``wsdl.xml``) in your
project directory and scroll all the way to the bottom until you see:

<wsdl:port name="BasicHttpBinding_OneAppWebService_SSL" binding="tns:BasicHttpBinding_OneAppWebService_SSL">
    <soap:address location="https://eoaapp0.echooneapp.com/YourOrganization/OneAppWebService.svc"/>
    </wsdl:port>
</wsdl:service>

You will want to change

<soap:address location="https://eoaapp0.echooneapp.com/YourOrganization/OneAppWebService.svc"/>

to

<soap:address location="https://cloud.echooneappcloud.com/yourorganization/OneAppWebService"/>

Once you've set up your wsdl and secrets files, test your connection.
For a secrets file that will remain in your project directory, simply
use:

.. code:: ipython3

    from echo_api import Connection
    # Connection() will log you in if everything is correctly configured.
    connection = Connection()
    connection.session_id




.. parsed-literal::

    'IAMYOURSESSIONID'



If you wish to use a custom secrets location, you will need to create a
``Settings`` object and use that when creating your connection.

.. code:: ipython3

    from echo_api import Settings, Connection
    # secrets_location is full or relative path to secrets location
    settings = Settings(secrets_location='secrets.json')
    connection = Connection(settings=settings)
