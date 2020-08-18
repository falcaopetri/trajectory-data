import requests
import logging

logger = logging.getLogger("fq_api.requests")

class Requests(object):

    _client_id = None
    _client_secret = None
    _status = None

    def config(self, client_id, client_secret):
        self._client_id = client_id
        self._client_secret = client_secret

    def get(self, endpoint, param = None, named_params = None):
        url = endpoint

        if param:
            url += param

        url += "?client_id=" + str(self._client_id)
        url += "&client_secret=" + str(self._client_secret)

        for p in named_params:
            url += "&" + p

        rsp = requests.get(url)
        self._status = rsp.status_code
        return rsp.json()

    def validate(self, response):
        if response['meta']['code'] != 200:
            logger.error("GET Request Error Code " + str(response['meta']['code']))
            logger.error("Error type: " + str(response['meta']['errorType']))
            logger.error("Error detail: " + str(response['meta']['errorDetail']))
            return False

        return True