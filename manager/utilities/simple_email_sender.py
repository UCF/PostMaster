import logging
import smtplib

from email.mime.text import MIMEText
from django.conf import settings


log = logging.getLogger(__name__)


class SimpleEmailSender:
    '''
    Utility class for sending simple text
    emails.
    '''

    def __init__(self, subject, from_email, from_friendly, text, recipients):
        self.subject = subject
        self.from_email = from_email
        self.from_friendly = from_friendly
        self.text = text
        self.recipients = recipients

    def send(self):
        try:
            amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
            amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
        except:
            print('Unable to connect to amazon')
            log.exception('Unable to connect to amazon')
        else:
            for recipient in self.recipients:
                msg = MIMEText(self.text)
                msg['subject'] = self.subject
                msg['From'] = f"{self.from_friendly} <{self.from_email}>"
                msg['To'] = recipient

                try:
                    amazon.sendmail(self.from_email, recipient, msg.as_string())
                except smtplib.SMTPException as e:
                    log.exception('Unable to send email.')
            amazon.quit()
