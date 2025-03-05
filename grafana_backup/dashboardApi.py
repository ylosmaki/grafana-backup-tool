import re
import json
import requests
import sys
from grafana_backup.commons import log_response, to_python2_and_3_compatible_string
from packaging import version


def health_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/health'.format(grafana_url)
    print("\n[Pre-Check] grafana health check: {0}".format(url))
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def auth_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/auth/keys'.format(grafana_url)
    print("\n[Pre-Check] grafana auth check: {0}".format(url))
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def uid_feature_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    # Get first dashboard on first page
    print("\n[Pre-Check] grafana uid feature check: calling 'search_dashboard'")
    (status, content) = search_dashboard(1, 1, grafana_url,
                                         http_get_headers, verify_ssl, client_cert, debug)
    if status == 200 and len(content):
        if 'uid' in content[0]:
            dashboard_uid_support = True
        else:
            dashboard_uid_support = False
    else:
        if len(content):
            dashboard_uid_support = "get dashboards failed, status: {0}, msg: {1}".format(
                status, content)
        else:
            # No dashboards exist, disable uid feature
            dashboard_uid_support = False
    # Get first datasource
    print("\n[Pre-Check] grafana uid feature check: calling 'search_datasource'")
    (status, content) = search_datasource(grafana_url,
                                          http_get_headers, verify_ssl, client_cert, debug)
    if status == 200 and len(content):
        if 'uid' in content[0]:
            datasource_uid_support = True
        else:
            datasource_uid_support = False
    else:
        if len(content):
            datasource_uid_support = "get datasources failed, status: {0}, msg: {1}".format(
                status, content)
        else:
            # No datasources exist, disable uid feature
            datasource_uid_support = False

    return dashboard_uid_support, datasource_uid_support


def paging_feature_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    print("\n[Pre-Check] grafana paging_feature_check: calling 'search_dashboard'")

    def get_first_dashboard_by_page(page):
        (status, content) = search_dashboard(page, 1, grafana_url,
                                             http_get_headers, verify_ssl, client_cert, debug)
        if status == 200 and len(content):
            if sys.version_info[0] > 2:
                content[0] = {k: to_python2_and_3_compatible_string(
                    v) for k, v in content[0].items()}
                dashboard_values = sorted(
                    content[0].items(), key=lambda kv: str(kv[1]))
            else:
                content[0] = {k: to_python2_and_3_compatible_string(
                    unicode(v)) for k, v in content[0].iteritems()}
                dashboard_values = sorted(
                    content[0].iteritems(), key=lambda kv: str(kv[1]))
            return True, dashboard_values
        else:
            if len(content):
                return False, "get dashboards failed, status: {0}, msg: {1}".format(status, content)
            else:
                # No dashboards exist, disable paging feature
                return False, False

    # Get first dashboard on first page
    (status, content) = get_first_dashboard_by_page(1)
    if status is False and content is False:
        return False  # Paging feature not supported
    elif status is True:
        dashboard_one_values = content
    else:
        return content  # Fail Message

    # Get second dashboard on second page
    (status, content) = get_first_dashboard_by_page(2)
    if status is False and content is False:
        return False  # Paging feature not supported
    elif status is True:
        dashboard_two_values = content
    else:
        return content  # Fail Message

    # Compare both pages
    return dashboard_one_values != dashboard_two_values


def contact_point_check(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    print("\n[Pre-Check] grafana contact_point api check")
    (status, content) = search_contact_points(
        grafana_url, http_get_headers, verify_ssl, client_cert, debug)
    if status == 200:
        return True
    else:
        return False


def search_dashboard(page, limit, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/search/?type=dash-db&limit={1}&page={2}'.format(
        grafana_url, limit, page)
    print("search dashboard in grafana: {0}".format(url))
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def get_dashboard(board_uri, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/dashboards/{1}'.format(grafana_url, board_uri)
    print("query dashboard uri: {0}".format(url))
    (status_code, content) = send_grafana_get(
        url, http_get_headers, verify_ssl, client_cert, debug)
    return (status_code, content)


def search_library_elements(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/library-elements?perPage=5000'.format(grafana_url)
    print("search library-elements in grafana: {0}".format(url))
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def create_library_element(library_element, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/library-elements'.format(grafana_url)
    return send_grafana_post(url, library_element, http_post_headers, verify_ssl, client_cert, debug)


def delete_library_element(id_, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/library-elements/{1}'.format(grafana_url, id_), http_get_headers,
                               verify_ssl, client_cert)


def search_teams(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/teams/search?perPage=5000'.format(grafana_url)
    print("search teams in grafana: {0}".format(url))
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def create_team(team, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/teams'.format(grafana_url)
    return send_grafana_post(url, team, http_post_headers, verify_ssl, client_cert, debug)


def delete_team(id_, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/teams/{1}'.format(grafana_url, id_), http_get_headers,
                               verify_ssl, client_cert)


def search_team_members(team_id, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/teams/{1}/members'.format(grafana_url, team_id)
    print("search team members in grafana: {0}".format(url))
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def create_team_member(user, team_id, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/teams/{1}/members'.format(grafana_url, team_id)
    return send_grafana_post(url, user, http_post_headers, verify_ssl, client_cert, debug)


def delete_team_member(user_id, team_id, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/teams/{1}/members/{2}'.format(grafana_url, team_id, user_id), http_get_headers,
                               verify_ssl, client_cert)


def search_annotations(grafana_url, ts_from, ts_to, http_get_headers, verify_ssl, client_cert, debug):
    # there are two types of annotations
    # annotation: are user created, custom ones and can be managed via the api
    # alert: are created by Grafana itself, can NOT be managed by the api
    url = '{0}/api/annotations?type=annotation&limit=5000&from={1}&to={2}'.format(
        grafana_url, ts_from, ts_to)
    print("search annotations in grafana: {0}".format(url))
    (status_code, content) = send_grafana_get(
        url, http_get_headers, verify_ssl, client_cert, debug)
    return (status_code, content)


def create_annotation(annotation, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/annotations'.format(grafana_url)
    return send_grafana_post(url, annotation, http_post_headers, verify_ssl, client_cert, debug)


def delete_annotation(id_, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/annotations/{1}'.format(grafana_url, id_), http_get_headers, verify_ssl,
                               client_cert, debug)


def search_alert_rules(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/v1/provisioning/alert-rules'.format(grafana_url)
    print("search alert rules in grafana: {0}".format(url))
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def get_alert_rule(uid, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/v1/provisioning/alert-rules/{1}'.format(grafana_url, uid)
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def create_alert_rule(alert, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/v1/provisioning/alert-rules'.format(grafana_url)
    return send_grafana_post(url, alert, http_get_headers, verify_ssl, client_cert, debug)


def delete_alert_rule(uid, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/v1/provisioning/alert-rules/{1}'.format(grafana_url, uid)
    return send_grafana_delete(url, http_get_headers, verify_ssl, client_cert, debug)


def update_alert_rule(uid, alert, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/v1/provisioning/alert-rules/{1}'.format(grafana_url, uid)
    return send_grafana_put(url, alert, http_get_headers, verify_ssl, client_cert, debug)


def search_alert_channels(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/alert-notifications'.format(grafana_url)
    print("search alert channels in grafana: {0}".format(url))
    return send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug)


def create_alert_channel(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/alert-notifications'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert, debug)


def delete_alert_channel_by_uid(uid, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/alert-notifications/uid/{1}'.format(grafana_url, uid), http_post_headers,
                               verify_ssl, client_cert, debug)


def delete_alert_channel_by_id(id_, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/alert-notifications/{1}'.format(grafana_url, id_), http_post_headers,
                               verify_ssl, client_cert, debug)


def search_alerts(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/alerts'.format(grafana_url)
    print("search alerts in grafana: {0}".format(url))
    (status_code, content) = send_grafana_get(
        url, http_get_headers, verify_ssl, client_cert, debug)
    return (status_code, content)


def pause_alert(id_, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/alerts/{1}/pause'.format(grafana_url, id_)
    payload = '{ "paused": true }'
    (status_code, content) = send_grafana_post(
        url, payload, http_post_headers, verify_ssl, client_cert, debug)
    return (status_code, content)


def unpause_alert(id_, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/alerts/{1}/pause'.format(grafana_url, id_)
    payload = '{ "paused": false }'
    (status_code, content) = send_grafana_post(
        url, payload, http_post_headers, verify_ssl, client_cert, debug)
    return (status_code, content)


def delete_folder(uid, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/folders/{1}'.format(grafana_url, uid), http_post_headers, verify_ssl,
                               client_cert, debug)


def delete_snapshot(key, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/snapshots/{1}'.format(grafana_url, key), http_post_headers, verify_ssl,
                               client_cert, debug)


def delete_dashboard_by_uid(uid, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/dashboards/uid/{1}'.format(grafana_url, uid), http_post_headers, verify_ssl,
                               client_cert, debug)


def delete_dashboard_by_slug(slug, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/dashboards/db/{1}'.format(grafana_url, slug), http_post_headers, verify_ssl,
                               client_cert, debug)


def create_dashboard(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/dashboards/db'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert, debug)


def search_datasource(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    print("search datasources in grafana:")
    return send_grafana_get('{0}/api/datasources'.format(grafana_url), http_get_headers, verify_ssl, client_cert, debug)


def search_snapshot(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    print("search snapshots in grafana:")
    return send_grafana_get('{0}/api/dashboard/snapshots'.format(grafana_url), http_get_headers, verify_ssl, client_cert, debug)


def get_snapshot(key, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    url = '{0}/api/snapshots/{1}'.format(grafana_url, key)
    (status_code, content) = send_grafana_get(
        url, http_get_headers, verify_ssl, client_cert, debug)
    return (status_code, content)


def create_snapshot(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/snapshots'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert, debug)


def create_datasource(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/datasources'.format(grafana_url), payload, http_post_headers, verify_ssl,
                             client_cert, debug)


def delete_datasource_by_uid(uid, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/datasources/uid/{1}'.format(grafana_url, uid), http_post_headers, verify_ssl,
                               client_cert, debug)


def delete_datasource_by_id(id_, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_delete('{0}/api/datasources/{1}'.format(grafana_url, id_), http_post_headers, verify_ssl,
                               client_cert, debug)


def search_folders(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    print("search folder in grafana:")
    return send_grafana_get('{0}/api/search/?type=dash-folder'.format(grafana_url), http_get_headers, verify_ssl,
                            client_cert, debug)


def get_folder(uid, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    (status_code, content) = send_grafana_get('{0}/api/folders/{1}'.format(grafana_url, uid), http_get_headers,
                                              verify_ssl, client_cert, debug)
    print("query folder:{0}, status:{1}".format(uid, status_code))
    return (status_code, content)


def get_folder_permissions(uid, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    (status_code, content) = send_grafana_get('{0}/api/folders/{1}/permissions'.format(grafana_url, uid), http_get_headers,
                                              verify_ssl, client_cert, debug)
    print("query folder permissions:{0}, status:{1}".format(uid, status_code))
    return (status_code, content)


def update_folder_permissions(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    items = json.dumps({'items': payload})
    return send_grafana_post('{0}/api/folders/{1}/permissions'.format(grafana_url, payload[0]['uid']), items, http_post_headers, verify_ssl, client_cert,
                             debug)


def get_folder_id(dashboard, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    folder_uid = ""
    try:
        folder_uid = dashboard['meta']['folderUid']
    except (KeyError):
        matches = re.search('dashboards\/f\/(.*)\/.*',
                            dashboard['meta']['folderUrl'])
        if matches is not None:
            folder_uid = matches.group(1)
        else:
            folder_uid = '0'

    if (folder_uid != ""):
        print("debug: quering with uid {}".format(folder_uid))
        response = get_folder(folder_uid, grafana_url,
                              http_post_headers, verify_ssl, client_cert, debug)
        if isinstance(response[1], dict):
            folder_data = response[1]
        else:
            folder_data = json.loads(response[1])

        try:
            return folder_data['id']
        except (KeyError):
            return 0
    else:
        return 0


def create_folder(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/folders'.format(grafana_url), payload, http_post_headers, verify_ssl, client_cert,
                             debug)


def get_dashboard_versions(dashboard_id, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    (status_code, content) = send_grafana_get('{0}/api/dashboards/id/{1}/versions'.format(grafana_url, dashboard_id), http_get_headers,
                                              verify_ssl, client_cert, debug)
    print("query dashboard versions: {0}, status: {1}".format(
        dashboard_id, status_code))
    return (status_code, content)


def get_version(dashboard_id, version_number, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    (status_code, content) = send_grafana_get('{0}/api/dashboards/id/{1}/versions/{2}'.format(grafana_url, dashboard_id, version_number), http_get_headers,
                                              verify_ssl, client_cert, debug)
    print("query dashboard {0} version {1}, status: {2}".format(
        dashboard_id, version_number, status_code))
    return (status_code, content)


def search_orgs(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    return send_grafana_get('{0}/api/orgs'.format(grafana_url), http_get_headers, verify_ssl,
                            client_cert, debug)


def get_org(id, grafana_url, http_get_headers, verify_ssl=False, client_cert=None, debug=True):
    return send_grafana_get('{0}/api/orgs/{1}'.format(grafana_url, id),
                            http_get_headers, verify_ssl, client_cert, debug)


def create_org(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/orgs'.format(grafana_url), payload, http_post_headers, verify_ssl, client_cert,
                             debug)


def update_org(id, payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_put('{0}/api/orgs/{1}'.format(grafana_url, id), payload, http_post_headers, verify_ssl, client_cert,
                            debug)


def search_users(page, limit, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    return send_grafana_get('{0}/api/users?perpage={1}&page={2}'.format(grafana_url, limit, page),
                            http_get_headers, verify_ssl, client_cert, debug)


def get_users(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    return send_grafana_get('{0}/api/org/users'.format(grafana_url), http_get_headers, verify_ssl, client_cert, debug)


def set_user_role(user_id, role, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    json_payload = json.dumps({'role': role})
    url = '{0}/api/org/users/{1}'.format(grafana_url, user_id)
    r = requests.patch(url, headers=http_post_headers,
                       data=json_payload, verify=verify_ssl, cert=client_cert)
    return (r.status_code, r.json())


def get_user(id, grafana_url, http_get_headers, verify_ssl=False, client_cert=None, debug=True):
    return send_grafana_get('{0}/api/users/{1}'.format(grafana_url, id),
                            http_get_headers, verify_ssl, client_cert, debug)


def get_user_by_email_or_username(email, grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    return send_grafana_get('{0}/api/users/lookup?loginOrEmail={1}'.format(grafana_url, email), http_get_headers,
                            verify_ssl, client_cert, debug)


def get_user_org(id, grafana_url, http_get_headers, verify_ssl=False, client_cert=None, debug=True):
    return send_grafana_get('{0}/api/users/{1}/orgs'.format(grafana_url, id),
                            http_get_headers, verify_ssl, client_cert, debug)


def create_user(payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/admin/users'.format(grafana_url), payload, http_post_headers, verify_ssl, client_cert,
                             debug)


def add_user_to_org(org_id, payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/orgs/{1}/users'.format(grafana_url, org_id), payload, http_post_headers, verify_ssl, client_cert,
                             debug)


def search_contact_points(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    print("search contact points in grafana: {0}".format('{0}/api/v1/provisioning/contact-points'.format(grafana_url)))
    return send_grafana_get('{0}/api/v1/provisioning/contact-points'.format(grafana_url), http_get_headers, verify_ssl, client_cert, debug)


def create_contact_point(json_palyload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_post('{0}/api/v1/provisioning/contact-points'.format(grafana_url), json_palyload, http_post_headers, verify_ssl, client_cert, debug)


def update_contact_point(uid, json_palyload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_put('{0}/api/v1/provisioning/contact-points/{1}'.format(grafana_url, uid), json_palyload, http_post_headers, verify_ssl, client_cert, debug)


def search_notification_policies(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    print("search notification policies in grafana: {0}".format('{0}/api/v1/provisioning/policies'.format(grafana_url)))
    return send_grafana_get('{0}/api/v1/provisioning/policies'.format(grafana_url), http_get_headers, verify_ssl, client_cert, debug)


def update_notification_policy(json_palyload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    return send_grafana_put('{0}/api/v1/provisioning/policies'.format(grafana_url), json_palyload, http_post_headers, verify_ssl, client_cert, debug)


def search_notification_templates(grafana_url, http_get_headers, verify_ssl, client_cert, debug):
    print("search notification templates in grafana: {0}".format('{0}/api/v1/provisioning/templates'.format(grafana_url)))
    return send_grafana_get('{0}/api/v1/provisioning/templates'.format(grafana_url), http_get_headers, verify_ssl, client_cert, debug)

def update_notification_template(name, json_payload, grafana_url, http_post_headers, verify_ssl, client_cert, debug):
    url_safe_name = requests.utils.quote(name)
    url = '{0}/api/v1/provisioning/templates/{1}'.format(grafana_url, url_safe_name)

    return send_grafana_put(url, json_payload, http_post_headers, verify_ssl, client_cert, debug)


def get_grafana_version(grafana_url, verify_ssl, http_get_headers):
    r = requests.get('{0}/api/health'.format(grafana_url),
                     verify=verify_ssl, headers=http_get_headers)
    if r.status_code == 200:
        if 'version' in r.json().keys():
            version_str = r.json()['version']
            pattern = r'\b(\d+\.\d+\.\d+)'
            # Extract major, minor, and patch version components only
            match = re.search(pattern, version_str)

            if match:
                version_number = match.group(1)
            else:
                raise Exception(
                    "version key found but string value could not be parsed, returned respone: {0}".format(r.json))

            return version.parse(version_number)
        else:
            raise KeyError(
                "Unable to get version, returned respone: {0}".format(r.json))
    else:
        raise Exception(
            "Unable to get version, returned response: {0}".format(r.status_code))


def send_grafana_get(url, http_get_headers, verify_ssl, client_cert, debug):
    r = requests.get(url, headers=http_get_headers,
                     verify=verify_ssl, cert=client_cert)
    try:
        status_message = r.json()
    except ValueError:
        status_message = to_python2_and_3_compatible_string(r.text)

    if debug:
        log_response(r)
    return (r.status_code, status_message)


def send_grafana_post(url, json_payload, http_post_headers, verify_ssl=False, client_cert=None, debug=True):
    r = requests.post(url, headers=http_post_headers,
                      data=json_payload, verify=verify_ssl, cert=client_cert)
    if debug:
        log_response(r)
    try:
        return (r.status_code, r.json())
    except ValueError:
        return (r.status_code, r.text)


def send_grafana_put(url, json_payload, http_post_headers, verify_ssl=False, client_cert=None, debug=True):
    r = requests.put(url, headers=http_post_headers,
                     data=json_payload, verify=verify_ssl, cert=client_cert)
    if debug:
        log_response(r)
    return (r.status_code, r.json())


def send_grafana_delete(url, http_get_headers, verify_ssl=False, client_cert=None, debug=True):
    r = requests.delete(url, headers=http_get_headers,
                        verify=verify_ssl, cert=client_cert)
    return int(r.status_code)
