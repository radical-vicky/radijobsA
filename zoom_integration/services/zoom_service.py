import requests
import json
from django.conf import settings
from datetime import datetime


def get_access_token():
    """Get Zoom access token using JWT or OAuth"""
    # For JWT authentication
    import jwt
    import time
    
    api_key = getattr(settings, 'ZOOM_API_KEY', '')
    api_secret = getattr(settings, 'ZOOM_API_SECRET', '')
    
    if not api_key or not api_secret:
        return None
    
    payload = {
        'iss': api_key,
        'exp': int(time.time()) + 60  # Token expires in 60 seconds
    }
    
    token = jwt.encode(payload, api_secret, algorithm='HS256')
    return token


def create_meeting(topic, start_time, duration_minutes=60, timezone='Africa/Nairobi'):
    """Create a Zoom meeting"""
    access_token = get_access_token()
    
    if not access_token:
        return {
            'success': False,
            'error': 'Zoom API credentials not configured'
        }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Format start time for Zoom API
    if isinstance(start_time, datetime):
        start_time = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    payload = {
        'topic': topic,
        'type': 2,  # Scheduled meeting
        'start_time': start_time,
        'duration': duration_minutes,
        'timezone': timezone,
        'settings': {
            'join_before_host': True,
            'waiting_room': False,
            'host_video': True,
            'participant_video': True,
            'mute_upon_entry': True,
            'approval_type': 0,  # Automatically approve
            'registrants_email_notification': False
        }
    }
    
    try:
        response = requests.post(
            'https://api.zoom.us/v2/users/me/meetings',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 201:
            data = response.json()
            return {
                'success': True,
                'meeting_id': data.get('id'),
                'join_url': data.get('join_url'),
                'start_url': data.get('start_url'),
                'password': data.get('password')
            }
        else:
            return {
                'success': False,
                'error': f"Zoom API error: {response.status_code} - {response.text}"
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_meeting(meeting_id):
    """Get meeting details"""
    access_token = get_access_token()
    
    if not access_token:
        return None
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        return None
        
    except Exception:
        return None


def update_meeting(meeting_id, updates):
    """Update meeting details"""
    access_token = get_access_token()
    
    if not access_token:
        return False
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.patch(
            f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers=headers,
            json=updates
        )
        
        return response.status_code == 204
        
    except Exception:
        return False


def delete_meeting(meeting_id):
    """Delete a meeting"""
    access_token = get_access_token()
    
    if not access_token:
        return False
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.delete(
            f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers=headers
        )
        
        return response.status_code == 204
        
    except Exception:
        return False