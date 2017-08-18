import os, json, importlib
from requests import Session

from zeep import Client
from zeep.transports import Transport


class APITestFailError(BaseException):
    pass


class ImproperlyConfigured(BaseException):
    pass


class Settings:

    def __init__(self, secrets_location='secrets.json'):
        try:
            with open(secrets_location, 'r') as secrets:
                secrets = json.load(secrets)
            self.USERNAME = secrets['USERNAME']
            self.PASSWORD = secrets['PASSWORD']
            self.WSDL_LOCATION = secrets["WSDL_LOCATION"]
            self.ENDPOINT = secrets["ENDPOINT"]

        except FileNotFoundError:
            print("echo_api is not properly configured and will not perform as expected. You must designate a fully "
                  "defined path to your secrets file. See documentation for more information.")
            self.USERNAME = ''
            self.PASSWORD = ''
            self.WSDL_LOCATION = ''
            self.ENDPOINT = ''


class Connection:

    def __init__(self, settings=Settings()):
        self.endpoint = settings.ENDPOINT
        self.session = Session()
        self.client = Client(settings.WSDL_LOCATION, transport=Transport(session=self.session))
        if "Success" in self.client.service.API_Test():
            self.session_id = self.client.service.API_Login(settings.USERNAME, settings.PASSWORD).split("|")[1]
        else:
            raise APITestFailError("Test connection failed.")
