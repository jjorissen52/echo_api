import configparser
import os, sys, inspect
from datetime import datetime

from requests import Session
from functools import wraps

from zeep import Client
from zeep.transports import Transport

from xmlmanip import XMLSchema, print_xml
from . wrappers import wrap_methods

import xml.etree.ElementTree as ET


class APITestFailError(BaseException):
    pass


class ImproperlyConfigured(BaseException):
    pass


class APICallError(BaseException):
    pass

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_LOCATION = os.environ.get('INTERFACE_CONF_FILE')
SECRETS_LOCATION = os.path.abspath(SECRETS_LOCATION) if SECRETS_LOCATION else os.path.join(PROJECT_DIR, 'echo.conf')


def handle_response(method):
    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        response = method(self, *method_args, **method_kwargs)
        if "Error|" in response:
            raise APICallError(response)
        else:
            return response
    return _impl


def keep_warm(method):
    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        self.__init__(self.settings)
        response = method(self, *method_args, **method_kwargs)
        return response
    return _impl


class Settings:
    """
    This class only exists to collect settings for the BaseConnection object.
    """

    def __init__(self, secrets_location=SECRETS_LOCATION):
        config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        try:
            config.read(secrets_location)
            self.USERNAME = config.get('echo', 'username')
            self.PASSWORD = config.get('echo', 'password')
            self.WSDL_LOCATION = config.get('echo', 'wsdl_location')
            self.ENDPOINT = config.get('echo', 'endpoint')

        except configparser.NoSectionError:
            sys.stdout.write("""Region [echo] was not found in the configuration file. 
You must set the location to a configuration file using the environment variable  
INTERFACE_SECRETS_LOCATION or have a file named "secrets.conf". Check the documentation 
for an example layout of this file.""")
            self.USERNAME = ''
            self.PASSWORD = ''
            self.WSDL_LOCATION = ''
            self.ENDPOINT = ''


class BaseConnection:
    """
    BaseConnection has the core functionality required to interact with Echo's SOAP API.
    """

    def get_operations(self, key=None):
        """

        :param key: (str) key corresponding to a stored procedure. If empty will show all stored procedures
        :return: integer corresponding to stored procedure
        """
        operations = {
            'add': 5,
            'delete': 6,
            'execute': 0
        }
        if not key:
            for key, procedure in operations.items():
                print('{key}: {procedure}'.format(key=key, procedure=procedure))
            return
        return operations[key]

    @keep_warm
    def API_SelectParameters(self, screen_name, name_space='Symed'):
        """

        :param screen_name: (string) name of the screen
        :param name_space: (string) namespace that the screen belongs to
        :return: (string) usually a string in the form @name|value|type, where the name is the parameter name, value is the value of the parameter and type specifies the type (int, string, bool, decimal). There may be multiple and not all values will be filled in. If there was an error, a string in the format ?XXX|YYY? where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_SelectParameters(self.session_id, screen_name, name_space)

    @keep_warm
    def API_GeneralQuery(self, query, parameters=""):
        """

        :param query: the SQL-style query to be run
        :param parameters: optional set of parameters in form of @name|value|type, where the name is the parameter name, value is the value of the parameter and type specifies the type (int, string, guid, decimal).
        :return: usually XML with the requested results. If there was an error, a string in the format ?XXX|YYY? where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_GeneralQuery(self.session_id, query, parameters)

    @keep_warm
    def API_GetData(self, screen_name, name_space, parameters):
        """

        :param screen_name: the session id returned from a login.
        :param name_space: name of the screen
        :param parameters: the parameters for the select statement. It is possible to get the names of the parameters from the API_SelectParameters function, the values will need to be supplied by the programmer.
        :return: usually the XML data. If there was an error, a string in the format ?XXX|YYY? where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_GetData(self.session_id, screen_name, name_space, parameters)

    @keep_warm
    def API_UpdateData(self, tree_name, level_name, screen_name, name_space, parameters, dsXML):
        """

        :param tree_name: the name of tree (for providers, this is ?Locations?)
        :param level_name: the name of the level (for providers, this is ?Providers?)
        :param screen_name: name of the screen.
        :param name_space: the name space that the screen belongs to. Currently always ?Symed?.
        :param parameters: the parameters for the select statement. It is possible to get the names of the parameters from the API_SelectParameters function, the values will need to be supplied by the programmer.
        :param dsXML: the XML data containing the updates.
        :return: usually the XML data. If there was an error, a string in the format ?XXX|YYY? where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_UpdateData(self.session_id, tree_name, level_name, screen_name, name_space,
                                                  parameters, dsXML)

    @keep_warm
    def API_TreeDataCommand(self, tree_name, level_name, stored_proc, operation, param):
        """

        :param tree_name: the name of tree (for providers, this is ?Locations?)
        :param level_name: the name of the level (for providers, this is ?Providers?)
        :param stored_proc: the stored procedure that will perform the operation (for adding providers, this is PhysicianDetail_Create)
        :param operation: an integer that specifies the operation (0, 5 or 6) is (execute, add, delete). you can run self.get_operation() (self.get_operation('add') for example) to get the integer corresponding to your stored procedure.

        :return: usually a string in the format of name|value|type where the name is the parameter name, value is the parameter value and type is the parameter type. If this format is returned, the parameter can be used directly with API_GetData to retrieve the newly added item. If there was an error, a string in the format ?XXX|YYY? where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_TreeDataCommand(self.session_id, tree_name, level_name, stored_proc, operation, param)

    @keep_warm
    def API_CreateNoPenUser(self, email, body, subject, return_email, password, parameters, security_groups, send_mail):
        """

        :param email: the email address, this will also be the security login.
        :param body: body of the email (usually a string built up of other information, like name, email and password.
        :param subject: subject of the email.
        :param return_email: the return email address for the email.
        :param password: the password for the new user (not the API user password).
        :param parameters: the parameters for the provider to add.
        :param security_groups: (list, string) contains a list (or string separated by vertical bars ?|?) of security groups.
        :param send_mail: (bool) do we send the registration mail?
        :return: a string in the format ?XXX|YYY? where XXX is a general description (Error, Denied, Success, etc) and YYY is the specific description.
        """
        if issubclass(security_groups, list):
            security_groups = '|'.join(security_groups)

        return self.client.service.API_CreateNoPenUser(self.session_id, email, body, subject, return_email, password,
                                                       parameters, security_groups, send_mail)

    @keep_warm
    def API_Login(self, username, password):
        """

        :param username: the base user name. No domain, actual login id, not the display name.
        :param password: the password corresponding to the user name.
        :return: if successful, a string containing the session id, in the format ?SessionID|XXX? where XXX corresponds to the session id. If not successful, a string in the format ?XXX|YYY? where XXX is a general description (Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_Login(username, password)

    def API_Logout(self):
        """

        :return: a string in the format ?XXX|YYY? where XXX is a general description (Success, Error, Denied, etc) and YYY is the specific description.
        """
        return self.client.service.API_Logout(self.session_id)

    def API_Test(self):
        """

        :return: "Success|This message from WCF Service. You are connected!" or some kind of connection error probably
        """
        return self.client.service.API_Test()

    def __init__(self, settings=Settings(), *args, **kwargs):
        self.settings=settings
        self.endpoint = settings.ENDPOINT
        self.session = Session()
        self.client = Client(settings.WSDL_LOCATION, transport=Transport(session=self.session))
        if "Success" in self.client.service.API_Test():
            self.session_id = self.client.service.API_Login(settings.USERNAME, settings.PASSWORD).split("|")[1]
        else:
            raise APITestFailError("Test connection failed.")


class Helpers:
    """
    Helper Methods
    """

    class Meta:
        abstract = True

    def _search_schema(self, schema_str, show_all=True, **kwarg):
        """

        :param schema_str: (xml string) valid xml string
        :param show_all: (boolean) indicate whether we want all items returned in the search. setting to False returns last item only (sorted by the pass kwarg)
        :param kwarg: (kwarg) kwarg indicating search parameters. for example, if you have a bunch of items with a <name/>, you can search using:
            * Helpers()._search_schema(schema_str, name__eq="Billy") or Helpers()._search_schema(schema_str, name__contains="B")
        :return:
        """
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
        """
        :param physician_id: (int) id of desired physician
        :return:
        """
        qs = "SELECT * FROM PhysicianDetail WHERE PhysicianID={physician_id}".format(physician_id=physician_id)
        schema_str = self.API_GeneralQuery(qs, "")
        physician = self._search_schema(schema_str, show_all=False, PhysicianID__ne=-1)
        if physician:
            return physician['EntityGuid']
        else:
            raise APICallError('No Physicians matching id {physician_id}'.format(physician_id=physician_id))

    @staticmethod
    def _indent(elem, level=0):
        i = "\n{indention}".format(indention=level*'  ')
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = "{i} ".format(i=i)
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


class EchoConnection(Helpers, BaseConnection):
    """
    EchoConnection has numerous methods to facilitate the usage of the BaseConnection class.
    """

    @handle_response
    def add_physician(self, office_id, **kwargs):
        """

        :param office_id: (int) office that the new physician belongs to
        :param kwargs: (kwargs) values that you want the new physician to have, ex: LastName="Jones"

            * LastName
            * FirstName
            * DegreeID
            * EMail
            * Language
            * TimeEdited
            * PhysicianPhoto
            * DoctorNumber
            * Inactive
            * DateAdded
            * ProviderTypeID
            * DateUpdated
            * BirthState
            * EmailAllowed
            * AlternateEmailAllowed
            * CAQHPassword
            * MiddleName
            * Sex
            * MaritalStatus
            * SpouseName
            * HomeAddress
            * HomeCity
            * HomeState
            * HomeZip
            * SSN
            * DateOfBirth
            * BirthCity
            * Citizenship
            * Title
            * MobilePhone
            * NPI
            * StreetName
            * StreetNumber
            * DriverLicenseNumber
            * DriverLicenseExpiration
            * DriverLicenseState
            * HomePhone
            * BirthCountry
            * HomeCountry
            * CAQHID
            * PhysicianPhotoSecondary
            * UPIN
            * MaidenName
            * HomeAddress2
            * VISAStatus
            * OtherNameStart
            * OtherNameStop
            * AlternateEmail
            * VisaNumber
            * PreferredContactMethod
            * Beeper
            * BirthCounty
            * HomeCounty
            * SuffixName
            * Medicare
            * AlliedHealthProfessional
            * EnrollmentStatusID
            * CAQHLogin
            * HomeFax
        :return:
        """
        args = ["Locations", "Provider", "PhysicianDetail_Create", 5, "@OfficeID|{office_id}|int".format(office_id=office_id)]
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
        """

        :param physician_id: (int) physician to whom to medical license belongs
        :param kwargs:  (kwargs) values that you want the new physician to have (ex:

            * LicenseStateOfIssue
            * LicenseNumber
            * LicenseDateOfIssue
            * LicenseExpirationDate
            * LicenseType
            * Notified
            * Active
            * TimeEdited
            * DateUpdated
            * LicenseTypeSpecialty
            * ProviderTypeID
            * LicenseStatus
            * LicenseRenewalDate
            * LicenseCountry
        :return:
        """
        license_data = self.get_medical_licenses(physician_id)
        schema_and_data = ET.fromstring(license_data)
        for i, (key, value) in enumerate(kwargs.items()):
            if i == 0:
                new_table = ET.SubElement(schema_and_data[1], 'Table')
            new_attr = ET.SubElement(new_table, key)
            new_attr.text = str(value)
        updated_schema = ET.tostring(schema_and_data)
        args = ["Locations", "Provider", "MedicalLicenses", "Symed",
                '@PhysicianID|{physician_id}|int'.format(physician_id=physician_id), updated_schema]
        return self.API_UpdateData(*args)

    @handle_response
    def add_contact_log_entry(self, physician_id, **kwargs):
        """

        :param physician_id: id of the physician to whom the note will be attached
        :param kwargs: keyword arguments corresponding to fields added to the log

            * FollowUpCompleted (boolean string) :: true/false
            * ContactLogTypeId (int string)
            * Notes (string)
            * Subject (string)
            * ContactID (int string)
            * ContactDate (isoformat datetime string YYYY-MM-DDTHH:mm:ss)
        :return:
        """
        required = {'Notes', 'Subject'}
        if required.intersection(kwargs.keys()) != required:
            raise APICallError('You must add "Notes" and "Subject" to contact log entries.')
        guid = self._get_physician_guid(physician_id)
        log_data = self.get_contact_log(physician_id)
        schema_and_data = ET.fromstring(log_data)
        kwargs['EntityGuid'] = guid
        kwargs['TrackingGuid'] = '00000000-0000-0000-0000-000000000000'
        # kwargs['TrackingGuid'] = str(uuid.uuid4())
        kwargs['TimeEdited'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        kwargs['UserDisplayName'] = 'Back-end API User'
        for i, (key, value) in enumerate(kwargs.items()):
            if i == 0:
                new_table = ET.SubElement(schema_and_data[1], 'Table')
            new_attr = ET.SubElement(new_table, key)
            new_attr.text = str(value)
        updated_schema = ET.tostring(schema_and_data)
        args = ["Locations", "Provider", "CallLog", "Symed",
                '@EntityGuid|{guid}|guid'.format(guid=guid), updated_schema]
        return XMLSchema(self.API_UpdateData(*args)).search(CallID__ne='-1')

    @handle_response
    def add_office(self, practice_id=""):
        """
        This method does not yet have the capability to modify the newly created office; There does not yet exist an
        edit_office method.

        :param practice_id: (int) practice with which to associate this new office
        :return:
        """
        if not practice_id:
            raise APICallError("You must provide a practice_id with which to associate this office.")
        args = ["Locations", "Office", "Offices_Create", 5, "@PracticeID|{practice_id}|int".format(practice_id=practice_id)]
        return self.API_TreeDataCommand(*args)

    # TODO add edit_office method and update add_office method
    @handle_response
    def edit_physician(self, physician_id, **kwargs):
        """

        :param physician_id: (int) id of physician to be edited
        :param kwargs:
            * see add_physician for full list of kwargs
        :return:
        """
        physician = self.get_physician(physician_id)
        schema_and_data = ET.fromstring(physician)
        for key, value in kwargs.items():
            if schema_and_data[1][0].find(key) is None:
                new_attr = ET.SubElement(schema_and_data[1][0], key)
                new_attr.text = value
            else:
                schema_and_data[1][0].find(key).text = str(value)
        updated_schema = ET.tostring(schema_and_data)
        # print_xml(updated_schema)
        args = ["Locations", "Provider", "PhysicianDetail",
                "Symed", "@PhysicianID|{physician_id}|int".format(physician_id=physician_id), updated_schema]
        return self.API_UpdateData(*args)

    @handle_response
    def delete_physician(self, physician_id="", office_id=""):
        """

        :param physician_id: (int) id of physician that will be deleted
        :param office_id: (int) id of office that physician is being removed from. will delete physician if it's the last office
        :return:
        """
        if not (physician_id and office_id):
            raise APICallError("You must specify both the physician_id and office_id.")
        args = ["Locations", "Provider", "PhysicianDetail_Delete", 6,
                "@PhysicianID|{physician_id}|int@OfficeID|{office_id}|int".format(physician_id=physician_id, office_id=office_id)]
        return self.API_TreeDataCommand(*args)

    @handle_response
    def delete_office(self, office_id=""):
        """

        :param office_id: (int) id of office to be deleted
        :return:
        """
        if not office_id:
            raise APICallError("You must specify the office_id.")
        args = ["Locations", "Office", "Offices_Delete", 6,
                "@OfficeID|{office_id}|int".format(office_id=office_id)]
        return self.API_TreeDataCommand(*args)

    @handle_response
    def delete_contact_log_entry(self, physician_id, call_id="", limit=2, **kwarg):
        """

        :param physician_id: (int) id of physician that the log entry belongs to
        :param call_id:  (int, optional) id of the call log entry to be deleted
        :param limit: (int) limits the number of logs to be deleted so you don't accidentally delete more than you meant to
        :param kwarg: (kwarg) search term that tells the XMLSchema object which items need to be deleted, allows almost all default python comparison methods (__lt__, __gt__, __ge__, __ne__, __eq__, etc.), though not all of them are guaranteed to work in every situation. This feature might break with some searches.

            * connection.delete_contact_log_entry(1, call_id=2) will delete the call log with CallID=2
                * connection.delete_contact_log_entry(1, CallID=2) will do the same
                * connection.delete_contact_log_entry(1, CallID__eq=2) will also
            * connection.delete_contact_log_entry(1, limit=20, CallID__ne='-1') will delete up to 20 call log entries where the CallID is not -1 (so it deletes all of them)
            * connection.delete_contact_log_entry(1, TimeEdited__lt=<insert isoformat timestampe>) will fail to delete the call log with edited before the date unless there is only one that matches the query
            * note that only CallID and TimeEdited searches will ever work due to a combination of factors.

        :return:
        """
        if call_id:
            kwarg['CallID'] = str(call_id)
        contact_log = self.get_contact_log(physician_id)
        guid = self._get_physician_guid(physician_id)
        schema_and_data = XMLSchema(contact_log)
        num_delete = len(schema_and_data.search(**kwarg))
        if num_delete <= limit and num_delete != 0:
            schema_and_data.delete_elements_where(**kwarg)
            updated_schema_str = ET.tostring(schema_and_data.schema)
            args = ["Locations", "Provider", "CallLog", "Symed", '@EntityGuid|{guid}|guid'.format(guid=guid),
                    updated_schema_str]
            return self.API_UpdateData(*args)

        elif num_delete == 0:
            raise APICallError('Could not find CallLog matching {kwarg}.'.format(kwarg=kwarg))

        else:
            raise APICallError('Attempted to delete {num_delete} items, which exceeds the limit of {limit}.'
                               ' If you wish to delete all {num_delete} items, you may set limit={num_delete} '
                               'when calling this method.'.format(num_delete=num_delete, limit=limit))

    @handle_response
    def get_physician(self, physician_id):
        """
        equivalent of self.API_GetData(*args) for the indicated physician

        :param physician_id: (int) id of physician whose data we desire
        :return: (xml string) whatever self.API_GetData(*args) returns
        """
        args = ["PhysicianDetail", "Symed", "@PhysicianID|{physician_id}|int".format(physician_id=physician_id)]
        return self.API_GetData(*args)

    @handle_response
    def get_office(self, office_id):
        """
        equivalent of self.API_GetData(*args) for the indicated office

        :param office_id: (int) id of whichever office we desire
        :return: (xml string) whatever self.API_GetData(*args) returns
        """
        args = ["Office", "Symed", "@OfficeID|{office_id}|int".format(office_id=office_id)]
        return self.API_GetData(*args)

    @handle_response
    def get_medical_licenses(self, physician_id):
        """
        equivalent of self.API_GetData(*args) for the medical licenses of the indicated physician

        :param physician_id: (int) id of whichever physician's licenses we desire
        :return: (xml string) whatever self.API_GetData(*args) returns
        """
        args = ["MedicalLicenses", "Symed", "@PhysicianID|{physician_id}|int".format(physician_id=physician_id)]
        return self.API_GetData(*args)

    @handle_response
    def get_contact_log(self, physician_id):
        """
        equivalent of self.API_GetData(*args) for the contact logs of the indicated physician

        :param physician_id: (int) id of whichever physician's logs we desire
        :return:
        """
        guid = self._get_physician_guid(physician_id)
        args = ["CallLog", "Symed", '@EntityGuid|{guid}|guid'.format(guid=guid)]
        return self.API_GetData(*args)

    @handle_response
    def show_physician(self, physician_id):
        """

        :param physician_id: (int) id of desired physician
        :return: xmlmanip.InnerSchemaDict (can be used as dict) of info
        """
        schema_str = self.get_physician(physician_id)
        return self._search_schema(schema_str, PhysicianID__ne=-1)

    @handle_response
    def show_physician_medical_licenses(self, physician_id, show_all=True):
        """

        :param physician_id: (int) id of desired physician
        :param show_all: (boolean) if True shows all, if False shows last created
        :return: xmlmanip.InnerSchemaDict or xmlmanip.SearchableList (can be used as dict) of info
        """
        schema_str = self.get_medical_licenses(physician_id)
        return self._search_schema(schema_str, show_all=show_all, AutoID__ne=-1)

    @handle_response
    def show_office(self, office_id):
        """

        :param office_id: (int) id of desired office
        :return: xmlmanip.InnerSchemaDict or xmlmanip.SearchableList (can be used as dict) of info
        """
        schema_str = self.get_office(office_id)
        return self._search_schema(schema_str, show_all=False, OfficeID__ne=-1)

    @handle_response
    def show_physician_contact_log(self, physician_id, show_all=True):
        """

        :param physician_id: (int) id of desired physician
        :param show_all: (boolean) if True shows all, if False shows last created
        :return: xmlmanip.InnerSchemaDict or xmlmanip.SearchableList (can be used as dict) of info
        """
        guid = self._get_physician_guid(physician_id)
        args = ["CallLog", "Symed", '@EntityGuid|{guid}|guid'.format(guid=guid)]
        schema_str = self.API_GetData(*args)
        return self._search_schema(schema_str, show_all=show_all, CallID__ne=-1)

    @handle_response
    def show_offices(self, show_all=True):
        """

        :param show_all: (boolean) if True shows all, if False shows last created
        :return: xmlmanip.InnerSchemaDict or xmlmanip.SearchableList (can be used as dict) of info
        """
        qs = "SELECT * FROM Offices"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, OfficeID__ne=-1)

    @handle_response
    def show_practices(self, show_all=True):
        """

        :param show_all: (boolean) if True shows all, if False shows last created
        :return: xmlmanip.InnerSchemaDict or xmlmanip.SearchableList (can be used as dict) of info
        """
        qs = "SELECT * FROM Offices WHERE OfficeID = PracticeID"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, OfficeID__ne=-1)

    @handle_response
    def show_physicians(self, show_all=True):
        """

        :param show_all: (boolean) if True shows all, if False shows last created
        :return: xmlmanip.InnerSchemaDict or xmlmanip.SearchableList (can be used as dict) of info
        """

        qs = "SELECT * FROM PhysicianDetail"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, PhysicianID__ne=-1)

    @handle_response
    def show_contact_logs(self, show_all=True):
        """

        :param show_all: (boolean) if True shows all, if False shows last created
        :return: xmlmanip.InnerSchemaDict or xmlmanip.SearchableList (can be used as dict) of info
        """
        qs = "SELECT * FROM ContactLog"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, CallID__ne=-1)

    @handle_response
    def show_medical_licenses(self, show_all=True):
        """

        :param show_all: (boolean) if True shows all, if False shows last created
        :return: xmlmanip.InnerSchemaDict or xmlmanip.SearchableList (can be used as dict) of info
        """
        qs = "SELECT * FROM MedicalLicenses"
        schema_str = self.API_GeneralQuery(qs, "")
        return self._search_schema(schema_str, show_all=show_all, AutoID__ne=-1)


@wrap_methods
class EchoDebug(EchoConnection):
    """
    This class adds some quality-of-life improvements to the BaseConnection class.

    - WRAPPED_METHODS are wrapped by WRAPPER_METHOD_NAMES
    - wrappers can be toggled on and off during PaycomConnection instanciation.

    example:
    - paycom = PaycomConnection(show_messages=True, log_errors=False, keep_authenticated=False, serialize=False)

    default:
    - paycom = PaycomConnection(show_messages=False, log_errors=True, keep_authenticated=True, serialize=True)
    """
    WRAPPER_METHOD_NAMES = ['show_signature']
    WRAPPED_METHODS = ['API_SelectParameters', 'API_GeneralQuery', 'API_GetData', 'API_UpdateData', 'API_TreeDataCommand', 'API_CreateNoPenUser', 'API_Login', 'API_Logout']
    MESSAGE_OVERRIDE_MAP = {}

    def show_xml(self, method, *args, **kwargs):
        if self._show_xml:
            try:
                print_xml(args[-1])
            except:
                print(f"Final {method.__name__} argument not XML")
        response = method(*args, **kwargs)
        return response

    def show_signature(self, method, *args, **kwargs):
        if self._show_signature:
            print(f'{method.__name__}{inspect.signature(method)}')
        if self._show_args:
            if 'dsXML' in str(inspect.signature(method)):
                arg_string = ', '.join([f'"{arg}"' for arg in args[:-1]])
                arg_string += ', *dsXML'
            else:
                arg_string = ', '.join([f'"{arg}"' for arg in args])
            print(f'{method.__name__}({arg_string})')
        if self._show_xml and 'dsXML' in str(inspect.signature(method)):
            print_xml(args[-1])

        response = method(*args, **kwargs)
        return response

    def __init__(self, settings=Settings(), show_xml=True, show_signature=True, show_args=True, *args, **kwargs):
        super(EchoConnection, self).__init__(settings, *args, **kwargs)
        self._show_xml = show_xml
        self._show_signature = show_signature
        self._show_args = show_args
        # the docstring is more useful if it the BaseConnection docstring is shown first,
        EchoDebug.__doc__ = EchoConnection.__doc__ + self.__doc__
        self.__doc__ = EchoDebug.__doc__

