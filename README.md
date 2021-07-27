# User audit script

currently we are using this tio disable atlassian accounts which are not being used for 3 months by default. However it can be expaneded to more if and when required

## Usage
- **default**<br><br>
This options disabled all the users who have not logged in in last 3 months from todays date and, sets reason as  'automated cleanup script' <br>
```$python manage.py diable_users```

- **with desired last active date date**<br>
with date in %d-%m-%Y format. i.e. to disable users who last logged in before 1st April 2021, we wukk use following command<br><br>
```python manage.py --desired-last-active-date 01-4-2021 ```

- **with reason to diable** <br>
default reason to disable is 'automated cleanup script' however, if you like to specify reason user following command<br><br>
```$python manage.py --disable-reason 'that\'s the way it is'```


- **combined** <br>
```$python manage.py  --disable-date 01-01-2052 --disable-reason 'cause .. i has the power'``` ```

## Environment variables 
- DEBUG=True <br>
- SECRET_KEY=\<yourkey\> <br>
- ALLOWED_HOSTS= localhost,127.0.0.1<br>
- ATLASSIAN_URL=https://api.atlassian.com<br>
- ATLASSIAN_ORG_NAME=\<your org name\>
- ATLASSIAN_AUTH_TOKEN=\<your admin api token\>