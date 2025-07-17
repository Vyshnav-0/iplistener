#!/usr/bin/env python3

from flask import Flask, request, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

# Ensure logs directory exists
if not os.path.exists('logs'):
    os.makedirs('logs')

@app.route('/collect', methods=['POST'])
def collect():
    """Endpoint to collect reconnaissance data"""
    try:
        data = request.get_json()
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        data['timestamp'] = timestamp
        
        # Save to file
        filename = f"logs/recon_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
            
        return jsonify({"status": "success", "message": f"Data saved to {filename}"}), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    print("Starting listener server on http://localhost:5000")
    print("Data will be saved to ./logs directory")
    app.run(host='0.0.0.0', port=5000) 