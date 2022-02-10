import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailMessage:
    '''
    Helper class that handles generation of an email message
    string with necessary headers and character encoding
    to pass along to Amazon for sending.
    '''
    msg = None
    subject = None
    from_friendly_name = None
    from_address = None
    to_address = None
    html = None
    text = None

    def __init__(self, subject, from_friendly_name, from_address, to_address, html=None, text=None):
        # Always generate a MIMEMultipart message here.
        # TODO support MIMEText for SimpleEmailSender?
        self.subject = subject
        self.from_friendly_name = from_friendly_name
        self.from_address = from_address
        self.to_address = to_address

        self.msg = MIMEMultipart('alternative')
        self.msg['subject'] = self.get_subject()
        self.msg['From'] = self.get_from()
        self.msg['To'] = self.to_address

        if html:
            self.attach_html(html)
        if text:
            self.attach_text(text)

    def get_subject(self):
        '''
        Returns an encoded email header string for the
        message's subject line.
        More info: https://docs.aws.amazon.com/ses/latest/dg/send-email-raw.html#send-email-mime-encoding-headers
        '''
        return '=?utf-8?B?{0}?='.format(self.base64_encode(self.subject))

    def get_from(self):
        '''
        Returns a formatted "from" name/address for the message.
        '''
        if self.from_friendly_name:
            return '"{0}" <{1}>'.format(self.from_friendly_name, self.from_address)
        else:
            return self.from_address

    def base64_encode(self, msg_str):
        '''
        Returns a base64-encoded string.
        More info:
        http://docs.aws.amazon.com/ses/latest/DeveloperGuide/send-email-raw.html#send-email-mime-encoding
        '''
        # Normalize back to a string
        msg_str = str(msg_str)

        b64_str = msg_str.encode('utf-8')
        b64_str = base64.b64encode(b64_str)
        b64_str = b64_str.decode('utf-8')

        return b64_str

    def attach_html(self, html):
        '''
        Encodes and attaches an HTML string to the message.
        '''
        self.html = html
        html_encoded = html.encode('utf-8')
        self.msg.attach(MIMEText(html_encoded, 'html', _charset='utf-8'))

    def attach_text(self, text):
        '''
        Encodes and attaches a plain text string to the message.
        '''
        self.text = text
        text_encoded = text.encode('utf-8')
        self.msg.attach(MIMEText(text_encoded, 'plain', _charset='utf-8'))

    def as_string(self):
        '''
        Returns the email message as a ready-to-send string.
        '''
        return self.msg.as_string()
