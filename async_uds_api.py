# Заглушка для UDSClient - чтобы бот запустился
import logging

logger = logging.getLogger(__name__)


class UDSClient:
    def __init__(self, company_id=None, api_key=None, silence_httpx_log=True):
        self.company_id = company_id
        self.api_key = api_key
        self.silence_httpx_log = silence_httpx_log
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None
    
    async def settings_get(self):
        return None
    
    async def customers_find(self, phone):
        return None
    
    async def customers_get(self, customer_id):
        return None
