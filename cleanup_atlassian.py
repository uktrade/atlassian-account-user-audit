import fire
import uplink
from dateutil.parser import parse as parse_dt
from furl import furl
from uplink.auth import BearerToken

BASE_URL = 'https://api.atlassian.com/'


class Atlassian(uplink.Consumer):

    @uplink.get('admin/v1/orgs/{org_id}/users')
    def get_users(self, org_id, cursor: uplink.Query = None):
        """get atlassian users for an org"""

    @uplink.json
    @uplink.post('users/{account_id}/manage/lifecycle/disable')
    def disable_user(self, account_id, body: uplink.Body):
        "disable a user given their account id"


def get_cursor(data):
    if not 'links' in data:
        return
    if not 'next' in data['links']:
        return

    next_ = data['links']['next']
    parse_result = furl(next_)
    return parse_result.args['cursor']


def cleanup(org_id, api_key, last_active):
    """
    Cleanup inactive atlassian accounts

    :param org_id: Organisation ID
    :param api_key: API Key
    :param last_active: remove users that haven't logged in since this date (e.g. 2020-01-01T00:00Z)
    """
    a = Atlassian(base_url=BASE_URL, auth=BearerToken(api_key))
    resp = a.get_users(org_id)
    users = resp.json()['data']

    c = get_cursor(resp.json())
    while c:
        print(f"cursor is {c}")
        resp = a.get_users(org_id, cursor=c)
        users.extend(resp.json()['data'])
        c = get_cursor(resp.json())

    active_users = [x for x in users if x['account_status'] == 'active']

    not_active_users = [
        x for x in active_users
        if 'last_active' in x and parse_dt(x['last_active']) < parse_dt(last_active)
    ]

    for user in not_active_users:
        msg = {'message': "automated cleanup script"}
        print(
            f"cleaning up: {user['name']} because their last access was: {user['last_active']}")
        a.disable_user(user['account_id'], body=msg)


if __name__ == '__main__':
    fire.Fire(cleanup)
