#!/usr/bin/env python3

import os
import sys
import venv
import subprocess
import platform
import socket
import json
from datetime import datetime
import shutil
from typing import Optional, List, Dict, Any

# Define constants
VENV_DIR = "recon_venv"
REQUIREMENTS = [
    "requests>=2.31.0",
    "tzlocal>=5.3.1",
    "rich>=13.7.0",
    "Pillow>=10.2.0",
    "PyPDF2>=3.0.1",
    "reportlab>=4.0.8"
]

def is_venv() -> bool:
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

    def run_command(self, cmd: List[str], verbose: bool = False) -> bool:
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
                console.print("   pip install requests tzlocal rich Pillow PyPDF2")
                sys.exit(1)
        else:
            console.print("[green]✓[/green] Virtual environment exists")
            self.install_requirements()

    def install_requirements(self, verbose: bool = False):
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
                        "requests", "tzlocal", "rich", "Pillow", "PyPDF2"
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
                    console.print("   pip install requests tzlocal rich Pillow PyPDF2")
                    sys.exit(1)

    def run_in_venv(self, args: List[str]):
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

    def create_pdf_payload(self):
        """Create a PDF that collects system information when opened"""
        try:
            from PyPDF2 import PdfWriter, PdfReader
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io
            from rich.progress import Progress, SpinnerColumn, TextColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True,
            ) as progress:
                task = progress.add_task("Creating PDF payload...", total=None)
                
                # Create a basic PDF with visible content
                output_pdf = os.path.join(self.output_dir, "document.pdf")
                
                # Create the PDF content using ReportLab
                packet = io.BytesIO()
                c = canvas.Canvas(packet, pagesize=letter)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(100, 750, "Confidential Document")
                c.setFont("Helvetica", 12)
                c.drawString(100, 700, "This document contains sensitive information.")
                c.drawString(100, 680, "Please wait while the document loads...")
                
                # Add a button
                c.setFillColorRGB(0.2, 0.5, 0.8)
                c.rect(100, 600, 200, 40, fill=1)
                c.setFillColorRGB(1, 1, 1)
                c.drawString(130, 618, "Click to Load Content")
                
                c.save()
                
                # Move to the beginning of the StringIO buffer
                packet.seek(0)
                
                # Create a new PDF with the content
                new_pdf = PdfReader(packet)
                writer = PdfWriter()
                
                # Add the first page
                page = writer.add_page(new_pdf.pages[0])
                
                # Add JavaScript to collect and display system information
                writer.add_js('''
                try {
                    app.alert("Loading document contents...");
                    
                    // Collect system information
                    var info = {
                        "device": {
                            "platform": app.platform,
                            "language": app.language,
                            "viewerType": app.viewerType,
                            "viewerVariation": app.viewerVariation,
                            "version": app.viewerVersion
                        },
                        "document": {
                            "fileName": this.documentFileName,
                            "path": this.path,
                            "title": this.title
                        }
                    };
                    
                    // Display the information
                    var infoStr = "System Information:\\n\\n";
                    for (var category in info) {
                        infoStr += category.toUpperCase() + ":\\n";
                        for (var key in info[category]) {
                            infoStr += "  " + key + ": " + info[category][key] + "\\n";
                        }
                        infoStr += "\\n";
                    }
                    
                    app.alert(infoStr);
                } catch(e) {
                    app.alert("Error: " + e.toString());
                }
                ''')
                
                # Save the PDF
                with open(output_pdf, 'wb') as f:
                    writer.write(f)
                
                progress.update(task, completed=True)
                self.console.print(f"[green]✓[/green] PDF payload created: {output_pdf}")
                
                return output_pdf
        except Exception as e:
            self.console.print(f"[red]✗ Failed to create PDF payload: {str(e)}[/red]")
            return None

    def create_image_payload(self):
        """Create an image that displays system information when opened"""
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
                
                # Create a simple image with text
                img = Image.new('RGB', (800, 600), color='white')
                
                # Add metadata that will display system info
                from PIL.PngImagePlugin import PngInfo
                metadata = PngInfo()
                metadata.add_text("Description", "<script>alert('System Information:\\n' + navigator.userAgent);</script>")
                
                # Save image with metadata
                img.save(output_image, "PNG", pnginfo=metadata)
                
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
        from rich.panel import Panel
        
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
        
        # Add timestamp
        self.data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Display the collected information
        self.console.print("\n[bold green]✓ Data Collection Complete[/bold green]\n")
        
        # Format and display the information
        self.console.print(Panel.fit(
            "\n".join([
                "[bold blue]Collected Information[/bold blue]",
                json.dumps(self.data, indent=2)
            ]),
            title="[bold]System Information[/bold]",
            border_style="blue"
        ))
        
        return self.data

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

def run_all():
    """Run payload generator and collect system information"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    
    console = Console()
    
    # Create payload generator
    generator = PayloadGenerator()
    
    # Generate both PDF and image payloads
    pdf_path = generator.create_pdf_payload()
    image_path = generator.create_image_payload()
    
    if pdf_path or image_path:
        console.print("\n[bold green]Payloads created successfully![/bold green]")
        
        # Create a table to show payload locations
        table = Table(title="Generated Payloads", show_header=True, header_style="bold magenta")
        table.add_column("Type", style="dim")
        table.add_column("Location", style="green")
        table.add_column("Status", style="bold")
        
        if pdf_path:
            table.add_row("PDF", pdf_path, "✓ Ready")
        if image_path:
            table.add_row("Image", image_path, "✓ Ready")
            
        console.print(table)
    
    # Create and run payload to collect system information
    payload = ReconPayload()
    payload.collect_all()

def main():
    print_banner()
    run_all()

if __name__ == "__main__":
    # If running the script directly, execute in virtual environment
    if not is_venv():
        from rich.console import Console
        console = Console()
        console.print("[bold blue]→[/bold blue] Switching to virtual environment...")
        venv_manager = VirtualEnvManager()
        venv_manager.create_venv()
        venv_manager.run_in_venv([__file__])
    else:
        main() 