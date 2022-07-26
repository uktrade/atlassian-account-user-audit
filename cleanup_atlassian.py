import os
from datetime import datetime

import fire
import uplink
from dateutil.parser import parse as parse_dt
from dateutil.relativedelta import relativedelta
from dateutil.tz import UTC
from furl import furl
from uplink.auth import BearerToken

# set Variables
ATLASSIAN_URL = os.environ["ATLASSIAN_URL"].strip("\r")
ATLASSIAN_ORG_NAME = os.environ["ATLASSIAN_ORG_NAME"].strip("\r")
ATLASSIAN_AUTH_TOKEN = os.environ["ATLASSIAN_AUTH_TOKEN"].strip("\r")
THREE_MONTHS_AGO = (datetime.today() - relativedelta(months=3)).strftime("%d-%m-%Y")
REASON = "automated cleanup script"


class Atlassian(uplink.Consumer):
    @uplink.get("admin/v1/orgs")
    def get_orgs(self, cursor: uplink.Query = None):
        """get all the orgs for which key has an access"""

    @uplink.get("admin/v1/orgs/{org_id}/users")
    def get_users(self, org_id, cursor: uplink.Query = None):
        """get atlassian users for an org"""

    @uplink.json
    @uplink.post("users/{account_id}/manage/lifecycle/disable")
    def disable_user(self, account_id, body: uplink.Body):
        "disable a user given their account id"


def get_cursor(data):
    if not "links" in data:
        return
    if not "next" in data["links"]:
        return

    next_ = data["links"]["next"]
    parse_result = furl(next_)
    return parse_result.args["cursor"]


def cleanup(
    base_url=ATLASSIAN_URL,
    organisation_name=ATLASSIAN_ORG_NAME,
    api_key=ATLASSIAN_AUTH_TOKEN,
    reason=REASON,
    last_active=THREE_MONTHS_AGO,
):
    """
    Cleanup inactive atlassian accounts
    :param base_url: base api endpoint
    :param organisation_name: Organisation name
    :param api_key: API Key
    :param reason: reason to disable account
    :param last_active: remove users that haven't logged in since this date in %d-%m-%Y (e.g. 1st April 2021 would be 1-4-2021)
    """

    last_active = (
        (datetime.strptime(last_active, "%d-%m-%Y")).replace(tzinfo=UTC).isoformat()
    )

    atlassian_client = Atlassian(base_url=base_url, auth=BearerToken(api_key))

    # get org id from name
    resp = atlassian_client.get_orgs()

    organisations = resp.json()["data"]

    c = get_cursor(resp.json())

    while c:
        resp = atlassian_client.get_orgs(cursor=c)
        organisations.extend(resp.json()["data"])
        c = get_cursor(resp.json())

    orgId = None

    for org in organisations:
        if (org["attributes"]["name"]).lower() == organisation_name.lower():
            orgId = org["id"]
            break

    # if we find org id!
    if orgId:
        resp = atlassian_client.get_users(org_id=orgId)

        users = resp.json()["data"]

        c = get_cursor(resp.json())
        while c:
            resp = atlassian_client.get_users(org_id=orgId, cursor=c)
            users.extend(resp.json()["data"])
            c = get_cursor(resp.json())

        active_users = [x for x in users if x["account_status"] == "active"]

        not_active_users = [
            x
            for x in active_users
            if "last_active" in x and parse_dt(x["last_active"]) < parse_dt(last_active)
        ]

        for user in not_active_users:
            msg = {"message": reason}
            print(
                f"cleaning up: {user['name']} because their last access was: {user['last_active']}"
            )
            atlassian_client.disable_user(user["account_id"], body=msg)

    else:
        raise RuntimeError(
            f'Error: Atlassian organisation "{organisation_name}" not found'
        )


if __name__ == "__main__":
    fire.Fire(cleanup)
