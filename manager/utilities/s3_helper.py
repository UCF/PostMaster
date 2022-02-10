from boto.s3.connection import OrdinaryCallingFormat
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from datetime import datetime
import logging
import os

from django.conf import settings
from django.core.exceptions import PermissionDenied


log = logging.getLogger(__name__)


class AmazonS3Helper:
    """
    Provides basic helper functions for adding, removing and listing files in
    an S3 bucket.

    Uses the bucket and other S3 settings defined in settings_local.py.
    """
    connection = None
    bucket = None
    base_key_path = settings.AMAZON_S3['base_key_path']
    valid_extension_groups = settings.AMAZON_S3['valid_extension_groups']
    valid_protocols = ['//', 'http://', 'https://']

    class AmazonS3HelperException(Exception):
        def __init__(self, value='No additional information'):
            self.parameter = value
            logging.error(': '.join([str(self.__doc__), str(value)]))

        def __str__(self):
            return repr(self.parameter)

    class S3ConnectionError(AmazonS3HelperException):
        """self.connect failed"""
        pass

    class InvalidKeyError(AmazonS3HelperException):
        """A key could not be validated against the S3 bucket"""
        pass

    class KeyDeleteError(AmazonS3HelperException):
        """A key could not be deleted"""
        pass

    class KeyFetchError(AmazonS3HelperException):
        """bucket.get_key failed"""
        pass

    class KeyCreateError(AmazonS3HelperException):
        """A key couldn't be created"""
        pass

    class KeylistFetchError(AmazonS3HelperException):
        """bucket.list failed"""
        pass

    def __init__(self):
        self.connect()

    def connect(self):
        try:
            self.connection = S3Connection(
                settings.AMAZON_S3['aws_access_key_id'],
                settings.AMAZON_S3['aws_secret_access_key'],
                calling_format=OrdinaryCallingFormat()
            )
            self.bucket = self.connection.get_bucket(
                settings.AMAZON_S3['bucket']
            )
        except Exception as e:
            raise AmazonS3Helper.S3ConnectionError(e)

    def get_extensions_by_groupname(self, groupname):
        """
        Returns a list of file extension strings in
        self.valid_extension_groups, or None if the groupname does not exist
        """
        try:
            extensions = self.valid_extension_groups[groupname]
        except KeyError:
            extensions = None

        return extensions

    def get_base_key_path_url(self):
        try:
            keyobj = self.bucket.get_key(self.base_key_path, validate=True)
        except Exception as e:
            raise AmazonS3Helper.InvalidKeyError(e)

        url = keyobj.generate_url(
            0,
            query_auth=False,
            force_http=True
        )

        return url

    def get_file_list(self, file_prefix='', return_extension_groupname=None):
        """
        Returns a list of key objects in self.bucket (optionally prefixed by
        file_prefix arg).

        return_extension_group specifies an extension group of filetypes to
        filter by; e.g. 'images' group returns .png, .jpg, .gif file urls (see
        settings_local.py).  Returns all filetypes by default.
        """
        file_list_unfiltered = None
        file_list = []
        valid_extensions = None

        if not file_prefix:
            file_prefix = ''

        if return_extension_groupname:
            valid_extensions = self.get_extensions_by_groupname(
                return_extension_groupname
            )

        try:
            file_list_unfiltered = self.bucket.list(
                prefix=self.base_key_path + file_prefix
            )
        except Exception as e:
            raise AmazonS3Helper.KeylistFetchError(e)

        if file_list_unfiltered:
            for keyobj in file_list_unfiltered:
                filename, file_extension = os.path.splitext(keyobj.name)

                # Determine if the file extension is valid
                is_valid = False
                if file_extension != '':
                    if not valid_extensions:
                        is_valid = True
                    elif valid_extensions and file_extension in valid_extensions:
                        is_valid = True

                if is_valid:
                    file_list.append(keyobj)

        return file_list

    def upload_file(self, file, unique, file_prefix='', extension_groupname=None):
        """
        Uploads a file to S3 and returns its key (optionally prefixed by
        file_prefix arg).

        Setting unique=True appends a timestamp to the filename to prevent
        overwriting existing files.
        """
        keyobj = None

        if file_prefix is None:
            file_prefix = ''

        if file:
            filename, file_extension = os.path.splitext(file.name)

            if extension_groupname:
                valid_extensions = self.get_extensions_by_groupname(
                    extension_groupname
                )
            if (
                extension_groupname is not None and
                file_extension not in valid_extensions
            ):
                # The user doesn't have permission to upload this type of file
                raise PermissionDenied

            # Create a unique filename (so we don't accidentally overwrite an
            # existing file) if unique==True
            if unique is True:
                filename_unique = filename \
                    + '_'  \
                    + str(datetime.now().strftime('%Y%m%d%H%M%S')) \
                    + file_extension
                filename = filename_unique
            else:
                filename = file.name

            try:
                # Create a new key for the new object and upload it
                keyname = self.base_key_path + file_prefix + filename
                keyobj = Key(self.bucket)
                keyobj.key = keyname
                keyobj.set_contents_from_file(fp=file, policy='public-read')
            except Exception as e:
                raise AmazonS3Helper.KeyCreateError(e)

        return keyobj

    def delete_file(self, keyname):
        """
        Deletes a file by its key name.  Returns remaining key data.
        """
        # Find the existing key in the bucket
        try:
            keyobj = self.bucket.get_key(keyname, validate=True)
        except Exception as e:
            raise AmazonS3Helper.KeyFetchError(e)

        if keyobj is None:
            raise AmazonS3Helper.InvalidKeyError(
                'AmazonS3Helper could not be delete file: file does not exist.'
                ' Keyname: %s',
                keyname
            )
        else:
            try:
                keyobj = self.bucket.delete_key(keyobj)
            except Exception as e:
                raise AmazonS3Helper.KeyDeleteError(e)
        return keyobj
