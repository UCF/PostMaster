from django.core.management.base import BaseCommand
from manager.models import RecipientGroup, RecipientImporterStatus
from manager.utilities.simple_email_sender import SimpleEmailSender
from django.conf import settings
from django.db import connections, transaction
import logging
import hashlib
import sys

log = logging.getLogger(__name__)

class ImporterException(Exception):
    def __init__(self, importer, e):
        self.importer = importer
        self.e = e

    def __str__(self):
        return str(self.e)

    def __unicode__(self):
        return str(self.e)

class ImporterHistoryException(Exception):
    def __init__(self, importer, e):
        self.importer = importer
        self.e = e

    def __str__(self):
        return str(self.e)

    def __unicode__(self):
        return str(self.e)

class Command(BaseCommand):
    '''
        Runs a specified recipient importer.
    '''

    # Recipient importers that are available.
    importers = (
        'GMUCFImporter',
        'AllStudentsImporter',
        'AllStaffImporter'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'importer',
            type=str,
            help="The importer to run"
        )


    def handle(self, *args, **kwargs):
        self.importer = kwargs['importer']

        if self.importer:
            cls = eval(self.importer)
            inst = cls()
            inst.setup()
            inst.do_import()

            try:
                results = inst.get_results()
                self.stdout.write(self.style.SUCCESS(results))
            except ImporterException as e:
                msg = f"""
The {e.importer} failed to complete with the following error:

{str(e)}
                """

                sender = SimpleEmailSender(
                    'PostMaster Recipient Importer Failed',
                    settings.DEBUG_FROM_EMAIL,
                    settings.DEBUG_FROM_FRIENDLY,
                    msg,
                    settings.DEBUG_RECIPIENTS
                )

            if settings.DO_IMPORT_AUDIT:
                try:
                    checks = inst.check_history()
                    if checks != "":
                        self.stdout.write(self.style.WARNING(checks))
                except ImporterHistoryException as e:
                    msg = f"""
    The history audit for {e.importer} failed with the following error:

    {str(e)}
                    """

                    sender = SimpleEmailSender(
                        'PostMaster Importer Audit Failure',
                        settings.DEBUG_FROM_EMAIL,
                        settings.DEBUG_FROM_FRIENDLY,
                        msg,
                        settings.DEBUG_RECIPIENTS
                    )
                    sender.send()

        else:
            error_msg = """
You must specify an importer to run. Example command:
python manage.py recipient-importer <importer-name>
Available importers are:
            """
            self.stdout.write(self.style.ERROR(error_msg))
            sys.exit(1)

class Importer(object):
    '''
        Base importer class. Any functionality that should be
        shared between all importers should be implemented
        or stubbed here.
    '''
    id           = None
    name         = None
    display_name = None

    def __init__(self, *args, **kwargs):
        self.current_record_count = 0
        self.rds_record_count = 0
        self.status_record = RecipientImporterStatus(import_name=self.name)

    def setup(self):
        pass

    def do_import(self):
        raise NotImplemented()

    def get_results(self):
        perc_change = round((self.rds_record_count / self.current_record_count * 100) - 100, 4)

        message = f"""
Record Count Prior to Import:   {self.current_record_count}
Record Count in RDS Wharehouse: {self.rds_record_count}

Percentage Change: {perc_change}%

        """

        return message

    def check_history(self):
        num_records = settings.NUM_IMPORTS_TO_CHECK

        status_records = RecipientImporterStatus.objects.filter(import_name=self.name).order_by('-import_date')[0:num_records]
        if status_records.count() < num_records:
            return f"""
Not enough imports have occurred to perform data checking.
Data checking will be done after {num_records} imports.
"""

        num_hashes = len(list(set(status_records.values_list('data_hash'))))

        if num_hashes == 1:
            message = f"The data for the {self.display_name} has not changed in the last {num_records} imports. Please, ensure the data is being properly written to the rds_wharehouse tables."
            raise ImporterHistoryException(self.display_name, message)

        return ""

class GMUCFImporter(Importer):
    '''
        Importer for the Good Morning UCF email list.
    '''
    name         = 'gmucfimporter'
    display_name = 'Good Morning UCF Importer'

    gmucf_recipient_group_name = 'Good Morning UCF'

    def setup(self):

        # Check to see if the rds_wharehouse database is configured
        if 'rds_wharehouse' not in settings.DATABASES:
            raise ImporterException(self.display_name, 'The rds_wharehouse database is not configured.')

        self.MINIMUM_IMPORT_EMAIL_COUNT = settings.MINIMUM_IMPORT_EMAIL_COUNT

        self.postmaster_db_name     = settings.DATABASES['default']['NAME']
        self.rds_wharehouse_db_name = settings.DATABASES['rds_wharehouse']['NAME']
        self.postmaster_cursor = connections['default'].cursor()

        # Check to see if the Good Morning UCF Group exists
        try:
            self.gmucf_recipient_group = RecipientGroup.objects.get(name=self.gmucf_recipient_group_name)
            self.current_record_count = self.gmucf_recipient_group.recipients.count()
        except RecipientGroup.DoesNotExist:
            raise ImporterException(self.display_name, 'The Good Morning UCF recipient group doesn\'t exist. Please create it.')

        # Make sure there is an index on the SMCA_GMUCF.email column
        self.postmaster_cursor.execute('SHOW INDEX FROM %s.SMCA_GMUCF WHERE Key_name=\'email\'' % self.rds_wharehouse_db_name)
        results = self.postmaster_cursor.fetchall()
        log.info('RDS Wharehouse index result count: %d' % len(results))
        if len(results) == 0:
            self.postmaster_cursor.execute('ALTER TABLE %s.SMCA_GMUCF ADD INDEX `email` (`email`)' % self.rds_wharehouse_db_name)
            transaction.commit()

        # Make sure there is an index on the manager_recipient.email_address column
        self.postmaster_cursor.execute('SHOW INDEX FROM %s.manager_recipient WHERE Key_name=\'email_address\'' % self.postmaster_db_name)
        results = self.postmaster_cursor.fetchall()
        log.info('Postmaster index result count: %d' % len(results))
        if len(results) == 0:
            self.postmaster_cursor.execute('ALTER TABLE %s.manager_recipient ADD INDEX `email_address` (`email_address`)' % self.postmaster_db_name)
            transaction.commit()

        # Make sure there is a significant number of emails in the RDS warehouse before proceeding
        self.postmaster_cursor.execute('SELECT COUNT(email) FROM %s.SMCA_GMUCF' % self.rds_wharehouse_db_name)
        (rds_count,) = self.postmaster_cursor.fetchone()

        self.status_record.row_count = rds_count
        self.rds_record_count = rds_count

        log.info('RDS Warehouse row count: %d' % rds_count)
        if rds_count < self.MINIMUM_IMPORT_EMAIL_COUNT:
            log.error('Import failed because of the limited number of entries from rds_wharehouse database (count %d < %d).' % (rds_count, self.MINIMUM_IMPORT_EMAIL_COUNT))
            raise ImporterException(self.display_name, 'Import failed because of the limited number of entries from rds_wharehouse database (count %d < %d).' % (rds_count, self.MINIMUM_IMPORT_EMAIL_COUNT))

    def do_import(self):
        '''
            1. Remove any recipients from the Good Morning UCF group who are no longer
                in the RDS wharehouse data.
            2. Create any recipients who are in the the RDS wharehouse data but not
                in the recipients table.
            3. Update any Recipient attributes
            4. Add any newly created recipients to the Good Morning UCF group
        '''

        self.postmaster_cursor.execute('''
            UPDATE
                %s.SMCA_GMUCF
            SET
                %s.SMCA_GMUCF.email = LOWER(%s.SMCA_GMUCF.email)
            ''' % (
                self.rds_wharehouse_db_name,
                self.rds_wharehouse_db_name,
                self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            DELETE FROM
                %s.manager_recipientgroup_recipients
            WHERE
                recipientgroup_id = %d  AND
                recipient_id IN (
                    SELECT
                        recipient.id
                    FROM
                        %s.manager_recipient recipient
                    LEFT JOIN
                        %s.SMCA_GMUCF ikm
                    ON
                        recipient.email_address = ikm.email
                    WHERE
                        ikm.email IS NULL
                )''' % (
            self.postmaster_db_name,
            self.gmucf_recipient_group.id,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            INSERT IGNORE INTO
                %s.manager_recipient(email_address)
            (
                SELECT
                    email
                FROM
                    %s.SMCA_GMUCF
            )
        ''' % (
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            INSERT INTO
                %s.manager_recipientattribute(recipient_id, name, value)
            (
                SELECT
                    recipient.id AS recipient_id,
                    'Preferred Name' AS name,
                    gmucf.first_name AS value
                FROM
                    %s.manager_recipient recipient
                JOIN
                    %s.SMCA_GMUCF AS gmucf
                ON
                    recipient.email_address = gmucf.email
            )
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        ''' % (
            self.postmaster_db_name,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            INSERT INTO
                %s.manager_recipientgroup_recipients(recipientgroup_id, recipient_id)
            (
                SELECT DISTINCT
                    %d AS recipientgroup_id,
                    recipient.id
                FROM
                    %s.manager_recipient recipient
                JOIN
                    %s.SMCA_GMUCF ikm
                ON
                    ikm.email = recipient.email_address
                LEFT JOIN
                    %s.manager_recipientgroup_recipients group_recipient
                ON
                    group_recipient.recipient_id = recipient.id AND
                    group_recipient.recipientgroup_id = %d
                WHERE
                    group_recipient.recipientgroup_id IS NULL
            )
        ''' % (
            self.postmaster_db_name,
            self.gmucf_recipient_group.id,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name,
            self.postmaster_db_name,
            self.gmucf_recipient_group.id
        ))
        transaction.commit()

        # Let's get the data to hash
        self.postmaster_cursor.execute(f'''
            SELECT
                *
            FROM
                {self.rds_wharehouse_db_name}.SMCA_GMUCF
        ''')

        results = self.postmaster_cursor.fetchall()
        results_hash = hashlib.sha256(str(results).encode())

        self.status_record.data_hash = results_hash.hexdigest()

        try:
            self.status_record.save()
        except:
            pass

class AllStudentsImporter(Importer):
    '''
        Importer for the All Students - Updated Daily IKM Data email list.
    '''
    name         = 'allstudentsimporter'
    display_name = 'All Students Importer'

    all_students_recipient_group_name = 'All Students - Updated Daily IKM Data'

    def setup(self):

        # Check to see if the rds_wharehouse database is configured
        if 'rds_wharehouse' not in settings.DATABASES:
            raise ImporterException(self.display_name, 'The rds_wharehouse database is not configured.')

        self.MINIMUM_IMPORT_EMAIL_COUNT = settings.MINIMUM_IMPORT_EMAIL_COUNT

        self.postmaster_db_name     = settings.DATABASES['default']['NAME']
        self.rds_wharehouse_db_name = settings.DATABASES['rds_wharehouse']['NAME']
        self.postmaster_cursor = connections['default'].cursor()

        self.status_record = RecipientImporterStatus(import_name=self.name)

        # Check to see if the 'All Students - Updated Daily IKM Data' Group exists
        try:
            self.all_students_recipient_group_name = RecipientGroup.objects.get(name=self.all_students_recipient_group_name)
            self.current_record_count = self.all_students_recipient_group_name.recipients.count()
        except RecipientGroup.DoesNotExist:
            raise ImporterException(self.display_name, 'The All Students - Updated Daily IKM Data recipient group doesn\'t exist. Please create it.')

        # Make sure there is an index on the ENRL_SDNT_LIST.email column
        self.postmaster_cursor.execute('SHOW INDEX FROM %s.ENRL_STDNT_LIST WHERE Key_name=\'email\'' % self.rds_wharehouse_db_name)
        results = self.postmaster_cursor.fetchall()
        log.info('RDS Wharehouse index result count: %d' % len(results))
        if len(results) == 0:
            self.postmaster_cursor.execute('ALTER TABLE %s.ENRL_STDNT_LIST ADD INDEX `email` (`email`)' % self.rds_wharehouse_db_name)
            transaction.commit()

        # Make sure there is an index on the manager_recipient.email_address column
        self.postmaster_cursor.execute('SHOW INDEX FROM %s.manager_recipient WHERE Key_name=\'email_address\'' % self.postmaster_db_name)
        results = self.postmaster_cursor.fetchall()
        log.info('Postmaster index result count: %d' % len(results))
        if len(results) == 0:
            self.postmaster_cursor.execute('ALTER TABLE %s.manager_recipient ADD INDEX `email_address` (`email_address`)' % self.postmaster_db_name)
            transaction.commit()

        # Make sure there is a significant number of emails in the RDS warehouse before proceeding
        self.postmaster_cursor.execute('SELECT COUNT(email) FROM %s.ENRL_STDNT_LIST' % self.rds_wharehouse_db_name)
        (rds_count,) = self.postmaster_cursor.fetchone()

        self.status_record.row_count = rds_count
        self.rds_record_count = rds_count

        log.info('RDS Warehouse row count: %d' % rds_count)
        if rds_count < self.MINIMUM_IMPORT_EMAIL_COUNT:
            log.error('Import failed because of the limited number of entries from rds_wharehouse database (count %d < %d).' % (rds_count, self.MINIMUM_IMPORT_EMAIL_COUNT))
            raise ImporterException(self.display_name, 'Import failed because of the limited number of entries from rds_wharehouse database (count %d < %d).' % (rds_count, self.MINIMUM_IMPORT_EMAIL_COUNT))

    def do_import(self):
        '''
            1. Remove any recipients from the All Students - Updated Daily IKM Data
                group who are no longer in the RDS wharehouse data.
            2. Create any recipients who are in the the RDS wharehouse data but not
                in the recipients table.
            3. Update any Recipient attributes
            4. Add any newly created recipients to the All Students - Updated Daily
                IKM Data group
        '''

        self.postmaster_cursor.execute('''
            UPDATE
                %s.ENRL_STDNT_LIST
            SET
                %s.ENRL_STDNT_LIST.email = LOWER(%s.ENRL_STDNT_LIST.email)
            ''' % (
                self.rds_wharehouse_db_name,
                self.rds_wharehouse_db_name,
                self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            DELETE FROM
                %s.manager_recipientgroup_recipients
            WHERE
                recipientgroup_id = %d  AND
                recipient_id IN (
                    SELECT
                        recipient.id
                    FROM
                        %s.manager_recipient recipient
                    LEFT JOIN
                        %s.ENRL_STDNT_LIST ikm
                    ON
                        recipient.email_address = ikm.email
                    WHERE
                        ikm.email IS NULL
                )''' % (
            self.postmaster_db_name,
            self.all_students_recipient_group_name.id,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            INSERT IGNORE INTO
                %s.manager_recipient(email_address)
            (
                SELECT
                    email
                FROM
                    %s.ENRL_STDNT_LIST
            )
        ''' % (
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            INSERT INTO
                %s.manager_recipientattribute(recipient_id, name, value)
            (
                SELECT
                    recipient.id AS recipient_id,
                    'Preferred Name' AS name,
                    enrl_stdnt.first_name AS value
                FROM
                    %s.manager_recipient recipient
                JOIN
                    %s.ENRL_STDNT_LIST AS enrl_stdnt
                ON
                    recipient.email_address = enrl_stdnt.email
            )
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        ''' % (
            self.postmaster_db_name,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            INSERT INTO
                %s.manager_recipientgroup_recipients(recipientgroup_id, recipient_id)
            (
                SELECT DISTINCT
                    %d AS recipientgroup_id,
                    recipient.id
                FROM
                    %s.manager_recipient recipient
                JOIN
                    %s.ENRL_STDNT_LIST ikm
                ON
                    ikm.email = recipient.email_address
                LEFT JOIN
                    %s.manager_recipientgroup_recipients group_recipient
                ON
                    group_recipient.recipient_id = recipient.id AND
                    group_recipient.recipientgroup_id = %d
                WHERE
                    group_recipient.recipientgroup_id IS NULL
            )
        ''' % (
            self.postmaster_db_name,
            self.all_students_recipient_group_name.id,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name,
            self.postmaster_db_name,
            self.all_students_recipient_group_name.id
        ))
        transaction.commit()

        # Let's get a count
        self.postmaster_cursor.execute(f'''
            SELECT
                *
            FROM
                {self.rds_wharehouse_db_name}.ENRL_STDNT_LIST
        ''')

        results = self.postmaster_cursor.fetchall()
        results_hash = hashlib.sha256(str(results).encode())

        self.status_record.data_hash = results_hash.hexdigest()

        try:
            self.status_record.save()
        except:
            pass

class AllStaffImporter(Importer):
    '''
        Importer for the All Faculty-Staff - Updated Daily IKM Data email list.
    '''
    name         = 'allstaffimporter'
    display_name = 'All Staff Importer'

    all_staff_recipient_group_name = 'All Faculty-Staff - Updated Daily IKM Data'

    def setup(self):

        # Check to see if the rds_wharehouse database is configured
        if 'rds_wharehouse' not in settings.DATABASES:
            raise ImporterException(self.display_name, 'The rds_wharehouse database is not configured.')

        self.MINIMUM_IMPORT_EMAIL_COUNT = settings.MINIMUM_IMPORT_EMAIL_COUNT

        self.postmaster_db_name     = settings.DATABASES['default']['NAME']
        self.rds_wharehouse_db_name = settings.DATABASES['rds_wharehouse']['NAME']
        self.postmaster_cursor = connections['default'].cursor()

        self.status_record = RecipientImporterStatus(import_name=self.name)

        # Check to see if the 'All Faculty-Staff - Updated Daily IKM Data' Group exists
        try:
            self.all_staff_recipient_group_name = RecipientGroup.objects.get(name=self.all_staff_recipient_group_name)
            self.current_record_count = self.all_staff_recipient_group_name.recipients.count()
        except RecipientGroup.DoesNotExist:
            raise ImporterException(self.display_name, 'The All Faculty-Staff - Updated Daily IKM Data recipient group doesn\'t exist. Please create it.')

        # Make sure there is an index on the ACTV_EMPL_LIST.email column
        self.postmaster_cursor.execute('SHOW INDEX FROM %s.ACTV_EMPL_LIST WHERE Key_name=\'email\'' % self.rds_wharehouse_db_name)
        results = self.postmaster_cursor.fetchall()
        log.info('RDS Wharehouse index result count: %d' % len(results))
        if len(results) == 0:
            self.postmaster_cursor.execute('ALTER TABLE %s.ACTV_EMPL_LIST ADD INDEX `email` (`email`)' % self.rds_wharehouse_db_name)
            transaction.commit()

        # Make sure there is an index on the manager_recipient.email_address column
        self.postmaster_cursor.execute('SHOW INDEX FROM %s.manager_recipient WHERE Key_name=\'email_address\'' % self.postmaster_db_name)
        results = self.postmaster_cursor.fetchall()
        log.info('Postmaster index result count: %d' % len(results))
        if len(results) == 0:
            self.postmaster_cursor.execute('ALTER TABLE %s.manager_recipient ADD INDEX `email_address` (`email_address`)' % self.postmaster_db_name)
            transaction.commit()

        # Make sure there is a significant number of emails in the RDS warehouse before proceeding
        self.postmaster_cursor.execute('SELECT COUNT(email) FROM %s.ACTV_EMPL_LIST' % self.rds_wharehouse_db_name)
        (rds_count,) = self.postmaster_cursor.fetchone()

        self.status_record.row_count = rds_count
        self.rds_record_count = rds_count

        log.info('RDS Warehouse row count: %d' % rds_count)
        if rds_count < self.MINIMUM_IMPORT_EMAIL_COUNT:
            log.error('Import failed because of the limited number of entries from rds_wharehouse database (count %d < %d).' % (rds_count, self.MINIMUM_IMPORT_EMAIL_COUNT))
            raise ImporterException(self.display_name, 'Import failed because of the limited number of entries from rds_wharehouse database (count %d < %d).' % (rds_count, self.MINIMUM_IMPORT_EMAIL_COUNT))

    def do_import(self):
        '''
            1. Remove any recipients from the All Faculty-Staff - Updated Daily IKM Data
                group who are no longer in the RDS wharehouse data.
            2. Create any recipients who are in the the RDS wharehouse data but not
                in the recipients table.
            3. Update any Recipient attributes
            4. Add any newly created recipients to the All Faculty-Staff - Updated Daily
                IKM Data group
        '''

        self.postmaster_cursor.execute('''
            UPDATE
                %s.ACTV_EMPL_LIST
            SET
                %s.ACTV_EMPL_LIST.email = LOWER(%s.ACTV_EMPL_LIST.email)
            ''' % (
                self.rds_wharehouse_db_name,
                self.rds_wharehouse_db_name,
                self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            DELETE FROM
                %s.manager_recipientgroup_recipients
            WHERE
                recipientgroup_id = %d  AND
                recipient_id IN (
                    SELECT
                        recipient.id
                    FROM
                        %s.manager_recipient recipient
                    LEFT JOIN
                        %s.ACTV_EMPL_LIST ikm
                    ON
                        recipient.email_address = ikm.email
                    WHERE
                        ikm.email IS NULL
                )''' % (
            self.postmaster_db_name,
            self.all_staff_recipient_group_name.id,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            INSERT IGNORE INTO
                %s.manager_recipient(email_address)
            (
                SELECT
                    email
                FROM
                    %s.ACTV_EMPL_LIST
            )
        ''' % (
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()


        self.postmaster_cursor.execute('''
            INSERT INTO
                %s.manager_recipientattribute(recipient_id, name, value)
            (
                SELECT
                    recipient.id AS recipient_id,
                    'Preferred Name' AS name,
                    allempl.first_name AS value
                FROM
                    %s.manager_recipient recipient
                JOIN
                    %s.ACTV_EMPL_LIST AS allempl
                ON
                    recipient.email_address = allempl.email
            )
            ON DUPLICATE KEY UPDATE value = VALUES(value)
        ''' % (
            self.postmaster_db_name,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name
        ))
        transaction.commit()

        self.postmaster_cursor.execute('''
            INSERT INTO
                %s.manager_recipientgroup_recipients(recipientgroup_id, recipient_id)
            (
                SELECT DISTINCT
                    %d AS recipientgroup_id,
                    recipient.id
                FROM
                    %s.manager_recipient recipient
                JOIN
                    %s.ACTV_EMPL_LIST ikm
                ON
                    ikm.email = recipient.email_address
                LEFT JOIN
                    %s.manager_recipientgroup_recipients group_recipient
                ON
                    group_recipient.recipient_id = recipient.id AND
                    group_recipient.recipientgroup_id = %d
                WHERE
                    group_recipient.recipientgroup_id IS NULL
            )
        ''' % (
            self.postmaster_db_name,
            self.all_staff_recipient_group_name.id,
            self.postmaster_db_name,
            self.rds_wharehouse_db_name,
            self.postmaster_db_name,
            self.all_staff_recipient_group_name.id
        ))
        transaction.commit()

        # Let's get a count
        self.postmaster_cursor.execute(f'''
            SELECT
                *
            FROM
                {self.rds_wharehouse_db_name}.ACTV_EMPL_LIST
        ''')

        results = self.postmaster_cursor.fetchall()
        results_hash = hashlib.sha256(str(results).encode())

        self.status_record.data_hash = results_hash.hexdigest()

        try:
            self.status_record.save()
        except:
            pass
