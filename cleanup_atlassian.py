import os
from datetime import datetime
import logging
import ecs_logging
import sys

import fire
import uplink
from dateutil.parser import parse as parse_dt
from dateutil.relativedelta import relativedelta
from dateutil.tz import UTC
from furl import furl
from uplink.auth import BearerToken

# Set up logging (ECS)
logger = logging.getLogger("CLEANUP-ATLASSIAN")
logger.setLevel(os.environ.get("LOGGING_LEVEL", logging.DEBUG))

# Warnings and above log to the stderr stream
stderr_handler = logging.StreamHandler(stream=sys.stderr)
stderr_handler.setLevel(logging.WARNING)
stderr_handler.setFormatter(ecs_logging.StdlibFormatter())
logger.addHandler(stderr_handler)

# Events below Warning log to the stdout stream
stdout_handler = logging.StreamHandler(stream=sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.addFilter(lambda record: record.levelno < logging.WARNING)
stdout_handler.setFormatter(ecs_logging.StdlibFormatter())
logger.addHandler(stdout_handler)

# set Variables
ATLASSIAN_URL = os.environ["ATLASSIAN_URL"].strip("\r")
ATLASSIAN_ORG_NAME = os.environ["ATLASSIAN_ORG_NAME"].strip("\r")
ATLASSIAN_AUTH_TOKEN = os.environ["ATLASSIAN_AUTH_TOKEN"].strip("\r")
MAX_USER_AGE_MONTHS = int(os.environ.get("MAX_USER_AGE_MONTHS", 3))
EARLIST_USER_DATE = (datetime.today() - relativedelta(months=MAX_USER_AGE_MONTHS)).strftime("%d-%m-%Y")
MAX_DISABLE_RATE = int(os.environ.get("MAX_DISABLE_RATE", 10))
TRUE_VALUES = ('on', 'yes', 'true')
ENABLE_DEACTIVATIONS = os.environ.get("ENABLE_DEACTIVATIONS", "").lower() in TRUE_VALUES
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
    last_active=(datetime.strptime(EARLIST_USER_DATE, "%d-%m-%Y")).replace(tzinfo=UTC).isoformat(),
):
    """
    Cleanup inactive atlassian accounts
    :param base_url: base api endpoint
    :param organisation_name: Organisation name
    :param api_key: API Key
    :param reason: reason to disable account
    :param last_active: remove users that haven't logged in since this date in %d-%m-%Y (e.g. 1st April 2021 would be 1-4-2021)
    """

    logger.info(f"MAX_USER_AGE_MONTHS: {MAX_USER_AGE_MONTHS}")
    logger.info(f"EARLIST_USER_DATE: {EARLIST_USER_DATE}")
    logger.info(f"MAX_DISABLE_RATE: {MAX_DISABLE_RATE}")
    logger.info(f"ENABLE_DEACTIVATIONS: {ENABLE_DEACTIVATIONS}")

    if MAX_USER_AGE_MONTHS < 1:
        logger.error(f"MAX_USER_AGE_MONTHS is set to {MAX_USER_AGE_MONTHS}. You don't want to set this less than 1!")
        exit(1)

    atlassian_client = Atlassian(base_url=base_url, auth=BearerToken(api_key))

    # get org id from name
    logger.info("Reading organisations")
    resp = atlassian_client.get_orgs()
    logger.info(f"Response: {resp}")

    organisations = resp.json()["data"]
    logger.info(f"Organisations: {organisations}")

    c = get_cursor(resp.json())

    while c:
        resp = atlassian_client.get_orgs(cursor=c)
        organisations.extend(resp.json()["data"])
        c = get_cursor(resp.json())

    orgId = None

    for org in organisations:
        logger.info(f"Organisation: {org}")
        if (org["attributes"]["name"]).lower() == organisation_name.lower():
            orgId = org["id"]
            logger.info(f"Organisation ID: {orgId}")
            break

    # if we find org id!
    if orgId:
        logger.info("Reading organisation users")
        resp = atlassian_client.get_users(org_id=orgId)
        logger.info(f"Response: {resp}")

        users = resp.json()["data"]

        c = get_cursor(resp.json())
        while c:
            resp = atlassian_client.get_users(org_id=orgId, cursor=c)
            users.extend(resp.json()["data"])
            c = get_cursor(resp.json())
        logger.info(f"Total users: {len(users)}")

        active_users = [x for x in users if x["account_status"] == "active"]
        logger.info(f"Total active users: {len(active_users)}")

        logger.info(f"Get aged users, active but not logged in since {last_active}")
        not_active_users = [
            x
            for x in active_users
            if "last_active" in x and parse_dt(x["last_active"]) < parse_dt(last_active)
        ]
        logger.info(f"Total activated aged users: {len(not_active_users)}")

        for index, user in enumerate(not_active_users):
            msg = {"message": reason}
            if index >= MAX_DISABLE_RATE:
                logger.info(f"Hit rate limit of {MAX_DISABLE_RATE}. Stopping.")
                break
            if ENABLE_DEACTIVATIONS:
                logger.info(f"Disabling user '{user['name']}' (index {index}) because their last access was: {user['last_active']}")
                resp = atlassian_client.disable_user(user["account_id"], body=msg)
                logger.info(f"Response: {resp}")
            else:
                logger.info(f"User deactivation not enabled. But user '{user['name']}' (index {index}) would be deactivated because their last access was: {user['last_active']}")
    else:
        logger.error( f'Error: Atlassian organisation "{organisation_name}" not found')
        raise RuntimeError(
            f'Error: Atlassian organisation "{organisation_name}" not found'
        )


if __name__ == "__main__":
    fire.Fire(cleanup)
