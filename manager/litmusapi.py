import httplib
import logging
from xml.dom import minidom

from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
import requests

log = logging.getLogger(__name__)


class LitmusApi(object):
    """
    API used to communicate with Litmus.
    http://docs.litmus.com/w/page/18056603/Customer%20API%20documentation
    """

    CLIENTS = 'emails/clients.xml'
    EMAILS = 'emails.xml'
    TESTS = 'tests/'

    def __init__(self, base_url, username, password, timeout=30, verify=False):
        """
        Initializes the handler.

        :param url: base URL to make requests against
        :param username: API Username
        :param password: API Password
        """
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)
        self.headers = {'Content-Type': 'application/xml',
                        'Accept': 'application/xml'}
        self.timeout = timeout
        self.verify = verify

    def get_clients(self):
        """
        Gets all the clients that can be used for testing
        """
        return self.get_request(self.base_url + LitmusApi.CLIENTS)

    def create_test(self):
        """
        Creates an email test with all the available email clients.
        """
        xml = '<?xml version="1.0" encoding="UTF-8"?>' + \
              '<test_set><applications type="array">'

        # Get all the clients and add them to the request
        clients_xml = self.get_clients()
        client_list = clients_xml.getElementsByTagName('application_code')

        # Get all the client ids and add them to the test
        for client_node in client_list:
            client = client_node.childNodes[0].nodeValue
            xml = xml + '<application><code>' + client + \
                        '</code></application>'

        xml = xml + '</applications><save_defaults>false</save_defaults>' + \
                    '<use_defaults>false</use_defaults></test_set>'

        return self.post_request(self.base_url + LitmusApi.EMAILS,
                                 xml)

    def get_test(self, test_id):
        """
        Return the test information for test_id.

        :param test_id: ID for the test email
        """
        return self.get_request(self.base_url + LitmusApi.TESTS +
                                str(test_id) + '.xml')

    def get_request(self, url):
        """
        Performs a GET request with the given url

        :param url: URL to make the request against
        :return: Response
        :rtype: xml
        """
        try:
            response = requests.get(url=url,
                                    auth=self.auth,
                                    headers=self.headers,
                                    timeout=self.timeout,
                                    verify=self.verify)

            if response.status_code != httplib.OK:
                logging.error('Could not make GET request using url ' + url +
                              ' Response headers: ' + str(response.headers))
                return None
        except RequestException as e:
            log.error('Could not connect to Litmus', e)

        return minidom.parseString(response.text)

    def post_request(self, url, data):
        """
        Performs a POST request with the given url and data

        :param url: URL to make the request against
        :param data: data that will be pass with the request
        :return: Response location
        :rtype: xml
        """

        response = requests.post(url=url,
                                 auth=self.auth,
                                 data=data,
                                 headers=self.headers,
                                 timeout=self.timeout,
                                 verify=self.verify)

        if response.status_code != httplib.CREATED:
            logging.error('Could not make POST request using url ' + url +
                          ' Response header: ' + str(response.headers))
            return None

        return minidom.parseString(response.text)
