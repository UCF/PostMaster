from django.core.management.base import BaseCommand
from django.db import connection, transaction
from manager.models import Email
from datetime import datetime, date, timedelta
import logging
import settings

log = logging.getLogger(__name__)


class Command(BaseCommand):
    '''
        Handles sending emails. Should be set to run according to the
        PROCESSING_INTERVAL_DURATION setting in settings_local.py
    '''

    def handle(self, *args, **options):
        log.info('The mailer-process command is starting...')

        now = datetime.now()
        self.calculate_estimates(start_datetime=now)
        previews = Email.objects.previewing_now(now=now)
        instances = Email.objects.sending_now(now=now)

        # log.info('There is/are %d preview(s) to send.' % len(previews))
        # for email in previews:
        #     log.info('Previewing the following email now: %s ' % email.title)
        #     email.send_preview()
        #
        # log.info('There is/are %d instance(s) to send.' % len(instances))
        # for email in instances:
        #     log.info('Sending the following email now: %s' % email.title)
        #     email.send()
        #
        # log.info('The mailer-process command is finished.')

    def calculate_estimates(self, start_datetime=datetime.now()):
        self.clear_time_est(today=start_datetime.date())

        # set estimated preview sending time
        time_interval = timedelta(seconds=settings.PROCESSING_INTERVAL_DURATION)
        pre_time_offset = timedelta(seconds=(settings.PREVIEW_LEAD_TIME + settings.PROCESSING_INTERVAL_DURATION))
        end_datetime = (start_datetime + timedelta(days=1)).replace(hour=0, minute=0, second=0)

        # no_preview_est = Email.objects.sending_today_no_pre_est()
        # if no_preview_est.exists():
        #     for email in no_preview_est:
        #         for next_datetime in time_range(start_datetime, end_datetime, time_interval):
        #             if email.preview_est_time is None and email.send_time < (next_datetime + pre_time_offset).time():
        #                 cursor = connection.cursor()
        #                 cursor.execute('UPDATE manager_email SET preview_est_time = %s WHERE id = %s',
        #                                [next_datetime, email.id])
        #                 transaction.commit_unless_managed()
        #
        #                 # Updated time so go to next email
        #                 break
        #
        # # set estimated live sending time
        # live_time_offset = timedelta(seconds=settings.PROCESSING_INTERVAL_DURATION)
        # no_live_est = Email.objects.sending_today_no_live_est()
        # if no_live_est.exists():
        #     for email in no_live_est:
        #         for next_datetime in time_range(start_datetime, end_datetime, time_interval):
        #             if email.live_est_time is None and email.send_time < (next_datetime + live_time_offset).time():
        #                 cursor = connection.cursor()
        #                 cursor.execute('UPDATE manager_email SET live_est_time = %s WHERE id = %s',
        #                                [next_datetime, email.id])
        #                 transaction.commit_unless_managed()
        #
        #                 # Updated time so go to next email
        #                 break

        no_preview_est = Email.objects.sending_today_no_pre_est()
        if no_preview_est.exists():
            for email in no_preview_est:
                for next_datetime in time_range(start_datetime, end_datetime, time_interval):
                    if email.preview_est_time is None and email.send_time < (next_datetime + pre_time_offset).time():
                        email.preview_est_time = next_datetime
                        email.save()

                        # Updated time so go to next email
                        break


        # set estimated live sending time
        live_time_offset = timedelta(seconds=settings.PROCESSING_INTERVAL_DURATION)
        no_live_est = Email.objects.sending_today_no_live_est()
        if no_live_est.exists():
            for email in no_live_est:
                for next_datetime in time_range(start_datetime, end_datetime, time_interval):
                    if email.live_est_time is None and email.send_time < (next_datetime + live_time_offset).time():
                        email.live_est_time = next_datetime
                        email.save()

                        # Updated time so go to next email
                        break

    def clear_time_est(self, today=date.today()):
        """Clears the email time to send estimates
        """

        # clear all emails that aren't today
        emails_not_sending = Email.objects.not_sending_today(today=today)
        for email in emails_not_sending:
            email.live_est_time = None
            email.preview_est_time = None
            email.save()
            # cursor = connection.cursor()
            # cursor.execute('UPDATE manager_email SET live_est_time = NULL and preview_est_time = NULL WHERE id = %s',
            #                [email.id])
            # transaction.commit_unless_managed()

        # clear all emails that are today but preview times and live times that are old
        # (primarily for daily emails from yesterday)
        emails_sending_old_est = Email.objects.sending_today_old_est(today=today)
        for email in emails_sending_old_est:
            email.live_est_time = None
            email.preview_est_time = None
            email.save()
            # cursor = connection.cursor()
            # cursor.execute('UPDATE manager_email SET live_est_time = NULL, preview_est_time = NULL WHERE id = %s',
            #                [email.id])
            # transaction.commit_unless_managed()


def time_range(start_datetime, end_datetime, time_interval):
    while start_datetime <= end_datetime:
        yield start_datetime
        start_datetime += time_interval