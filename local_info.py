"""Info IP laptop: lokal + publik."""
import socket, urllib.request


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return None


def get_public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=3) as r:
            return r.read().decode().strip()
    except Exception:
        return None
