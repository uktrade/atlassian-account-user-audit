# Atlassian audit script
To disable all atlassin user who have not logged in since last active date ( default 3 months ago). This can be configured with the optional env var MAX_USER_AGE_MONTHS.

## Usage

- **default** <br>
  This will disable users who have not logged in since last 3 months and, put reason as "automated cleanup script" <br>
```$python cleanup_atlassian.py```

- **with specific last active date**<br>
This example will disable users who have not logged in since specified date, to disable users who have not logged in since *1st April 2021* and, put reason as "automated cleanup script"<br>
```$python cleanup_atlassian.py --last-active 01-04-2021```

- **with specific reason** <br>
This example will disable users and give it user specififed reason.<br>
```$python cleanup_atlassian.py --reason 'that\'s way it is'```

- **more**<br>
You can speicfy some more parms, to see full list just do<br>
```python cleanup_atlassian.py --help```

## Environment Variables
| Variable | Description | Default |
| -------- | ----------- | ------- |
| ATLASSIAN_URL | \<atlassian admin api url\><br> | |
| ATLASSIAN_ORG_NAME | \<atlassian organisation name\><br> | |
| ATLASSIAN_AUTH_TOKEN | \<atlassian admin api token\><br> | |
| MAX_USER_AGE_MONTHS | Max user age (months) | `3` |
| MAX_DISABLE_RATE | Rate limit. Max users to disable in any one run | `10` |
| ENABLE_DEACTIVATIONS | Set to `True` to enable deactivations | `False` |
