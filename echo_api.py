import configparser
import os, sys, moment
from requests import Session
from functools import wraps

from zeep import Client
from zeep.transports import Transport

from xmlmanip import XMLSchema

import xml.etree.ElementTree as ET


class APITestFailError(BaseException):
    pass


class ImproperlyConfigured(BaseException):
    pass


class APICallError(BaseException):
    pass

SECRETS_LOCATION = os.environ.get('ECHO_SECRETS_LOCATION')
SECRETS_LOCATION = os.path.abspath(SECRETS_LOCATION) if SECRETS_LOCATION else 'secrets.conf'


def handle_response(method):
    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        response = method(self, *method_args, **method_kwargs)
        if "Error|" in response:
            raise APICallError(response)
        else:
            return response
    return _impl


class Settings:

    def __init__(self, secrets_location=SECRETS_LOCATION):
        config = configparser.ConfigParser()
        try:
            config.read(secrets_location)
            self.USERNAME = config.get('echo', 'username')
            self.PASSWORD = config.get('echo', 'password')
            self.WSDL_LOCATION = config.get('echo', 'wsdl_location')
            self.ENDPOINT = config.get('echo', 'endpoint')

        except configparser.NoSectionError:
            sys.stdout.write(f'Region [echo] was not found in the configuration file. '
                             f'You must set the location to a configuration file using the environment variable '
                             f'ECHO_SECRETS_LOCATION or have a file named "secrets.conf". Check the documentation'
                             f'for an example layout of this file.')
            self.USERNAME = ''
            self.PASSWORD = ''
            self.WSDL_LOCATION = ''
            self.ENDPOINT = ''

DOCSTRING = """
    self.client.service.API_SelectParameters(session, screenName, nameSpace)
    Parameters:
        session (string): the session id returned from a login.
        sreenName (string): name of the screen.
        nameSpace (string): the name space that the screen belongs to. Currently always “Symed”.
    
    self.client.service.API_UpdateData(session, treename, levelname, screenName, nameSpace, parameters)
    Parameters:
        session (string): the session id returned from a login.
        treename (string): the name of tree (for providers, this is “Locations”)
        levelname (string): the name of the level (for providers, this is “Providers”)
        sreenName (string): name of the screen.
        nameSpace (string): the name space that the screen belongs to. Currently always “Symed”.
        parameters (string): the parameters for the select statement. It is possible to get the 
                             names of the parameters from the API_SelectParameters function, 
                             the values will need to be supplied by the programmer.
        dsXML (string): the XML data containing the updates.
        
    self.client.service.API_GeneralQuery(session, query, parameters)
    Parameters:
        session (string): the session id returned from a login.
        query (string): the actual query that will be run.
        parameters (string): optional set of parameters in the form @name|value|type, where the name 
                             is the parameter name, value is the value of the parameter and type specifies 
                             the type (int, string, Guid, decimal).    
                             
    self.client.service.API_TreeDataCommand(session, treename, levelname, storedproc, operation)
    Parameters:
        session (string): the session id returned from a login.
        treename (string): the name of tree (for providers, this is “Locations”)
        levelname (string): the name of the level (for providers, this is “Providers”)
        storedproc (string): the stored procedure that will perform the operation (for adding providers, 
                             this is PhysicianDetail_Create)
        operation (int): an integer that specifies the operation (0, 5 or 6). The currently supported 
                         operations are
                * 0 – execute stored procedure
                * 5 – add an item to the tree
                * 6 – delete an item from the tree.
                * parameters (string) set of parameters in the form @name|value|type, where the name is 
                  the parameter name, value is the value of the parameter and type specifies the type 
                  (int, string, guid, decimal). 
    """


class Connection:
    def __init__(self, settings=Settings()):
        self.endpoint = settings.ENDPOINT
        self.session = Session()
        self.client = Client(settings.WSDL_LOCATION, transport=Transport(session=self.session))
        if "Success" in self.client.service.API_Test():
            self.session_id = self.client.service.API_Login(settings.USERNAME, settings.PASSWORD).split("|")[1]
        else:
            raise APITestFailError("Test connection failed.")

    """
    Helper Methods
    """

    def _search_schema(self, schema_str, show_all=True, **kwarg):
        schema = XMLSchema(schema_str)
        paths = schema.locate(**kwarg)
        items = [schema.retrieve('__'.join(path.split('__')[:-1])) for path in paths]
        kwarg_key = list(kwarg.keys())[0].split('__')[0]
        sorted_list = sorted(items, key=lambda x: int(x[kwarg_key])) if show_all else \
            sorted(items, key=lambda x: int(x[kwarg_key]))[-1]
        return sorted_list

    @handle_response
    def _get_physician_guid(self, physician_id):
        qs = f"SELECT * FROM PhysicianDetail WHERE PhysicianID={physician_id}"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        schema = XMLSchema(schema_str)
        paths = schema.locate(PhysicianID__ne='-1')
        physicians = [schema.retrieve('__'.join(path.split('__')[:-1])) for path in paths]
        if len(physicians) > 0:
            physician = sorted(physicians, key=lambda x: int(x['PhysicianID']), reverse=True)[0]
        else:
            raise APICallError(f'No Physicians matching id {physician_id}')
        return physician["EntityGuid"]

    @staticmethod
    def _indent(elem, level=0):
        i = f"\n{level*'  '}"
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = f"{i} "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                Connection._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    @staticmethod
    def _pretty_print(schema_str):
        root = ET.fromstring(schema_str)
        tree = ET.ElementTree(root)
        Connection._indent(root)
        print(str(ET.tostring(root), 'utf-8'))

    """
    Add Stuff
    """

    @handle_response
    def add_physician(self, office_id, **kwargs):
        args = [self.session_id, "Locations", "Provider", "PhysicianDetail_Create", 5, f"@OfficeID|{office_id}|int"]
        result = self.client.service.API_TreeDataCommand(*args)
        if "Error|" in result:
            raise APICallError(result)
        else:
            if len(kwargs) != 0:
                physician_id = result.split("|")[1]
                return self.edit_physician(physician_id, **kwargs)
            else:
                return result

    def add_contact_log_entry(self, physician_id, **kwargs):
        if 'Notes' not in kwargs.keys():
            raise APICallError(f'You must add a note to contact log entries.')
        guid = self._get_physician_guid(physician_id)
        log_data = self.get_contact_log(physician_id)
        schema_and_data = ET.fromstring(log_data)
        kwargs2 = {'CallID': len(schema_and_data[1]) // 2, 'Subject': kwargs.pop('Subject')}
        kwargs1 = {
            'EntityGuid': guid, 'CallID': len(schema_and_data[1]) // 2, 'ContactID': 0,
            'ContactDate': moment.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), **kwargs
        }
        for i, (key, value) in enumerate(kwargs1.items()):
            if i == 0:
                new_table1 = ET.SubElement(schema_and_data[1], 'Table')
            new_attr = ET.SubElement(new_table1, key)
            new_attr.text = f'{value}'
        for i, (key, value) in enumerate(kwargs2.items()):
            if i == 0:
                new_table2 = ET.SubElement(schema_and_data[1], 'Table1')
            new_attr = ET.SubElement(new_table2, key)
            new_attr.text = f'{value}'
        updated_schema = ET.tostring(schema_and_data)
        Connection._pretty_print(updated_schema)
        args = [self.session_id, "Locations", "Provider", "CallLog", "Symed",
                f'@EntityGuid|{guid}|guid', updated_schema]
        print(args[:-1])
        return self.client.service.API_UpdateData(*args)

    @handle_response
    def add_office(self, practice_id=""):
        if not practice_id:
            raise APICallError("You must provide a practice_id with which to associate this office.")
        args = [self.session_id, "Locations", "Office", "Offices_Create", 5, f"@PracticeID|{practice_id}|int"]
        return self.client.service.API_TreeDataCommand(*args)

    """
    Edit Stuff
    """

    @handle_response
    def edit_physician(self, physician_id, **kwargs):
        physician = self.get_physician(physician_id)
        schema_and_data = ET.fromstring(physician)
        for key, value in kwargs.items():
            if schema_and_data[1][0].find(key) is None:
                new_attr = ET.SubElement(schema_and_data[1][0], key)
                new_attr.text = value
            else:
                schema_and_data[1][0].find(key).text = f'{value}'
        updated_schema = ET.tostring(schema_and_data)
        args = [self.session_id, "Locations", "Provider", "PhysicianDetail",
                "Symed", f"@PhysicianID|{physician_id}|int", updated_schema]
        return self.client.service.API_UpdateData(*args)

    """
    Delete Stuff
    """

    @handle_response
    def delete_physician(self, physician_id="", office_id=""):
        if not (physician_id and office_id):
            raise APICallError("You must specify both the physician_id and office_id.")
        args = [self.session_id, "Locations", "Provider", "PhysicianDetail_Delete", 6,
                f"@PhysicianID|{physician_id}|int@OfficeID|{office_id}|int"]
        return self.client.service.API_TreeDataCommand(*args)

    @handle_response
    def delete_office(self, office_id=""):
        if not office_id:
            raise APICallError("You must specify the office_id.")
        args = [self.session_id, "Locations", "Office", "Offices_Delete", 6,
                f"@OfficeID|{office_id}|int"]
        return self.client.service.API_TreeDataCommand(*args)

    """
    Get Stuff
    """

    @handle_response
    def get_physician(self, physician_id):
        args = [self.session_id, "PhysicianDetail", "Symed", f"@PhysicianID|{physician_id}|int"]
        return self.client.service.API_GetData(*args)

    @handle_response
    def get_office(self, office_id):
        args = [self.session_id, "Office", "Symed", f"@OfficeID|{office_id}|int"]
        return self.client.service.API_GetData(*args)

    @handle_response
    def get_contact_log(self, physician_id):
        guid = self._get_physician_guid(physician_id)
        args = [self.session_id, "CallLog", "Symed", f'@EntityGuid|{guid}|guid']
        return self.client.service.API_GetData(*args)

    """
    Show Stuff
    """

    @handle_response
    def show_physician(self, physician_id):
        args = [self.session_id, "PhysicianDetail", "Symed", f"@PhysicianID|{physician_id}|int"]
        schema_str = self.client.service.API_GetData(*args)
        return self._search_schema(schema_str, PhysicianID__ne=-1)

    @handle_response
    def show_office(self, office_id):
        args = [self.session_id, "Office", "Symed", f"@OfficeID|{office_id}|int"]
        schema_str = self.client.service.API_GetData(*args)
        return self._search_schema(schema_str, show_all=False, OfficeID__ne=-1)

    @handle_response
    def show_latest_office(self):
        qs = "SELECT * FROM Offices"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=False, OfficeID__ne=-1)

    @handle_response
    def show_latest_practice(self):
        qs = "SELECT * FROM Offices WHERE OfficeID = PracticeID"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=False, OfficeID__ne=-1)

    @handle_response
    def show_latest_physician(self):
        qs = "SELECT * FROM PhysicianDetail"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=False, PhysicianID__ne=-1)

    @handle_response
    def show_latest_contact_log(self):
        qs = "SELECT * FROM ContactLog"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=False, CallID__ne=-1)



