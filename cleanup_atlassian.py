import logging
import os
import sys
from datetime import datetime

import ecs_logging
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
EARLIST_USER_DATE = (
    datetime.today() - relativedelta(months=MAX_USER_AGE_MONTHS)
).strftime("%d-%m-%Y")
MAX_DISABLE_RATE = int(os.environ.get("MAX_DISABLE_RATE", 10))
TRUE_VALUES = ("on", "yes", "true")
ENABLE_DEACTIVATIONS = os.environ.get("ENABLE_DEACTIVATIONS", "").lower() in TRUE_VALUES
REASON = "automated cleanup script"
BOT_USERS = [email.strip() for email in os.environ.get("BOT_USERS").split(",")]


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
    last_active=(datetime.strptime(EARLIST_USER_DATE, "%d-%m-%Y"))
    .replace(tzinfo=UTC)
    .isoformat(),
):
    """
    Cleanup inactive atlassian accounts
    :param base_url: base api endpoint
    :param organisation_name: Organisation name
    :param api_key: API Key
    :param reason: reason to disable account
    :param last_active: remove users that haven't logged in since this date in %d-%m-%Y (e.g. 1st April 2021 would be 1-4-2021)
    """

    logger.info("MAX_USER_AGE_MONTHS: %s", MAX_USER_AGE_MONTHS)
    logger.info("EARLIST_USER_DATE: %s", EARLIST_USER_DATE)
    logger.info("MAX_DISABLE_RATE: %s", MAX_DISABLE_RATE)
    logger.info("ENABLE_DEACTIVATIONS: %s", ENABLE_DEACTIVATIONS)

    if MAX_USER_AGE_MONTHS < 1:
        logger.error(
            "MAX_USER_AGE_MONTHS is set to %s. You don't want to set this less than 1!",
            MAX_USER_AGE_MONTHS,
        )
        exit(1)

    atlassian_client = Atlassian(base_url=base_url, auth=BearerToken(api_key))

    # get org id from name
    logger.info("Reading organisations")
    resp = atlassian_client.get_orgs()
    logger.info("Response: %s", resp)

    organisations = resp.json()["data"]
    logger.info("Organisations: %s", organisations)

    c = get_cursor(resp.json())

    while c:
        resp = atlassian_client.get_orgs(cursor=c)
        organisations.extend(resp.json()["data"])
        c = get_cursor(resp.json())

    orgId = None

    for org in organisations:
        logger.info("Organisation: %s", org)
        if (org["attributes"]["name"]).lower() == organisation_name.lower():
            orgId = org["id"]
            logger.info("Organisation ID: %s", orgId)
            break

    # if we find org id!
    if orgId:
        logger.info("Reading organisation users")
        resp = atlassian_client.get_users(org_id=orgId)
        logger.info("Response: %s", resp)
        users = resp.json()["data"]

        c = get_cursor(resp.json())
        while c:
            resp = atlassian_client.get_users(org_id=orgId, cursor=c)
            users.extend(resp.json()["data"])
            c = get_cursor(resp.json())
        logger.info("Total users: %s", len(users))

        active_users = [x for x in users if x["account_status"] == "active"]
        logger.info("Total active users: %s", len(active_users))

        logger.info("Get aged users, active but not logged in since %s", last_active)

        not_active_users = []
        for user in active_users:
            # if user is a bot user, ignore and continue
            if user["email"] in BOT_USERS:
                logger.info("skipping because,%s is a bot user", user["name"])
                continue
            # if product_access is not an empty list
            if user["product_access"]:
                product_last_access_dates = []
                for product in user["product_access"]:
                    if "last_active" in product:
                        # Having to strip out the "microseconds" here since strptime supports
                        # 6 DPs and the Atlassian API has started returning 9.
                        # Nanosecond accuracy not required here!
                        # Recent example: '2023-08-01T15:19:32.354230769Z'
                        # Throws a ValueError: time data does not match format '%Y-%m-%dT%H:%M:%S.%fZ'
                        product_last_access_dates.append(
                            datetime.strptime(
                                product["last_active"].split(".")[0]+"Z",
                                "%Y-%m-%dT%H:%M:%SZ"
                            )
                            .replace(tzinfo=UTC)
                            .isoformat()
                        )
                # check if all product access dates are older than 3 months,
                # if so add user to not_active_user
                if all(
                    parse_dt(date) < parse_dt(last_active)
                    for date in product_last_access_dates
                ):
                    not_active_users.append(user)
            # if product_access is an empty list we resort to checking top level last_active date
            elif "last_active" in user and parse_dt(user["last_active"]) < parse_dt(
                last_active
            ):
                not_active_users.append(user)

        logger.info("Total activated aged users: %s", len(not_active_users))

        for index, user in enumerate(not_active_users):
            msg = {"message": reason}
            if index >= MAX_DISABLE_RATE:
                logger.info("Hit rate limit of %s. Stopping.", MAX_DISABLE_RATE)
                break
            if ENABLE_DEACTIVATIONS:
                logger.info(
                    "Disabling user '%s' (index %s) because their last access was: %s",
                    user.get("name","none"),
                    index,
                    user.get("last_active","'none'"),
                )
                resp = atlassian_client.disable_user(user["account_id"], body=msg)
                logger.info("Response: %s", resp)
            else:
                logger.info(
                    "User deactivation not enabled. But user '%s' (index %s) would be deactivated because their last access was: %s",
                    user.get("name","none"),
                    index,
                    user.get("last_active","'none'"),
                )
    else:
        logger.error('Error: Atlassian organisation "%s" not found', organisation_name)
        raise RuntimeError(
            f'Error: Atlassian organisation "{organisation_name}" not found'
        )


if __name__ == "__main__":
    fire.Fire(cleanup)
