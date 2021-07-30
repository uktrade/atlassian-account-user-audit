# Atlassian audit script
To disable all atlassin user who have not logged in since last active date ( default 3 months ago)

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
- ATLASSIAN_URL=\<atlassian admin api url\><br>
- ATLASSIAN_ORG_NAME=\<atlassian organisation name\><br>
- ATLASSIAN_AUTH_TOKEN=\<atlassian admin api token\><br>
