# !Notice!
This documentation is not yet complete as the api is still in development. If you need clarification on any of the below feel free to contact me at [jjorissen52@gmail.com](mailto:jjorissen52@gmail.com)

# Installation
pip install echo_api
# Configuration

## Secrets

`echo_api` is configured to take credentials from a file named `secrets.conf` that is expected by default in your working directory. `secrets.conf` should look like:

```
[echo]
username = UserName
password = Password
wsdl_location = /path/to/wsdl.xml
endpoint = https://cloud.echooneappcloud.com/yourorganizationname/OneAppWebService
```


If you want `secrets.json` to be somewhere other than your project directory, you will need to set it in a `Settings` object and make reference to it in your `Connection`. More on that below.

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
Once you've set up your wsdl and secrets files, test your connection. For a secrets file that will remain in your project directory, simply use:


```python
from echo_api import Connection
# Connection() will log you in if everything is correctly configured.
connection = Connection()
connection.session_id
```




    'IAMYOURSESSIONID'



If you wish to use a custom secrets location, you will need to create a `Settings` object and use that when creating your connection. 


```python
from echo_api import Settings, Connection
# secrets_location is full or relative path to secrets location
settings = Settings(secrets_location='secrets.json')
connection = Connection(settings=settings)
```
# Some Echo API Documentation
Below is a portion of the SOAP documentation on Echo's end that should be helpful while using this package.

`connection.client.service.API_SelectParameters(connection.session_id, screenName, nameSpace='Symed')`
   * `session` (string): the session id returned from a login.
   * `screenName` (string): name of the screen.
   * `nameSpace` (string): the name space that the screen belongs to. Currently always “Symed”.
   
`connection.client.service.API_GeneralQuery(connection.session_id, query, parameters)`
   * `session` (string): the session id returned from a login.
   * `query` (string): the actual query that will be run.
   * `parameters` (string): optional set of parameters in the form @name|value|type, where the name 
                     is the parameter name, value is the value of the parameter and type specifies 
                     the type (int, string, Guid, decimal).       
           
   
`connection.client.service.API_GetData(connection.session_id, screenName, nameSpace='Symed', parameters)`
   * `session` (string): the session id returned from a login.
   * `screenName` (string) name of the screen.
   * `nameSpace` (string) the name space that the screen belongs to. Currently always “Symed”.
   * `parameters` (string) the parameters for the select statement. It is possible to get the names of the parameters from the API_SelectParameters function, the values will need to be supplied by the programmer.
   
`connection.client.service.API_UpdateData(connection.session_id, treename, levelname, screenName, nameSpace, parameters, dsXML)`
   * `session` (string): the session id returned from a login.
   * `treename` (string) the name of tree (for providers, this is “Locations”)
   * `levelname` (string) the name of the level (for providers, this is “Providers”)
   * `screenName` (string) name of the screen.
   * `nameSpace` (string) the name space that the screen belongs to. Currently always “Symed”.
   * `parameters` (string) the parameters for the select statement. It is possible to get the names of the parameters from the API_SelectParameters function, the values will need to be supplied by the programmer.
   * `dsXML` (string) the XML data containing the updates.
   
`connection.client.service.API_TreeDataCommand(connection.session_id, treename, levelname, storedproc, operation)`
   * `session` (string): the session id returned from a login.
   * `treename` (string): the name of tree (for providers, this is “Locations”)
   * `levelname` (string): the name of the level (for providers, this is “Providers”)
   * `storedproc` (string): the stored procedure that will perform the operation (for adding providers, 
                     this is PhysicianDetail_Create)
   * `operation` (int): an integer that specifies the operation (0, 5 or 6). The currently supported 
                 operations are
        * 0 – execute stored procedure
        * 5 – add an item to the tree
        * 6 – delete an item from the tree.
   * `parameters` (string) set of parameters in the form @name|value|type, where the name is 
          the parameter name, value is the value of the parameter and type specifies the type 
          (int, string, guid, decimal). 
   
`connection.client.service.API_CreateNoPenUser(connection.session_id, email, body, subject, returnemail, parameters, securitygroups, sendmail)`

   * `session` (string): the session id returned from a login.
   * `email` (string) the email address, this will also be the security login.
   * `body` (string) body of the email (usually a string built up of other information, like name, email and password.
   * `subject` (string) subject of the email.
   * `returnemail` (string) the return email address for the email.
   * `password` (string) the password for the new user (not the API user password).
   * `parameters` (string) the parameters for the provider to add. 
   * `securitygroups` (string) contains a list of security groups, separated by vertical bars “|”.
   * `sendmail` (bool) do we send the registration mail?