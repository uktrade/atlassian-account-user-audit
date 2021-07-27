from django.core.management.base import BaseCommand
from django.conf import settings

from atlassian import Atlassian

from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as parse_dt

import time
import traceback

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--desired-last-active-date',type=str)
        parser.add_argument('--disable-reason',default='automated cleanup script',type=str)

    def handle(self, *args, **options):
        start_time = time.perf_counter()
        try:
            # set reason 
            disable_reason = options['disable_reason']

            desired_last_active_date_format = '%d-%m-%Y'
            desired_last_active_date = options['desired_last_active_date']

            # set last active date
            if desired_last_active_date is None:
                desired_last_active_date = (datetime.today() - relativedelta(months=3)).strftime(desired_last_active_date_format)
          
            desired_last_active_date_obj = datetime.strptime(desired_last_active_date,desired_last_active_date_format).date()
           
            atlassian_client = Atlassian(url = settings.ATLASSIAN_URL, organisation_name = settings.ATLASSIAN_ORG_NAME, auth_token = settings.ATLASSIAN_AUTH_TOKEN)

            orgUsers = atlassian_client.getOrgUsers()
            active_users = [user for user in orgUsers if user['account_status'] == 'active']

            target_users = [ 
                user for user in active_users
                if 'last_active' in user and parse_dt(user['last_active']).date() < desired_last_active_date_obj
            ]

            for user in target_users:
                print(f"cleaning up: {user['name']} because their last access was: {parse_dt(user['last_active']).date()}")
                atlassian_client.disableUser(user_id=user['account_id'],message=disable_reason)

        except Exception as e:
            print(f'Error:{e}')
            traceback.print_exc()

        run_time = time.perf_counter() - start_time
        print(f"run time:{run_time}")        