import os, json, importlib
from requests import Session

from zeep import Client
from zeep.transports import Transport


class APITestFailError(BaseException):
    pass


class ImproperlyConfigured(BaseException):
    pass


class Settings:
    BASE_DIR = os.path.dirname(__file__)
    SECRETS_LOCATION = 'secrets.json'

    try:
        with open(SECRETS_LOCATION, 'r') as secrets:
            secrets = json.load(secrets)
        USERNAME = secrets['USERNAME']
        PASSWORD = secrets['PASSWORD']
        WSDL_LOCATION = secrets["WSDL_LOCATION"]
        ENDPOINT = secrets["ENDPOINT"]

    except FileNotFoundError:
        print("This package is not properly configured and will not perform as expected. You must designate a secrets "
              "file. See documentation for more information.")
        USERNAME = ''
        PASSWORD = ''
        WSDL_LOCATION = ''
        ENDPOINT = ''

settings = Settings()


class Connection:
    endpoint = settings.ENDPOINT
    session = Session()
    client = Client(settings.WSDL_LOCATION, transport=Transport(session=session))

    def __init__(self):
        if "Success" in self.client.service.API_Test():
            self.session_id = self.client.service.API_Login(settings.USERNAME, settings.PASSWORD).split("|")[1]
        else:
            raise APITestFailError("Test connection failed.")
