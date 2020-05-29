
import requests
import json



class DataFetcher(object):
    """ DataFetcher class

    This class sends defines requests to specified web service APIs.
    """

    def __init__(self, auth_header, headers):
        """ DataFetcher constructor method
        
        Parameters
        ----------
        auth_header : object
            Object containing authentication token header name,
            token and token prefix
        headers : dict
            Dictionary containing header data pairs of
            'header_name : header_value'
        """

        self.headers = {}
        if (auth_header != None):
            self.headers[auth_header.auth_header_name] = \
                auth_header.token_prefix + " " + auth_header.token

        if (headers != None):
            for h in headers:
                self.headers[h.header_name] = h.header_value



    def create(self, url, payload, headers):
        """ Sends 'create' request to the web server
        
        Parameters
        ----------
        url : str
            REST URL on which request will be sent
        payload : object
            JSON object containing data for creation of new entity
        headers : dict
            Dictionary containing header data pairs of 
            'header_name : header_value'
        
        Returns
        -------
        str
            JSON string representing created entity
        """

        headers.update(self.headers)
        response = requests.post(
            url, 
            data=json.dumps(payload), 
            headers=headers
        )
        response.raise_for_status()
        return response.text



    def read_one(self, url, headers):
        """ Sends 'read_one' request to the web server
        
        Parameters
        ----------
        url : str
            REST URL on which request will be sent
        headers : dict
            Dictionary containing header data pairs of 
            'header_name : header_value'
        
        Returns
        -------
        str
            JSON string representing read entity
        """

        headers.update(self.headers)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text



    def read_multiple(self, url, headers):
        """ Sends 'read_multiple' request to the web server
        
        Parameters
        ----------
        url : str
            REST URL on which request will be sent
        headers : dict
            Dictionary containing header data pairs of
            'header_name : header_value'
        
        Returns
        -------
        str
            JSON string representing read array of entities
        """
       
        headers.update(self.headers)
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text



    def update(self, url, payload, headers):
        """ Sends 'update' request to the web server
        
        Parameters
        ----------
        url : str
            REST URL on which request will be sent
        payload : object
            JSON object containing data for updating of new entity
        headers : dict
            Dictionary containing header data pairs of 
            'header_name : header_value'
        
        Returns
        -------
        str
            JSON string representing created entity
        """

        headers.update(self.headers)
        response = requests.put(
            url, 
            data=json.dumps(payload), 
            headers=headers
        )
        response.raise_for_status()
        return response.text
    

    def delete(self, url, headers):
        """ Sends 'delete' request to the web server
        
        Parameters
        ----------
        url : str
            REST URL on which request will be sent
        headers : dict
            Dictionary containing header data pairs of 
            'header_name : header_value'
        
        Returns
        -------
        str
            Empty.
        """

        headers.update(self.headers)
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return response.text
    
