import requests
import json

class Atlassian:

    def __init__(self,url,organisation_name,auth_token):
        self.url = url
        self.organisation_name = organisation_name
        self.get_headers = { "Accept": "application/json", "Authorization": f"Bearer {auth_token}" }
        self.post_headers = { "Content-Type": "application/json", "Authorization": f"Bearer {auth_token}" }

    def __apiPost(self,url,payload):
        payload = json.dumps({'message': payload})
        response = requests.request('POST',url,data=payload,headers=self.post_headers)
        
        if response.status_code != 204:
            raise RuntimeError(f'Error: {response.status_code} Message:{response.text}')
                
    def __apiGet(self,url):
        response_data = []
        original_url = url

        while True:
            response = requests.request('GET',url,headers=self.get_headers)

            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                break

            response_json = json.loads(response.text)

            response_data += response_json['data']

            response_links = response_json['links']

            #check if there is more data to fetch!
            if "next" in response_links:
                if response_links['next']:
                    url = response_links['next']
                else:
                    break
            #break if next key is not found!
            else:
                break

        url = original_url
        return response_data

    def getOrgs(self):
        orgs_url = f'{self.url}/admin/v1/orgs'
        return self.__apiGet(url=orgs_url)

    def getOrgId(self):

        orgId = ''

        accountOrgs = self.getOrgs()

        for org in accountOrgs:
            if (org['attributes']['name']).lower() == self.organisation_name.lower():
                orgId = org['id']
                break

        return orgId

    def getOrgUsers(self):
        orgId = self.getOrgId()
        url = f'{self.url}/admin/v1/orgs/{orgId}/users'
        return self.__apiGet(url=url)                


    def disableUser(self,user_id,message):
        url = f'{self.url}/users/{user_id}/manage/lifecycle/disable'
        self.__apiPost(url=url,payload=message)