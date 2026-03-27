#!/usr/bin/env python3
"""
Infrastructure Monitor - Checks PM2 and ports, alerts via Telegram if issues found.
Run via cron every 3 minutes.
"""

import subprocess
import json
import requests
from datetime import datetime

# Configuration
CHAT_ID = "5127607280"
BOT_TOKEN = "8297820489:AAEIIZZ5BReyN-HgCTfd-xzvd3hBOU-kxKs"

# Expected state
EXPECTED_PROCESSES = ["openclaw-gateway", "telegram-middleware"]
EXPECTED_PORTS = [443, 18789]  # middleware, gateway

# Known safe ports (don't alert for these)
KNOWN_SAFE_PORTS = [
    22,     # SSH
    443,    # Telegram middleware
    18789,  # OpenClaw gateway
    18790, 18791, 18792, 18793,  # OpenClaw additional ports
    25,     # SMTP (if mail server)
    53,     # DNS
    80,     # HTTP (if web server)
    3306,   # MySQL (if database)
    5432,   # PostgreSQL (if database)
    6379,   # Redis (if cache)
]

def get_pm2_status():
    """Get PM2 process status."""
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except:
        return []

def get_listening_ports_with_process():
    """Get list of listening ports with process info."""
    try:
        result = subprocess.run(
            ["ss", "-tulpn"],
            capture_output=True,
            text=True,
            timeout=10
        )
        ports_info = []
        for line in result.stdout.split('\n'):
            if 'LISTEN' in line:
                parts = line.split()
                port = None
                process = "unknown"

                # Extract port
                for part in parts:
                    if ':' in part:
                        try:
                            port = int(part.split(':')[-1])
                            break
                        except ValueError:
                            pass

                # Extract process name from users:(("name",pid=xxx))
                for part in parts:
                    if 'users:' in part:
                        try:
                            process = part.split('"')[1]
                        except:
                            pass

                if port and port not in [p['port'] for p in ports_info]:
                    ports_info.append({'port': port, 'process': process})

        return ports_info
    except:
        return []

def send_telegram_alert(message):
    """Send alert to Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def check_webhook_health():
    """Check if Telegram webhook is actually reachable."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {"error": f"API returned {resp.status_code}"}

        data = resp.json().get("result", {})
        issues = []

        # Check for recent errors
        last_error = data.get("last_error_message")
        last_error_date = data.get("last_error_date", 0)

        # If error in last 5 minutes
        import time
        if last_error and (time.time() - last_error_date) < 300:
            issues.append(f"Webhook error: {last_error}")

        # Check pending updates (messages stuck)
        pending = data.get("pending_update_count", 0)
        if pending > 10:
            issues.append(f"Stuck messages: {pending} pending")

        # Check URL is correct
        webhook_url = data.get("url", "")
        if "161.97.83.88" not in webhook_url:
            issues.append(f"Wrong webhook URL: {webhook_url}")

        return {"issues": issues}
    except Exception as e:
        return {"error": str(e)}


def check_ufw_rules():
    """Check if critical ports are allowed in UFW."""
    try:
        result = subprocess.run(
            ["ufw", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout
        issues = []

        # Check if UFW is active
        if "inactive" in output.lower():
            return {"issues": []}  # UFW off = all ports open, OK

        # Check critical ports
        if "443" not in output:
            issues.append("Port 443 NOT in UFW rules!")
        if "22" not in output:
            issues.append("Port 22 NOT in UFW rules (SSH)!")

        return {"issues": issues}
    except:
        return {"issues": []}


def check_ssl_certificate():
    """Check if SSL certificate exists and is not expired."""
    import os
    from datetime import datetime

    CERT_PATH = "/root/.openclaw/telegram_cert.pem"
    KEY_PATH = "/root/.openclaw/telegram_key.pem"
    issues = []

    # Check files exist
    if not os.path.exists(CERT_PATH):
        issues.append(f"SSL cert MISSING: {CERT_PATH}")
        return {"issues": issues}

    if not os.path.exists(KEY_PATH):
        issues.append(f"SSL key MISSING: {KEY_PATH}")
        return {"issues": issues}

    # Check cert expiry using openssl
    try:
        result = subprocess.run(
            ["openssl", "x509", "-enddate", "-noout", "-in", CERT_PATH],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Parse: notAfter=Mar 21 12:00:00 2027 GMT
            date_str = result.stdout.strip().replace("notAfter=", "")
            # Simple check: if "202" in output but year < current, expired
            import re
            year_match = re.search(r'20\d{2}', date_str)
            if year_match:
                cert_year = int(year_match.group())
                if cert_year < datetime.now().year:
                    issues.append(f"SSL cert EXPIRED: {date_str}")
                elif cert_year == datetime.now().year:
                    # Check month more carefully - warn if expires within 30 days
                    issues.append(f"SSL cert expires soon: {date_str}")
    except:
        pass

    return {"issues": issues}


def check_required_scripts():
    """Check if required Python scripts exist."""
    import os
    issues = []

    SCRIPTS = [
        "/root/.openclaw/workspace/skills/calendar/scripts/simple_quiz.py",
        "/root/.openclaw/workspace/skills/contact/scripts/contact_quiz.py",
        "/root/.openclaw/workspace/telegram_middleware.py",
    ]

    for script in SCRIPTS:
        if not os.path.exists(script):
            issues.append(f"Script MISSING: {script.split('/')[-1]}")

    return {"issues": issues}


def check_bot_token():
    """Check if bot token is valid by calling getMe."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return {"issues": [f"Bot token invalid: HTTP {resp.status_code}"]}

        data = resp.json()
        if not data.get("ok"):
            return {"issues": ["Bot token invalid: API returned not ok"]}

        return {"issues": []}
    except Exception as e:
        return {"issues": [f"Bot token check failed: {e}"]}


def check_disk_space():
    """Check if disk has enough free space."""
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Parse output: Filesystem Size Used Avail Use% Mounted
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                use_percent = int(parts[4].replace('%', ''))
                if use_percent > 90:
                    return {"issues": [f"Disk {use_percent}% full!"]}
                elif use_percent > 80:
                    return {"issues": [f"Disk warning: {use_percent}% used"]}
        return {"issues": []}
    except:
        return {"issues": []}


def check_infrastructure():
    """Check infrastructure and return issues."""
    issues = {
        "pm2": [],
        "ports_missing": [],
        "ports_unknown": [],
        "webhook": [],
        "ufw": [],
        "ssl": [],
        "scripts": [],
        "bot": [],
        "disk": []
    }

    # Check PM2 processes
    pm2_data = get_pm2_status()
    running_names = {p.get("name"): p.get("pm2_env", {}).get("status", "unknown") for p in pm2_data}

    for expected in EXPECTED_PROCESSES:
        if expected not in running_names:
            issues["pm2"].append(f"{expected}: NOT FOUND")
        elif running_names[expected] != "online":
            issues["pm2"].append(f"{expected}: {running_names[expected]}")

    # Check ports
    ports_info = get_listening_ports_with_process()
    listening_ports = [p['port'] for p in ports_info]

    # Check expected ports are listening
    for port in EXPECTED_PORTS:
        if port not in listening_ports:
            issues["ports_missing"].append(f"Port {port}: NOT listening")

    # Check for unknown ports
    for p in ports_info:
        if p['port'] not in KNOWN_SAFE_PORTS:
            issues["ports_unknown"].append(f"Port {p['port']} ({p['process']})")

    # Check webhook health (asks Telegram if it can reach us)
    webhook_result = check_webhook_health()
    if "error" in webhook_result:
        issues["webhook"].append(f"Webhook check failed: {webhook_result['error']}")
    else:
        issues["webhook"].extend(webhook_result.get("issues", []))

    # Check UFW rules
    ufw_result = check_ufw_rules()
    issues["ufw"].extend(ufw_result.get("issues", []))

    # Check SSL certificate
    ssl_result = check_ssl_certificate()
    issues["ssl"].extend(ssl_result.get("issues", []))

    # Check required scripts exist
    scripts_result = check_required_scripts()
    issues["scripts"].extend(scripts_result.get("issues", []))

    # Check bot token is valid
    bot_result = check_bot_token()
    issues["bot"].extend(bot_result.get("issues", []))

    # Check disk space
    disk_result = check_disk_space()
    issues["disk"].extend(disk_result.get("issues", []))

    return issues

def main():
    issues = check_infrastructure()

    has_issues = any([
        issues["pm2"], issues["ports_missing"], issues["ports_unknown"],
        issues["webhook"], issues["ufw"], issues["ssl"],
        issues["scripts"], issues["bot"], issues["disk"]
    ])

    if has_issues:
        msg = "⚠️ *INFRASTRUCTURE ALERT*\n\n"

        # Critical issues first
        if issues["webhook"]:
            msg += "*🚨 WEBHOOK BLOCKED:*\n"
            for issue in issues["webhook"]:
                msg += f"• {issue}\n"
            msg += "\n"

        if issues["ufw"]:
            msg += "*🔥 FIREWALL:*\n"
            for issue in issues["ufw"]:
                msg += f"• {issue}\n"
            msg += "Fix: `ufw allow 443 && ufw allow 22`\n\n"

        if issues["ssl"]:
            msg += "*🔐 SSL CERTIFICATE:*\n"
            for issue in issues["ssl"]:
                msg += f"• {issue}\n"
            msg += "\n"

        if issues["bot"]:
            msg += "*🤖 BOT TOKEN:*\n"
            for issue in issues["bot"]:
                msg += f"• {issue}\n"
            msg += "\n"

        if issues["scripts"]:
            msg += "*📜 SCRIPTS MISSING:*\n"
            for issue in issues["scripts"]:
                msg += f"• {issue}\n"
            msg += "\n"

        if issues["disk"]:
            msg += "*💾 DISK:*\n"
            for issue in issues["disk"]:
                msg += f"• {issue}\n"
            msg += "\n"

        if issues["pm2"]:
            msg += "*PM2:*\n"
            for issue in issues["pm2"]:
                msg += f"• {issue}\n"
            msg += "\n"

        if issues["ports_missing"]:
            msg += "*Missing Ports:*\n"
            for issue in issues["ports_missing"]:
                msg += f"• {issue}\n"
            msg += "\n"

        if issues["ports_unknown"]:
            msg += "*Unknown Ports:*\n"
            for issue in issues["ports_unknown"]:
                msg += f"• {issue}\n"
            msg += "\n"

        msg += f"_Time: {datetime.now().strftime('%H:%M:%S')}_"

        send_telegram_alert(msg)
        print(f"[{datetime.now()}] ALERT sent: {issues}")
    else:
        print(f"[{datetime.now()}] OK - All systems healthy")

if __name__ == "__main__":
    main()
