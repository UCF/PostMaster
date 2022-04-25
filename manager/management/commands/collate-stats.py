from django.core.management.base import BaseCommand, CommandError

from threading import Thread, Lock
from queue import Queue

from manager.models import Campaign, CampaignInstanceStat
from progress.bar import ChargingBar

class Command(BaseCommand):
    help = 'Collates campaign stats in the stats tables'

    def add_arguments(self, parser):
        parser.add_argument(
            '--thread-count',
            dest='thread_count',
            type=int,
            help='The number of threads to use while updating stats',
            default=10
        )

        parser.add_argument(
            '--show-progress',
            dest='show_progress',
            action='store_true',
            help='Shows a progress bar',
            default=False
        )

    def __init__(self):
        super().__init__()

        self.instance_queue_lock = Lock()
        self.campaign_queue_lock = Lock()
        self.instance_queue = Queue()
        self.campaign_queue = Queue()

        self.instance_count = 0
        self.campaign_count = 0
        self.instance_count_lock = Lock()
        self.campaign_count_lock = Lock()

        self.pb_lock = Lock()

    def update_instances(self, q):
        while True:
            try:
                with self.instance_queue_lock:
                    obj = q.get()
                    instance = obj['instance']
                    campaign = obj['campaign']

                if campaign and instance:
                    try:
                        instance_stat = CampaignInstanceStat.objects.get(campaign=campaign, instance=instance)
                    except CampaignInstanceStat.DoesNotExist:
                        instance_stat = CampaignInstanceStat(campaign=campaign, instance=instance)
                        instance_stat.save()

                    instance_stat.open_rate = instance.open_rate
                    instance_stat.click_rate = instance.click_rate
                    instance_stat.recipient_count = instance.recipients.count()
                    instance_stat.click_to_open_rate = instance.click_to_open_rate

                    instance_stat.save()

                    with self.instance_count_lock:
                        self.instance_count += 1

            finally:
                q.task_done()
                if self.instance_bar:
                    with self.pb_lock:
                        self.instance_bar.next()

    def update_campaigns(self, q):
        while True:
            try:
                with self.campaign_queue_lock:
                    campaign = q.get()

                if campaign:
                    campaign.avg_open_rate = campaign.calc_avg_open_rate()
                    campaign.avg_click_rate = campaign.calc_avg_click_rate()
                    campaign.avg_recipient_count = campaign.calc_avg_recipient_count()
                    campaign.avg_click_to_open_rate = campaign.calc_avg_click_to_open_rate()
                    campaign.save()

                    with self.campaign_count_lock:
                        self.campaign_count += 1
            finally:
                q.task_done()
                if self.campaign_bar:
                    with self.pb_lock:
                        self.campaign_bar.next()

    def print_stats(self):
        self.stdout.write(f"""
Completed Collating Stats!

Instances Updated: {self.style.SUCCESS(self.instance_count)}
Campaigns Updated: {self.style.SUCCESS(self.campaign_count)}
        """)


    def handle(self, *args, **options):
        instance_threads = []
        campaign_threads = []

        thread_count = options['thread_count']
        show_progress = options['show_progress']

        self.instance_bar = (ChargingBar('Processing instances...')
            if show_progress
            else None)

        self.campaign_bar = (ChargingBar('Processing campaigns...')
            if show_progress
            else None)

        for _ in range(0, thread_count):
            t = Thread(target=self.update_instances, args=[self.instance_queue], daemon=True).start()
            instance_threads.append(t)

        # Fill up our queues
        for campaign in Campaign.objects.all():
            self.campaign_queue.put(campaign)

            for instance in campaign.instances.all():
                self.instance_queue.put({
                    'campaign': campaign,
                    'instance': instance
                })

        if self.instance_bar:
            self.instance_bar.max = self.instance_queue.qsize()

        self.instance_queue.join()

        for _ in range(0, thread_count):
            t = Thread(target=self.update_campaigns, args=[self.campaign_queue], daemon=True).start()
            campaign_threads.append(t)

        if self.campaign_bar:
            self.campaign_bar.max = self.campaign_queue.qsize()

        self.campaign_queue.join()

        self.print_stats()
