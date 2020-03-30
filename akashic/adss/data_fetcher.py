import requests
import json

class DataFetcher(object):

    def __init__(self, auth_header, headers):
        self.headers = {}
        if (auth_header != None):
            self.headers[auth_header.auth_header_name] = auth_header.token_prefix + " " + auth_header.token
        
        if (headers != None):
            for h in headers:
                self.headers[h.header_name] = h.header_value


    def create(self, url, payload, headers):
        response = requests.post(url, data=json.dumps(payload), headers=headers.update(self.headers))
        response.raise_for_status()
        return response.text


    def read_one(self, url, headers):
        response = requests.get(url, headers=headers.update(self.headers))
        response.raise_for_status()
        return response.text


    def read_multiple(self, url, headers):
        response = requests.get(url, headers=headers.update(self.headers))
        response.raise_for_status()
        return response.text


    def update(self, url, payload, headers):
        response = requests.put(url, data=json.dumps(payload), headers=headers.update(self.headers))
        response.raise_for_status()
        return response.text
    

    def delete(self, url, headers):
        response = requests.delete(url, headers=headers.update(self.headers))
        response.raise_for_status()
        return response.text
    
