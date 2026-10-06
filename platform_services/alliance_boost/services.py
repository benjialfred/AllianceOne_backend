import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class IzyBoostAPIError(Exception):
    pass

class IzyBoostService:
    def __init__(self):
        self.api_key = getattr(settings, 'IZYBOOST_API_KEY', 'izy_live_aa0e13aa365ed1fb68d290c47802876c')
        self.base_url = "https://izyboost.site/api/v2"

    def _post(self, action: str, data: dict = None):
        if data is None:
            data = {}
        data['key'] = self.api_key
        data['action'] = action

        try:
            response = requests.post(self.base_url, json=data, timeout=10)
            if response.status_code != 200:
                logger.error(f"IzyBoost API Error {response.status_code}: {response.text}")
            
            response.raise_for_status()
            
            json_response = response.json()
            if isinstance(json_response, dict) and 'error' in json_response:
                 raise IzyBoostAPIError(json_response['error'])
            
            return json_response
        except requests.RequestException as e:
            logger.error(f"Network error calling IzyBoost API ({action}): {str(e)}")
            raise IzyBoostAPIError(f"API connection failed: {str(e)}")

    def get_services(self) -> list:
        """Fetch all services from IzyBoost."""
        return self._post("services")

    def create_order(self, service_id: int, link: str, quantity: int, comments: str = None) -> dict:
        """Place a new order on IzyBoost."""
        payload = {
            "service": service_id,
            "link": link,
            "quantity": quantity
        }
        if comments:
            payload["comments"] = comments
            
        return self._post("add", payload)

    def get_order_status(self, order_id: int) -> dict:
        """Get the status of an existing order."""
        payload = {
            "order": order_id
        }
        return self._post("status", payload)

    def get_balance(self) -> dict:
        """Get the current balance of the IzyBoost account."""
        return self._post("balance")
