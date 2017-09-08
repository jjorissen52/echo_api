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


class BaseConnection:

    def get_operations(self, key=""):
        """

        :param key: key corresponding to stored procedure. If empty will show all stored procedures
        :return: integer corresponding to stored procedure
        """
        operations = {
            'add': 5,
            'delete': 6,
            'execute': 0
        }
        if not key:
            for key, procedure in operations.items():
                print(f'{key}: {procedure}')
            return
        return operations[key]

    def API_SelectParameters(self, screen_name, name_space='Symed'):
        """

        :param screen_name: (string) name of the screen
        :param name_space: (string) namespace that the screen belongs to
        :return: (string) usually a string in the form @name|value|type, where the name is the parameter name,
        value is the value of the parameter and type specifies the type (int, string, bool, decimal).
        There may be multiple and not all values will be filled in. If there was an error, a string in the format
        “XXX|YYY” where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_SelectParameters(self.session_id, screen_name, name_space)

    def API_GeneralQuery(self, query, parameters=""):
        """

        :param query: the SQL-style query to be run
        :param parameters: optional set of parameters in form of @name|value|type, where the name is the
        parameter name, value is the value of the parameter and type specifies the type (int, string, guid, decimal).
        :return: usually XML with the requested results. If there was an error, a string in the
        format “XXX|YYY” where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_GeneralQuery(self.session_id, query, parameters)

    def API_GetData(self, screen_name, name_space, parameters):
        """

        :param screen_name: the session id returned from a login.
        :param name_space: name of the screen
        :param parameters: the parameters for the select statement. It is possible to get the
        names of the parameters from the API_SelectParameters function, the values will need to
        be supplied by the programmer.
        :return: usually the XML data. If there was an error, a string in the format “XXX|YYY”
        where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_GetData(self.session_id, screen_name, name_space, parameters)

    def API_UpdateData(self, tree_name, level_name, screen_name, name_space, parameters, dsXML):
        """

        :param tree_name: the name of tree (for providers, this is “Locations”)
        :param level_name: the name of the level (for providers, this is “Providers”)
        :param screen_name: name of the screen.
        :param name_space: the name space that the screen belongs to. Currently always “Symed”.
        :param parameters: the parameters for the select statement. It is possible to get the names
        of the parameters from the API_SelectParameters function, the values will need to be supplied by the programmer.
        :param dsXML: the XML data containing the updates.
        :return: usually the XML data. If there was an error, a string in the format “XXX|YYY” where XXX is a
        general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_UpdateData(self.session_id, tree_name, level_name, screen_name, name_space,
                                                  parameters, dsXML)

    def API_TreeDataCommand(self, tree_name, level_name, stored_proc, operation):
        """

        :param tree_name: the name of tree (for providers, this is “Locations”)
        :param level_name: the name of the level (for providers, this is “Providers”)
        :param stored_proc: the stored procedure that will perform the operation
        (for adding providers, this is PhysicianDetail_Create)
        :param operation: an integer that specifies the operation (0, 5 or 6) is (execute, add, delete).
        you can run self.get_operation() (self.get_operation('add') for example) to get the integer corresponding to
        your stored procedure.
        :return: usually a string in the format of name|value|type where the name is the parameter name,
        value is the parameter value and type is the parameter type. If this format is returned, the parameter can
        be used directly with API_GetData to retrieve the newly added item. If there was an error, a string in the
        format “XXX|YYY” where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_TreeDataCommand(self.session_id, tree_name, level_name, stored_proc, operation)

    def API_CreateNoPenUser(self, email, body, subject, return_email, password, parameters, security_groups, send_mail):
        """

        :param email: the email address, this will also be the security login.
        :param body: body of the email (usually a string built up of other information, like name, email and password.
        :param subject: subject of the email.
        :param return_email: the return email address for the email.
        :param password: the password for the new user (not the API user password).
        :param parameters: the parameters for the provider to add.
        :param security_groups: (list, string) contains a list (or string separated by vertical bars “|”)
        of security groups.
        :param send_mail: (bool) do we send the registration mail?
        :return: a string in the format “XXX|YYY” where XXX is a general description (Error, Denied, Success, etc)
        and YYY is the specific description.
        """
        if issubclass(security_groups, list):
            security_groups = '|'.join(security_groups)

        return self.client.service.API_CreateNoPenUser(self.session_id, email, body, subject, return_email, password,
                                                       parameters, security_groups, send_mail)

    def API_Login(self, username, password):
        """

        :param username: the base user name. No domain, actual login id, not the display name.
        :param password: the password corresponding to the user name.
        :return: if successful, a string containing the session id, in the format “SessionID|XXX” where XXX
        corresponds to the session id. If not successful, a string in the format “XXX|YYY” where XXX is a general
        description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_Login(username, password)

    def API_Logout(self):
        """

        :return: a string in the format “XXX|YYY” where XXX is a general description (Success, Error, Denied, etc)
        and YYY is the specific description.
        """
        return self.client.service.API_Logout(self.session_id)

    def API_Test(self):
        """

        :return: "Success|This message from WCF Service. You are connected!" or some kind of connection error probably
        """
        return self.client.service.API_Test()

    def __init__(self, settings=Settings()):
        self.endpoint = settings.ENDPOINT
        self.session = Session()
        self.client = Client(settings.WSDL_LOCATION, transport=Transport(session=self.session))
        if "Success" in self.client.service.API_Test():
            self.session_id = self.client.service.API_Login(settings.USERNAME, settings.PASSWORD).split("|")[1]
        else:
            raise APITestFailError("Test connection failed.")


class Helpers:
    class Meta:
        abstract = True

    """
    Helper Methods
    """

    def _search_schema(self, schema_str, show_all=True, **kwarg):
        schema = XMLSchema(schema_str)
        paths = schema.locate(**kwarg)
        items = [schema.retrieve('__'.join(path.split('__')[:-1])) for path in paths]
        kwarg_key = list(kwarg.keys())[0].split('__')[0]
        try:
            sorted_list = sorted(items, key=lambda x: int(x[kwarg_key])) if show_all else \
                sorted(items, key=lambda x: int(x[kwarg_key]))[-1]
        except IndexError:  # happens when there are no results in the search
            sorted_list = None
        return sorted_list

    @handle_response
    def _get_physician_guid(self, physician_id):
        qs = f"SELECT * FROM PhysicianDetail WHERE PhysicianID={physician_id}"
        schema_str = self.API_GeneralQuery(qs, "")
        physician = self._search_schema(schema_str, show_all=False, PhysicianID__ne=-1)
        if physician:
            return physician['EntityGuid']
        else:
            raise APICallError(f'No Physicians matching id {physician_id}')

    @staticmethod
    def _indent(elem, level=0):
        i = f"\n{level*'  '}"
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = f"{i} "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                Helpers._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    @staticmethod
    def _pretty_print(schema_str, *keys):
        root = ET.fromstring(schema_str)
        tree = ET.ElementTree(root)
        Helpers._indent(root)
        item = root
        for key in keys:
            item = item[key]
        print(str(ET.tostring(item), 'utf-8'))


class Adders:
    class Meta:
        abstract = True

    """
    Add Stuff
    """

    @handle_response
    def add_physician(self, office_id, **kwargs):
        args = ["Locations", "Provider", "PhysicianDetail_Create", 5, f"@OfficeID|{office_id}|int"]
        result = self.API_TreeDataCommand(*args)
        if "Error|" in result:
            raise APICallError(result)
        else:
            if len(kwargs) != 0:
                physician_id = result.split("|")[1]
                return self.edit_physician(physician_id, **kwargs)
            else:
                return result

    @handle_response
    def add_medical_license(self, physician_id, **kwargs):
        license_data = self.get_medical_licenses(physician_id)
        schema_and_data = ET.fromstring(license_data)
        for i, (key, value) in enumerate(kwargs.items()):
            if i == 0:
                new_table = ET.SubElement(schema_and_data[1], 'Table')
            new_attr = ET.SubElement(new_table, key)
            new_attr.text = f'{value}'
        updated_schema = ET.tostring(schema_and_data)
        args = ["Locations", "Provider", "MedicalLicenses", "Symed",
                f'@PhysicianID|{physician_id}|int', updated_schema]
        return self.API_UpdateData(*args)

    @handle_response
    def add_contact_log_entry(self, physician_id, **kwargs):
        if 'Notes' not in kwargs.keys():
            raise APICallError(f'You must add a note to contact log entries.')
        guid = self._get_physician_guid(physician_id)
        log_data = self.get_contact_log(physician_id)
        schema_and_data = ET.fromstring(log_data)
        for i, (key, value) in enumerate(kwargs.items()):
            if i == 0:
                new_table = ET.SubElement(schema_and_data[1], 'Table')
            new_attr = ET.SubElement(new_table, key)
            new_attr.text = f'{value}'
        updated_schema = ET.tostring(schema_and_data)
        Helpers._pretty_print(updated_schema, 1)
        args = ["Locations", "Provider", "CallLog", "Symed",
                f'@EntityGuid|{guid}|guid', updated_schema]
        return self.API_UpdateData(*args)

    @handle_response
    def add_office(self, practice_id=""):
        if not practice_id:
            raise APICallError("You must provide a practice_id with which to associate this office.")
        args = ["Locations", "Office", "Offices_Create", 5, f"@PracticeID|{practice_id}|int"]
        return self.service.API_TreeDataCommand(*args)


class Editors:
    class Meta:
        abstract = True

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
        args = ["Locations", "Provider", "PhysicianDetail",
                "Symed", f"@PhysicianID|{physician_id}|int", updated_schema]
        return self.API_UpdateData(*args)


class Deleters:
    class Meta:
        abstract = True

    """
    Delete Stuff
    """

    @handle_response
    def delete_physician(self, physician_id="", office_id=""):
        if not (physician_id and office_id):
            raise APICallError("You must specify both the physician_id and office_id.")
        args = ["Locations", "Provider", "PhysicianDetail_Delete", 6,
                f"@PhysicianID|{physician_id}|int@OfficeID|{office_id}|int"]
        return self.API_TreeDataCommand(*args)

    @handle_response
    def delete_office(self, office_id=""):
        if not office_id:
            raise APICallError("You must specify the office_id.")
        args = ["Locations", "Office", "Offices_Delete", 6,
                f"@OfficeID|{office_id}|int"]
        return self.API_TreeDataCommand(*args)


class Getters:
    class Meta:
        abstract = True

    """
    Get Stuff
    """

    @handle_response
    def get_physician(self, physician_id):
        args = ["PhysicianDetail", "Symed", f"@PhysicianID|{physician_id}|int"]
        return self.API_GetData(*args)

    @handle_response
    def get_office(self, office_id):
        args = ["Office", "Symed", f"@OfficeID|{office_id}|int"]
        return self.API_GetData(*args)

    @handle_response
    def get_medical_licenses(self, physician_id):
        args = ["MedicalLicenses", "Symed", f"@PhysicianID|{physician_id}|int"]
        return self.API_GetData(*args)

    @handle_response
    def get_contact_log(self, physician_id):
        guid = self._get_physician_guid(physician_id)
        args = ["CallLog", "Symed", f'@EntityGuid|{guid}|guid']
        return self.API_GetData(*args)


class Showers:
    class Meta:
        abstract = True

    """
    Show Stuff
    """

    @handle_response
    def show_physician(self, physician_id, show_all=True):
        schema_str = self.get_physician(physician_id)
        return self._search_schema(schema_str, PhysicianID__ne=-1)

    @handle_response
    def show_medical_licenses(self, physician_id, show_all=True):
        schema_str = self.get_medical_licenses(physician_id)
        return self._search_schema(schema_str, show_all=show_all, AutoID__ne=-1)

    @handle_response
    def show_office(self, office_id):
        schema_str = self.get_office(office_id)
        return self._search_schema(schema_str, show_all=False, OfficeID__ne=-1)

    @handle_response
    def show_physician_contact_log(self, physician_id, show_all=True):
        guid = self._get_physician_guid(physician_id)
        args = ["CallLog", "Symed", f'@EntityGuid|{guid}|guid']
        schema_str = self.API_GetData(*args)
        return self._search_schema(schema_str, show_all=show_all, CallID__ne=-1)

    @handle_response
    def show_latest_office(self, show_all=False):
        qs = "SELECT * FROM Offices"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, OfficeID__ne=-1)

    @handle_response
    def show_latest_practice(self, show_all=False):
        qs = "SELECT * FROM Offices WHERE OfficeID = PracticeID"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, OfficeID__ne=-1)

    @handle_response
    def show_latest_physician(self, show_all=False):
        qs = "SELECT * FROM PhysicianDetail"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, PhysicianID__ne=-1)

    @handle_response
    def show_latest_contact_log(self, show_all=False):
        qs = "SELECT * FROM ContactLog"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, CallID__ne=-1)

    @handle_response
    def show_latest_medical_license(self, show_all=False):
        qs = "SELECT * FROM MedicalLicenses"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, AutoID__ne=-1)


class EchoConnection(Helpers, Adders, Editors, Deleters, Getters, Showers, BaseConnection):
    pass


class OldConnection(BaseConnection):


    """
    Helper Methods
    """

    def _search_schema(self, schema_str, show_all=True, **kwarg):
        schema = XMLSchema(schema_str)
        paths = schema.locate(**kwarg)
        items = [schema.retrieve('__'.join(path.split('__')[:-1])) for path in paths]
        kwarg_key = list(kwarg.keys())[0].split('__')[0]
        try:
            sorted_list = sorted(items, key=lambda x: int(x[kwarg_key])) if show_all else \
                sorted(items, key=lambda x: int(x[kwarg_key]))[-1]
        except IndexError:  # happens when there are no results in the search
            sorted_list = None
        return sorted_list

    @handle_response
    def _get_physician_guid(self, physician_id):
        qs = f"SELECT * FROM PhysicianDetail WHERE PhysicianID={physician_id}"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        physician = self._search_schema(schema_str, show_all=False, PhysicianID__ne=-1)
        if physician:
            return physician['EntityGuid']
        else:
            raise APICallError(f'No Physicians matching id {physician_id}')

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
    def _pretty_print(schema_str, *keys):
        root = ET.fromstring(schema_str)
        tree = ET.ElementTree(root)
        Connection._indent(root)
        item = root
        for key in keys:
            item = item[key]
        print(str(ET.tostring(item), 'utf-8'))

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

    @handle_response
    def add_medical_license(self, physician_id, **kwargs):
        license_data = self.get_medical_licenses(physician_id)
        schema_and_data = ET.fromstring(license_data)
        for i, (key, value) in enumerate(kwargs.items()):
            if i == 0:
                new_table = ET.SubElement(schema_and_data[1], 'Table')
            new_attr = ET.SubElement(new_table, key)
            new_attr.text = f'{value}'
        updated_schema = ET.tostring(schema_and_data)
        args = [self.session_id, "Locations", "Provider", "MedicalLicenses", "Symed",
                f'@PhysicianID|{physician_id}|int', updated_schema]
        return self.client.service.API_UpdateData(*args)

    @handle_response
    def add_contact_log_entry(self, physician_id, **kwargs):
        if 'Notes' not in kwargs.keys():
            raise APICallError(f'You must add a note to contact log entries.')
        guid = self._get_physician_guid(physician_id)
        log_data = self.get_contact_log(physician_id)
        schema_and_data = ET.fromstring(log_data)
        for i, (key, value) in enumerate(kwargs.items()):
            if i == 0:
                new_table = ET.SubElement(schema_and_data[1], 'Table')
            new_attr = ET.SubElement(new_table, key)
            new_attr.text = f'{value}'
        updated_schema = ET.tostring(schema_and_data)
        Connection._pretty_print(updated_schema, 1)
        args = [self.session_id, "Locations", "Provider", "CallLog", "Symed",
                f'@EntityGuid|{guid}|guid', updated_schema]
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
    def get_medical_licenses(self, physician_id):
        args = [self.session_id, "MedicalLicenses", "Symed", f"@PhysicianID|{physician_id}|int"]
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
    def show_physician(self, physician_id, show_all=True):
        schema_str = self.get_physician(physician_id)
        return self._search_schema(schema_str, PhysicianID__ne=-1)

    @handle_response
    def show_medical_licenses(self, physician_id, show_all=True):
        schema_str = self.get_medical_licenses(physician_id)
        return self._search_schema(schema_str, show_all=show_all, AutoID__ne=-1)

    @handle_response
    def show_office(self, office_id):
        schema_str = self.get_office(office_id)
        return self._search_schema(schema_str, show_all=False, OfficeID__ne=-1)

    @handle_response
    def show_physician_contact_log(self, physician_id, show_all=True):
        guid = self._get_physician_guid(physician_id)
        args = [self.session_id, "CallLog", "Symed", f'@EntityGuid|{guid}|guid']
        schema_str = self.client.service.API_GetData(*args)
        return self._search_schema(schema_str, show_all=show_all, CallID__ne=-1)

    @handle_response
    def show_latest_office(self, show_all=False):
        qs = "SELECT * FROM Offices"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=show_all, OfficeID__ne=-1)

    @handle_response
    def show_latest_practice(self, show_all=False):
        qs = "SELECT * FROM Offices WHERE OfficeID = PracticeID"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=show_all, OfficeID__ne=-1)

    @handle_response
    def show_latest_physician(self, show_all=False):
        qs = "SELECT * FROM PhysicianDetail"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=show_all, PhysicianID__ne=-1)

    @handle_response
    def show_latest_contact_log(self, show_all=False):
        qs = "SELECT * FROM ContactLog"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=show_all, CallID__ne=-1)

    @handle_response
    def show_latest_medical_license(self, show_all=False):
        qs = "SELECT * FROM MedicalLicenses"
        schema_str = self.client.service.API_GeneralQuery(self.session_id, qs, "")
        return self._search_schema(schema_str, show_all=show_all, AutoID__ne=-1)
