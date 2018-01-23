import httplib
import logging
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

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
        text_xml = None

        # Get all the clients and add them to the request
        clients_xml = self.get_clients()
        element_type = type(Element(None))
        if clients_xml and isinstance(clients_xml, element_type):
            xml = '<?xml version="1.0" encoding="UTF-8"?>' + \
                  '<test_set><applications type="array">'

            client_list = clients_xml.findall('./testing_application/application_code')

            # Get all the client ids and add them to the test
            for client_node in client_list:
                client = client_node.text
                xml = xml + '<application><code>' + client + \
                            '</code></application>'

            xml = xml + '</applications><save_defaults>false</save_defaults>' + \
                        '<use_defaults>false</use_defaults></test_set>'

            text_xml = self.post_request(self.base_url + LitmusApi.EMAILS,
                                         xml)

        return text_xml

    def get_test(self, test_id):
        """
        Return the test information for test_id.

        :param test_id: ID for the test email
        """
        return self.get_request(self.base_url + LitmusApi.TESTS +
                                str(test_id) + '.xml')

    def get_test_id(self, xml):
        """
        Returns the email test id

        :param xml: Test email xml document
        """
        test_id = None
        element_type = type(Element(None))
        if xml and isinstance(xml, element_type):
            test_id_xml = xml.find('./id')
            if test_id_xml is not None:
                test_id = test_id_xml.text

        return test_id

    def get_email_address(self, xml):
        """
        Returns the email address for the litmus test

        :param xml: Litmus test xml document
        """
        email = None
        element_type = type(Element(None))
        if xml and isinstance(xml, element_type):
            email_xml = xml.findall('./test_set_versions/test_set_version/url_or_guid')
            if email_xml is not None:
                email = email_xml[0].text

        return email

    def get_image_urls(self, client_code, test_id=None, xml=None):
        """
        Returns the thumbnail url for the specificed client

        :param client_code: Email client code
        :param test_id: ID of the email test
        :param xml: test email xml document
        """
        urls = None

        if client_code and (xml or test_id):
            # prefer the xml document over the test ID if both are given
            if not xml and test_id:
                xml = self.get_test(test_id)

            element_type = type(Element(None))
            if xml is not None and isinstance(xml, element_type):
                client_tests = xml.findall('./test_set_versions/test_set_version/results/result')

                # loop through the clients and get the client specified
                for client_test in client_tests:
                    xml_test_code = client_test.find('test_code')
                    if isinstance(xml_test_code, element_type) and client_code == xml_test_code.text:
                        xml_images = client_test.findall('result_images/result_image')
                        xml_image = self.get_full_on(xml_images)
                        if xml_image is not None:
                            thumbnail_url = xml_image.find('thumbnail_image')
                            full_image = xml_image.find('full_image')

                            if isinstance(thumbnail_url, element_type) and isinstance(full_image, element_type):
                                thumbnail_url = thumbnail_url.text
                                full_image = full_image.text
                                urls = {'thumbnail_url': thumbnail_url,
                                        'full_url': full_image}
        else:
            log.warning('Could not retrieve the thumbnail url because' +
                        ' the xml or client code is empty.')

        return urls

    def get_full_on(self, xml_images):
        """
        Get the full on image type

        :param xml_images: xml document
        """
        result_image = None

        if xml_images is not None and isinstance(xml_images, list):
            for xml_image in xml_images:
                image_type = xml_image.find('image_type')
                element_type = type(Element(None))
                if isinstance(image_type, element_type) and 'full_on' == image_type.text:
                    result_image = xml_image
                    break

        return result_image

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
            return None

        return ET.fromstring(response.text.encode('utf-8'))

    def post_request(self, url, data):
        """
        Performs a POST request with the given url and data

        :param url: URL to make the request against
        :param data: data that will be pass with the request
        :return: Response location
        :rtype: xml
        """
        try:
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
        except RequestException as e:
            log.error('Could not connect to Litmus', e)
            return None

        return ET.fromstring(response.text.encode('utf-8'))
