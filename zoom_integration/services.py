import requests
import time
import jwt
from django.conf import settings
from datetime import datetime, timedelta

class ZoomService:
    def __init__(self):
        self.account_id = settings.ZOOM_ACCOUNT_ID
        self.client_id = settings.ZOOM_CLIENT_ID
        self.client_secret = settings.ZOOM_CLIENT_SECRET
        self.access_token = None
        self.token_expires_at = None
        
    def get_access_token(self):
        """Get or refresh Zoom access token using Server-to-Server OAuth"""
        if self.access_token and self.token_expires_at and time.time() < self.token_expires_at:
            return self.access_token
        
        url = "https://zoom.us/oauth/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "account_credentials",
            "account_id": self.account_id,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires_at = time.time() + token_data['expires_in']
            return self.access_token
        else:
            raise Exception(f"Failed to get Zoom access token: {response.text}")
    
    def create_meeting(self, topic, start_time, duration_minutes, timezone='UTC'):
        """Create a Zoom meeting"""
        access_token = self.get_access_token()
        
        url = "https://api.zoom.us/v2/users/me/meetings"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_time.isoformat(),
            "duration": duration_minutes,
            "timezone": timezone,
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "watermark": False,
                "use_pmi": False,
                "approval_type": 0,
                "registration_type": 1,
                "audio": "both",
                "auto_recording": "none"
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            meeting_data = response.json()
            return {
                'meeting_id': meeting_data['id'],
                'join_url': meeting_data['join_url'],
                'start_url': meeting_data['start_url'],
                'password': meeting_data.get('password', '')
            }
        else:
            raise Exception(f"Failed to create Zoom meeting: {response.text}")
    
    def delete_meeting(self, meeting_id):
        """Delete a Zoom meeting"""
        access_token = self.get_access_token()
        
        url = f"https://api.zoom.us/v2/meetings/{meeting_id}"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.delete(url, headers=headers)
        return response.status_code == 204

zoom_service = ZoomService()