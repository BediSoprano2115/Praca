from hubspot import HubSpot
from urllib3.util.retry import Retry
import os

class Config:
    hs = os.getenv('HUBSPOT_ACCESS_TOKEN')
    hubspot_client = HubSpot(access_token=hs, retry=Retry(total=5, status_forcelist=(429, ))) 
    HUBSPOT_API_TOKEN = 'pat-eu1-1bfb61a0-5d6b-4a25-b674-7ceaf966c12a'
    HUBSPOT_POSTS_URL = "https://api.hubapi.com/cms/v3/blogs/posts"
    HUBSPOT_HUBDB_URL = "https://api.hubapi.com/cms/v3/hubdb/tables"
    HUBSPOT_TAGS_URL =  "https://api.hubapi.com/cms/v3/blogs/tags"