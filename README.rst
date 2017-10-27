
Welcome to ``echo_api``'s documentation!
========================================

This project is a work in progress, and contributions are encouraged. If
you have questions feels free to contact me at
`jjorissen52@gmail.com <jjorissen52@gmail.com>`__

Installation
============

pip install echo_api

Configuration
=============

Secrets
=======

``echo_api`` is configured to take credentials from a file named
``echo.conf`` that is expected by default in your working directory.
``echo.conf`` should look like:

.. sourcecode:: python

    [echo]
    username = UserName
    password = Password
    wsdl_location = /path/to/wsdl.xml
    endpoint = https://cloud.echooneappcloud.com/yourorganizationname/OneAppWebService

If you want ``echo.conf`` to be somewhere other than your project
directory, you will need to set it the location using an environment
variable.

.. sourcecode:: python

    # Linux
    export INTERFACE_CONF_FILE=/absolute/path/to/conf_file.conf #name doesn't matter
    
    # Or set in Python before you import echo_api
    import os
    os.environ["INTERFACE_CONF_FILE"] = '/absolute/path/to/conf_file.conf'

Note that you must have credentials for a user that has access to the
API before you can proceed.

SOAP API WSDL Definition
========================

Due to the possibility of some configuration issues on Echo's side, you
will need to manually inspect the XML describing the API and ensure that
the endpoint definition is correct. Copy and paste this into the address
bar on your browser (you will need to change it to be your
organization):

https://cloud.echooneappcloud.com/yourorganization/OneAppWebService.svc?singleWsdl

Copy and paste the XML response into an XML file (``wsdl.xml``) in your
project directory and scroll all the way to the bottom until you see:

.. sourcecode:: python

    <wsdl:port name="BasicHttpBinding_OneAppWebService_SSL" binding="tns:BasicHttpBinding_OneAppWebService_SSL">
        <soap:address location="https://eoaapp0.echooneapp.com/YourOrganization/OneAppWebService.svc"/>
        </wsdl:port>
    </wsdl:service>

You will want to change

.. sourcecode:: python

    <soap:address location="https://eoaapp0.echooneapp.com/YourOrganization/OneAppWebService.svc"/>

to

.. sourcecode:: python

    <soap:address location="https://cloud.echooneappcloud.com/yourorganization/OneAppWebService"/>

Once you've set up your wsdl and secrets files, test your connection.
For a secrets file that will remain in your project directory, simply
use:

.. sourcecode:: python

    from echo_api import api
    # Connection() will log you in if everything is correctly configured.
    connection = api.BaseConnection()
    connection.session_id




.. parsed-literal::

    '61d63ecc7571430a9ead84dfc7f6301d'



If you see a string like the one above, it means that a connection was
successfully established and you've got the hard part done...

.. sourcecode:: python

    connection.API_Logout()




.. parsed-literal::

    'LoggedOut|kathleen.reynolds'



Usage
=====

The ``BaseConnection`` object has all of the API definitions provided by
the WSDL file. The API documentation can be found at
`read the docs. <http://echo-api.readthedocs.io/en/latest/index.html>`__
