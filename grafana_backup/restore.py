from grafana_backup.create_org import main as create_org
from grafana_backup.api_checks import main as api_checks
from grafana_backup.create_folder import main as create_folder
from grafana_backup.update_folder_permissions import main as update_folder_permissions
from grafana_backup.create_datasource import main as create_datasource
from grafana_backup.create_dashboard import main as create_dashboard
from grafana_backup.create_alert_channel import main as create_alert_channel
from grafana_backup.create_alert_rule import main as create_alert_rule
from grafana_backup.create_user import main as create_user
from grafana_backup.create_snapshot import main as create_snapshot
from grafana_backup.create_annotation import main as create_annotation
from grafana_backup.create_team import main as create_team
from grafana_backup.create_team_member import main as create_team_member
from grafana_backup.create_library_element import main as create_library_element
from grafana_backup.create_contact_point import main as create_contact_point
from grafana_backup.update_notification_policy import main as update_notification_policy
from grafana_backup.update_notification_template import main as update_notification_template
from grafana_backup.s3_download import main as s3_download
from grafana_backup.azure_storage_download import main as azure_storage_download
from grafana_backup.gcs_download import main as gcs_download
from glob import glob
import sys
import tarfile
import tempfile
import os
import shutil
import fnmatch
import collections


def main(args, settings):
    def open_compressed_backup(compressed_backup):
        try:
            tar = tarfile.open(fileobj=compressed_backup, mode='r:gz')
            return tar
        except Exception as e:
            print(str(e))
            sys.exit(1)

    arg_archive_file = args.get('<archive_file>', None)
    aws_s3_bucket_name = settings.get('AWS_S3_BUCKET_NAME')
    azure_storage_container_name = settings.get('AZURE_STORAGE_CONTAINER_NAME')
    gcs_bucket_name = settings.get('GCS_BUCKET_NAME')

    (status, json_resp, dashboard_uid_support, datasource_uid_support,
     paging_support, contact_point_support) = api_checks(settings)
    settings.update({'CONTACT_POINT_SUPPORT': contact_point_support})

    # Do not continue if API is unavailable or token is not valid
    if not status == 200:
        sys.exit(1)

    # Use tar data stream if S3 bucket name is specified
    if aws_s3_bucket_name:
        print('Download archives from S3:')
        s3_data = s3_download(args, settings)
        tar = open_compressed_backup(s3_data)

    elif azure_storage_container_name:
        print('Download archives from Azure:')
        azure_storage_data = azure_storage_download(args, settings)
        tar = open_compressed_backup(azure_storage_data)

    elif gcs_bucket_name:
        print('Download archives from GCS:')
        gcs_storage_data = gcs_download(args, settings)
        tar = open_compressed_backup(gcs_storage_data)

    else:
        try:
            tarfile.is_tarfile(name=arg_archive_file)
        except IOError as e:
            print(str(e))
            sys.exit(1)
        try:
            tar = tarfile.open(name=arg_archive_file, mode='r:gz')
        except Exception as e:
            print(str(e))
            sys.exit(1)

    # TODO:
    # Shell game magic warning: restore_function keys require the 's'
    # to be removed in order to match file extension names...
    restore_functions = collections.OrderedDict()
    # Folders must be restored before Library-Elements
    restore_functions['folder'] = create_folder
    restore_functions['datasource'] = create_datasource
    # Library-Elements must be restored before dashboards
    restore_functions['library_element'] = create_library_element
    restore_functions['dashboard'] = create_dashboard
    restore_functions['alert_channel'] = create_alert_channel
    restore_functions['organization'] = create_org
    restore_functions['user'] = create_user
    restore_functions['snapshot'] = create_snapshot
    restore_functions['annotation'] = create_annotation
    restore_functions['team'] = create_team
    restore_functions['team_member'] = create_team_member
    restore_functions['folder_permission'] = update_folder_permissions
    restore_functions['alert_rule'] = create_alert_rule
    restore_functions['contact_point'] = create_contact_point
    restore_functions['notification_policy'] = update_notification_policy # Note! Can cause conflict in case policy is provisioned
    restore_functions['notification_template'] = update_notification_template

    if sys.version_info >= (3,):
        with tempfile.TemporaryDirectory() as tmpdir:
            tar.extractall(tmpdir)
            tar.close()
            restore_components(args, settings, restore_functions, tmpdir)
    else:
        tmpdir = tempfile.mkdtemp()
        tar.extractall(tmpdir)
        tar.close()
        restore_components(args, settings, restore_functions, tmpdir)
        try:
            shutil.rmtree(tmpdir)
        except OSError as e:
            print("Error: %s : %s" % (tmpdir, e.strerror))


def restore_components(args, settings, restore_functions, tmpdir):
    arg_components = args.get('--components', [])

    if arg_components:
        arg_components_list = arg_components.replace("-", "_").split(',')

        # Restore only the components that provided via an argument
        # but must also exist in extracted archive
        # NOTICE: ext[:-1] cuts the 's' off in order to match the file extension name to be restored...
        for ext in arg_components_list:
            if sys.version_info >= (3,):
                for file_path in glob('{0}/**/*.{1}'.format(tmpdir, ext[:-1]), recursive=True):
                    print('restoring {0}: {1}'.format(ext, file_path))
                    restore_functions[ext[:-1]](args, settings, file_path)
            else:
                for root, dirnames, filenames in os.walk('{0}'.format(tmpdir)):
                    for filename in fnmatch.filter(filenames, '*.{0}'.format(ext[:-1])):
                        file_path = os.path.join(root, filename)
                        print('restoring {0}: {1}'.format(ext, file_path))
                        restore_functions[ext[:-1]](args, settings, file_path)
    else:
        # Restore every component included in extracted archive
        for ext in restore_functions.keys():
            if sys.version_info >= (3,):
                for file_path in glob('{0}/**/*.{1}'.format(tmpdir, ext), recursive=True):
                    print('restoring {0}: {1}'.format(ext, file_path))
                    restore_functions[ext](args, settings, file_path)
            else:
                for root, dirnames, filenames in os.walk('{0}'.format(tmpdir)):
                    for filename in fnmatch.filter(filenames, '*.{0}'.format(ext)):
                        file_path = os.path.join(root, filename)
                        print('restoring {0}: {1}'.format(ext, file_path))
                        restore_functions[ext](args, settings, file_path)
