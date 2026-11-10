"""ARP scan via scapy; fallback ke nmap kalau scapy gagal."""
import ipaddress, socket, subprocess

try:
    from scapy.all import ARP, Ether, srp, conf
    SCAPY_OK = True
except ImportError:
    SCAPY_OK = False


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return None


def get_local_subnet():
    ip = get_local_ip()
    return str(ipaddress.ip_network(f"{ip}/24", strict=False)) if ip else "192.168.1.0/24"


def _resolve(ip):
    try:
        socket.setdefaulttimeout(0.6)
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return None


def _sort(devs):
    return sorted(devs, key=lambda d: tuple(int(p) for p in d["ip"].split(".")))


def _scapy_scan(subnet, timeout=3):
    conf.verb = 0
    answered, _ = srp(
        Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=subnet),
        timeout=timeout, retry=2, verbose=False,
    )
    devs = [{"ip": r.psrc, "mac": r.hwsrc, "hostname": _resolve(r.psrc)}
            for _, r in answered]
    return {"subnet": subnet, "devices": _sort(devs), "count": len(devs)}


def _nmap_scan(subnet):
    try:
        r = subprocess.run(["nmap", "-sn", "-oG", "-", subnet],
                           capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        return {"error": "scapy gagal & nmap tidak terpasang. Jalankan dengan sudo."}
    except Exception as e:
        return {"error": f"nmap fallback error: {e}"}
    devs = []
    for line in r.stdout.splitlines():
        if line.startswith("Host:") and "Status: Up" in line:
            parts = line.split()
            if len(parts) > 1:
                devs.append({"ip": parts[1], "mac": None,
                             "hostname": _resolve(parts[1])})
    return {"subnet": subnet, "devices": _sort(devs), "count": len(devs)}


def scan_network(subnet=None):
    subnet = subnet or get_local_subnet()
    if SCAPY_OK:
        try:
            return _scapy_scan(subnet)
        except Exception:
            pass
    return _nmap_scan(subnet)
