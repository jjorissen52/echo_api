import unittest


class TestShowers(unittest.TestCase):
    from echo_api.api import EchoConnection

    connection = EchoConnection()

    def body(self):
        self.connection.show_physician(1)
        self.connection.show_medical_licenses(1)
        self.connection.show_office(1)
        self.connection.show_physician_contact_log(1)
        self.connection.show_latest_office()
        self.connection.show_latest_practice()
        self.connection.show_latest_physician()
        self.connection.show_latest_contact_log()
        self.connection.show_latest_medical_license()

    def test_showers(self):
        self.body()


class TestGetters(unittest.TestCase):
    from echo_api.api import EchoConnection

    connection = EchoConnection()

    def body(self):
        self.connection.get_physician(1)
        self.connection.get_office(1)
        self.connection.get_medical_licenses(1)
        self.connection.get_contact_log(1)

    def test_getters(self):
        self.body()



def run():
    unittest.main()

if __name__ == "__main__":
    run()