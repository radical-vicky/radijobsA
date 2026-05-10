import requests
from django.conf import settings


def get_zoom_access_token():
    """Get Zoom OAuth access token"""
    try:
        token_url = "https://zoom.us/oauth/token"
        
        account_id = settings.ZOOM_ACCOUNT_ID
        client_id = settings.ZOOM_CLIENT_ID
        client_secret = settings.ZOOM_CLIENT_SECRET
        
        # Check if credentials are configured
        if not account_id or not client_id or not client_secret:
            return {
                'success': False,
                'error': 'Zoom credentials not configured. Please check your .env file.'
            }
        
        data = {
            'grant_type': 'account_credentials',
            'account_id': account_id,
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            return {
                'success': True,
                'access_token': response.json().get('access_token'),
            }
        else:
            return {
                'success': False,
                'error': f'Zoom auth failed: {response.status_code} - {response.text}'
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def create_meeting(topic, start_time, duration_minutes=60):
    """Create a REAL Zoom meeting"""
    
    # Get access token
    token_response = get_zoom_access_token()
    
    if not token_response.get('success'):
        return {
            'success': False,
            'error': token_response.get('error', 'Failed to authenticate with Zoom')
        }
    
    try:
        headers = {
            'Authorization': f'Bearer {token_response["access_token"]}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'topic': topic,
            'type': 2,  # Scheduled meeting
            'start_time': start_time.isoformat(),
            'duration': duration_minutes,
            'timezone': 'UTC',
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': False,
                'mute_upon_entry': True,
                'waiting_room': True
            }
        }
        
        response = requests.post(
            'https://api.zoom.us/v2/users/me/meetings',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 201:
            data = response.json()
            return {
                'success': True,
                'join_url': data.get('join_url'),
                'meeting_id': data.get('id'),
                'start_url': data.get('start_url')
            }
        else:
            return {
                'success': False,
                'error': f'Zoom API error: {response.status_code} - {response.text}'
            }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_meeting(meeting_id):
    """Get meeting details"""
    token_response = get_zoom_access_token()
    
    if not token_response.get('success'):
        return {'success': False, 'error': token_response.get('error')}
    
    try:
        headers = {'Authorization': f'Bearer {token_response["access_token"]}'}
        
        response = requests.get(
            f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        return {'success': False, 'error': 'Meeting not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}