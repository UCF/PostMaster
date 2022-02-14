import logging
import re
import smtplib

from django.conf import settings

from manager.models import RecipientAttribute
from manager.utilities.email_message import EmailMessage


log = logging.getLogger(__name__)


class EmailSender:
    '''
    This helper class will send an email without creating
    an Email Instance
    '''
    email = None
    recipients = None
    html = None
    status_code = None

    def __init__(self, email, recipients):
        self.email = email
        self.recipients = recipients
        self.status_code, self.html = self.email.html

    @property
    def placeholders(self):
        delimiter = self.email.replace_delimiter
        placeholders = re.findall(re.escape(delimiter) + '(.+)' + re.escape(delimiter), self.html)
        return [p for p in placeholders if p.lower() != 'unsubscribe']

    def get_attributes(self, recipient):
        attributes = {}
        atts = RecipientAttribute.objects.filter(recipient=recipient)
        for att in atts:
            attributes[att.name] = att.value

        return attributes

    def send(self):

        try:
            amazon = smtplib.SMTP_SSL(settings.AMAZON_SMTP['host'], settings.AMAZON_SMTP['port'])
            amazon.login(settings.AMAZON_SMTP['username'], settings.AMAZON_SMTP['password'])
        except:
            log.exception('Unable to connect to amazon')
        else:
            for recipient in self.recipients:
                # Get recipient attributes
                attributes = self.get_attributes(recipient)
                # Customize the email for this recipient
                customized_html = self.html
                # Replace template placeholders
                delimiter = self.email.replace_delimiter
                for placeholder in self.placeholders:
                    replacement = ''
                    if placeholder.lower() != 'unsubscribe':
                        if attributes[placeholder] is None:
                            log.error('Recipient %s is missing attribute %s' % (str(recipient), placeholder))
                        else:
                            replacement = attributes[placeholder]
                        customized_html = customized_html.replace(delimiter + placeholder + delimiter, replacement)

                msg = EmailMessage(
                    subject=self.email.subject,
                    from_friendly_name=self.email.from_friendly_name,
                    from_address=self.email.from_email_address,
                    to_address=recipient.email_address,
                    html=customized_html
                )
                try:
                    amazon.sendmail(self.email.from_email_address, recipient.email_address, msg.as_string())
                except smtplib.SMTPException as e:
                    log.exception('Unable to send email.')
            amazon.quit()
