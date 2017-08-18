
# Installation
pip install echo_api
# Configuration

## Secrets

`echo_api` is configured to take credentials from a file named `secrets.json` that should live in your project directory and make reference to it in the `settings` module. `secrets.json` should look something like:
{
    "USERNAME": "Username",
    "PASSWORD": "P4ssw0rd123",
    "WSDL_LOCATION": "wsdl.xml",
    "ENDPOINT": "https://cloud.echooneappcloud.com/yourorganization/OneAppWebService"
}
Note that you must have credentials for a user that has access to the API before you can proceed.

## API Definition

Due to the possibility of some configuration issues on Echo's side, you will need to manually inspect the XML describing the API and ensure that the endpoint definition is correct. Copy and paste this into the address bar on your browser (you will need to change it to be your organization):

https://cloud.echooneappcloud.com/yourorganization/OneAppWebService.svc?singleWsdl

Copy and paste the XML response into an XML file (`wsdl.xml`) in your project directory and scroll all the way to the bottom until you see:
<wsdl:port name="BasicHttpBinding_OneAppWebService_SSL" binding="tns:BasicHttpBinding_OneAppWebService_SSL">
    <soap:address location="https://eoaapp0.echooneapp.com/YourOrganization/OneAppWebService.svc"/>
    </wsdl:port>
</wsdl:service>
You will want to change
<soap:address location="https://eoaapp0.echooneapp.com/YourOrganization/OneAppWebService.svc"/>
to
<soap:address location="https://cloud.echooneappcloud.com/yourorganization/OneAppWebService"/>
Once you've done that, test your connection.


```python
from api import Connection
# Connection() will log you in if everything is correctly configured.
connection = Connection()
connection.session_id
```




    'IAMYOURSESSIONID'



Your session_id should look like a random string of characters.


```python

```
