import json
import os
import platform
import psutil
import subprocess
import secrets
import sys
import socket
import time
import datetime # For current_year context processor

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sock import Sock
import bcrypt
import gevent.monkey
# from simple_websocket.errors import ConnectionClosed as SimpleWebSocketConnectionClosed # Only if using WebSockets directly
# import gevent.timeout # Only if using WebSockets directly

# Patch standard libraries for async I/O with gevent
try:
    gevent.monkey.patch_all()
    print("gevent monkey patching applied.")
except Exception as e:
    print(f"Error applying gevent monkey patch: {e}.")

# --- Configuration ---
CONFIG_FILE = 'config.json'
config = {}
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print(f"Error: Configuration file '{CONFIG_FILE}' not found or invalid.")
    print("Please run 'python setup.py' first.")
    sys.exit(1)

APP_SECRET_KEY = secrets.token_hex(16)
PASSWORD_HASH = config.get('password_hash')
LISTEN_PORT = config.get('port', 417)
SESSION_TIMEOUT = 3600 # Session timeout in seconds (1 hour)

if not PASSWORD_HASH:
     print(f"Error: 'password_hash' not found in '{CONFIG_FILE}'. Please run 'python setup.py'.")
     sys.exit(1)

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = APP_SECRET_KEY
sock = Sock(app) # Initialize Sock for potential future use

# Set session timeout
app.permanent_session_lifetime = SESSION_TIMEOUT

# --- Context Processor for Current Year ---
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.datetime.now().year}

# --- Authentication Decorator ---
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            next_url = request.url
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login', next=next_url))
        return f(*args, **kwargs)
    return decorated_function

# --- Utility Functions ---
def get_system_info():
     try: return {"os": {"name": platform.system(), "release": platform.release(), "version": platform.version(), "architecture": platform.machine(), "node_name": platform.node(), "uptime": get_system_uptime()}}
     except Exception as e: print(f"Error getting basic system info: {e}"); return {"os": {"error": f"Could not retrieve basic OS info: {e}"}}

def get_cpu_info():
    try:
        model_name = "Unknown"
        if platform.system() == "Linux":
            try:
                result = subprocess.run(['lscpu'], capture_output=True, text=True, check=True)
                for line in result.stdout.splitlines():
                    if line.strip().startswith("Model name:"):
                        model_name = line.split(':', 1)[1].strip()
                        break
            except Exception: pass
        return { "count": psutil.cpu_count(logical=False), "logical_count": psutil.cpu_count(logical=True), "usage_percent": psutil.cpu_percent(interval=0.5, percpu=True), "overall_usage_percent": psutil.cpu_percent(interval=0.5), "freq": psutil.cpu_freq().current if psutil.cpu_freq() else "N/A", "model": model_name } # Reduced interval for quicker response
    except Exception as e: print(f"Error getting CPU info: {e}"); return {"error": f"Could not retrieve CPU info: {e}", "overall_usage_percent":0} # Default for template

def get_memory_info():
    try: mem = psutil.virtual_memory(); swap = psutil.swap_memory(); return {"total_gb": round(mem.total / (1024**3), 2), "available_gb": round(mem.available / (1024**3), 2), "used_gb": round(mem.used / (1024**3), 2), "percent": mem.percent, "swap_total_gb": round(swap.total / (1024**3), 2), "swap_used_gb": round(swap.used / (1024**3), 2), "swap_percent": swap.percent}
    except Exception as e: print(f"Error getting memory info: {e}"); return {"error": f"Could not retrieve Memory info: {e}", "percent":0} # Default for template

def get_disk_info():
    partitions = []
    try:
        for part in psutil.disk_partitions():
            if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''): continue
            if os.path.exists(part.mountpoint):
                 try: usage = psutil.disk_usage(part.mountpoint); partitions.append({"device": part.device, "mountpoint": part.mountpoint, "fstype": part.fstype, "total_gb": round(usage.total / (1024**3), 2), "used_gb": round(usage.used / (1024**3), 2), "free_gb": round(usage.free / (1024**3), 2), "percent": usage.percent})
                 except Exception as usage_e: partitions.append({"device": part.device, "mountpoint": part.mountpoint, "fstype": part.fstype, "total_gb": "N/A", "used_gb": "N/A", "free_gb": "N/A", "percent": 0, "error": f"Could not get usage: {usage_e}"}) # Default percent
            else: partitions.append({"device": part.device, "mountpoint": part.mountpoint, "fstype": part.fstype, "total_gb": "N/A", "used_gb": "N/A", "free_gb": "N/A", "percent": 0, "error": "Mountpoint not accessible or does not exist"}) # Default percent
    except Exception as e: print(f"Error getting disk info: {e}"); partitions = [{"error": f"Failed to retrieve disk information: {e}", "percent":0}] # Default percent
    return partitions

def get_network_info():
    try:
        net_io = psutil.net_io_counters(); net_addrs = psutil.net_if_addrs(); interfaces = []
        for name, addrs in net_addrs.items():
             interface_info = {"name": name, "addresses": []}
             for addr in addrs:
                 if addr.family == socket.AF_PACKET: interface_info["addresses"].append({"family": "MAC", "address": addr.address})
                 elif addr.family == socket.AF_INET: interface_info["addresses"].append({"family": "IPv4", "address": addr.address, "netmask": addr.netmask, "broadcast": addr.broadcast})
                 elif addr.family == socket.AF_INET6: interface_info["addresses"].append({"family": "IPv6", "address": addr.address, "netmask": addr.netmask})
             interfaces.append(interface_info)
        overall_traffic = {"bytes_sent_gb": round(net_io.bytes_sent / (1024**3), 2), "bytes_recv_gb": round(net_io.bytes_recv / (1024**3), 2), "packets_sent": net_io.packets_sent, "packets_recv": net_io.packets_recv, "errin": net_io.errin, "errout": net_io.errout, "dropin": net_io.dropin, "dropout": net_io.dropout}
        return {"interfaces": interfaces, "overall_traffic": overall_traffic}
    except Exception as e: print(f"Error getting network info: {e}"); return {"error": f"Could not retrieve Network info: {e}"}

def get_system_uptime():
    try: boot_time = psutil.boot_time(); current_time = psutil.time.time(); uptime_seconds = current_time - boot_time; days, remainder = divmod(uptime_seconds, 86400); hours, remainder = divmod(remainder, 3600); minutes, seconds = divmod(remainder, 60); return f"{int(days)} days, {int(hours)} hours, {int(minutes)} minutes"
    except Exception: return "N/A"

def save_config():
    global config
    try:
        temp_config_file = CONFIG_FILE + ".tmp"
        with open(temp_config_file, 'w') as f: json.dump(config, f, indent=4)
        os.replace(temp_config_file, CONFIG_FILE)
        print(f"Configuration saved to {CONFIG_FILE}")
    except IOError as e: print(f"Error saving configuration file: {e}")

def get_server_ip_for_ssh():
    if request and request.host: return request.host.split(':')[0]
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(0.1)
        s.connect(('8.8.8.8', 80)); ip = s.getsockname()[0]; s.close(); return ip
    except Exception: return "your_server_ip"

# --- Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Prepare stats for login page regardless of POST/GET or errors,
    # ensuring defaults if data fetching fails.
    cpu_data = get_cpu_info()
    mem_data = get_memory_info()
    disk_data_list = get_disk_info()

    cpu_usage_percent = cpu_data.get('overall_usage_percent', 0) if isinstance(cpu_data, dict) else 0
    memory_usage_percent = mem_data.get('percent', 0) if isinstance(mem_data, dict) else 0
    
    root_disk_percent = 0
    if isinstance(disk_data_list, list):
        for disk_item in disk_data_list:
            if isinstance(disk_item, dict) and disk_item.get('mountpoint') == '/':
                root_disk_percent = disk_item.get('percent', 0)
                break
        if not root_disk_percent and disk_data_list and isinstance(disk_data_list[0], dict): # Fallback to first disk
            root_disk_percent = disk_data_list[0].get('percent', 0)

    template_vars = {
        'cpu_usage': cpu_usage_percent,
        'memory_usage': memory_usage_percent,
        'disk_usage': root_disk_percent
    }

    if 'authenticated' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        password_attempt = request.form.get('password')
        try:
            with open(CONFIG_FILE, 'r') as f: current_config_data = json.load(f)
            current_password_hash = current_config_data.get('password_hash')
            if not current_password_hash:
                flash('Panel not configured. Please run setup.py.', 'danger')
                return render_template('login.html', **template_vars)
        except Exception as e:
            print(f"Error loading config for login: {e}")
            flash('Error loading configuration.', 'danger')
            return render_template('login.html', **template_vars)

        if password_attempt and bcrypt.checkpw(password_attempt.encode('utf-8'), current_password_hash.encode('utf-8')):
            session['authenticated'] = True
            session.permanent = True
            flash('Login successful!', 'success')
            next_url = request.args.get('next')
            if next_url:
                from urllib.parse import urlparse
                if urlparse(next_url).netloc == '' or urlparse(next_url).netloc == request.host:
                    return redirect(next_url)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password. Please try again.', 'danger')
    
    # For GET request or if POST fails password check
    return render_template('login.html', **template_vars)


@app.route('/logout')
def logout(): session.pop('authenticated', None); flash('You have been logged out.', 'info'); return redirect(url_for('login'))
@app.route('/')
def index(): return redirect(url_for('login')) if 'authenticated' not in session else redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard(): system_overview = get_system_info(); return render_template('dashboard.html', system_overview=system_overview)
@app.route('/cpu')
@login_required
def cpu_info(): cpu_data = get_cpu_info(); return render_template('cpu.html', cpu_data=cpu_data)
@app.route('/memory')
@login_required
def memory_info(): mem_data = get_memory_info(); return render_template('memory.html', mem_data=mem_data)
@app.route('/disk')
@login_required
def disk_info(): disk_data = get_disk_info(); return render_template('disk.html', disk_data=disk_data)
@app.route('/network')
@login_required
def network_info(): network_data = get_network_info(); return render_template('network.html', network_data=network_data)

@app.route('/processes')
@login_required
def processes_info(): process_data = get_running_processes(); return render_template('processes.html', process_data=process_data)

@app.route('/system_logs')
@login_required
def system_logs_page():
    log_file_to_show = "/var/log/syslog"
    log_lines_data = get_system_log_tail(log_file_path=log_file_to_show, lines=200)
    return render_template('system_logs.html', log_lines=log_lines_data, log_file_name=f"Log ({os.path.basename(log_file_to_show)})")

@app.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password'); new_password = request.form.get('new_password'); confirm_password = request.form.get('confirm_password')
        try:
            with open(CONFIG_FILE, 'r') as f: current_config_on_disk = json.load(f)
            current_password_hash_on_disk = current_config_on_disk.get('password_hash')
            global config; config.update(current_config_on_disk)
            if not current_password_hash_on_disk: flash('Cannot change password, panel not configured.', 'danger'); return render_template('password.html')
        except Exception as e: print(f"Error loading config for password change: {e}"); flash('Error loading configuration.', 'danger'); return render_template('password.html')
        if not current_password or not bcrypt.checkpw(current_password.encode('utf-8'), current_password_hash_on_disk.encode('utf-8')): flash('Invalid current password.', 'danger')
        elif not new_password: flash('New password cannot be empty.', 'danger')
        elif len(new_password) < 8: flash('New password must be at least 8 characters.', 'danger')
        elif new_password != confirm_password: flash('New password and confirmation do not match.', 'danger')
        else: new_password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'); config['password_hash'] = new_password_hash; save_config(); flash('Password changed successfully!', 'success')
        return redirect(url_for('change_password'))
    return render_template('password.html')

@app.route('/console')
@login_required
def console(): server_ip = get_server_ip_for_ssh(); ssh_user = "root"; return render_template('console_ssh.html', server_ip=server_ip, ssh_user=ssh_user)

@app.route('/server_actions')
@login_required
def server_actions_page(): return render_template('server_actions.html')

@app.route('/actions/reboot', methods=['POST'])
@login_required
def reboot_server():
    try:
        print("Attempting to reboot server..."); reboot_command = '/sbin/reboot'
        if not os.path.exists(reboot_command): reboot_command = '/usr/sbin/reboot'
        result = subprocess.run(['sudo', reboot_command], capture_output=True, text=True, check=False)
        if result.returncode == 0: flash('Server reboot command issued!', 'success'); print("Reboot successful."); return jsonify({"message": "Reboot command sent."}), 200
        else: error_message = result.stderr.strip() or result.stdout.strip() or "Unknown error"; flash(f'Reboot failed: {error_message}', 'danger'); print(f"Reboot failed: {error_message}"); return jsonify({"message": f"Reboot failed: {error_message}"}), 500
    except Exception as e: flash(f'Exception during reboot: {str(e)}', 'danger'); print(f"Exception during reboot: {e}"); return jsonify({"message": f"Exception: {str(e)}"}), 500

@app.route('/actions/stop', methods=['POST'])
@login_required
def stop_server():
    try:
        print("Attempting to stop server..."); shutdown_command = '/sbin/shutdown'
        if not os.path.exists(shutdown_command): shutdown_command = '/usr/sbin/shutdown'
        result = subprocess.run(['sudo', shutdown_command, '-h', 'now'], capture_output=True, text=True, check=False)
        if result.returncode == 0: flash('Server shutdown command issued!', 'success'); print("Shutdown successful."); return jsonify({"message": "Shutdown command sent."}), 200
        else: error_message = result.stderr.strip() or result.stdout.strip() or "Unknown error"; flash(f'Shutdown failed: {error_message}', 'danger'); print(f"Shutdown failed: {error_message}"); return jsonify({"message": f"Shutdown failed: {error_message}"}), 500
    except Exception as e: flash(f'Exception during shutdown: {str(e)}', 'danger'); print(f"Exception during shutdown: {e}"); return jsonify({"message": f"Exception: {str(e)}"}), 500

# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e): return render_template('404.html'), 404

# --- Run the app ---
if __name__ == '__main__':
    from gevent.pywsgi import WSGIServer
    from geventwebsocket.handler import WebSocketHandler
    print(f"Starting Void Nodes Server Panel on http://0.0.0.0:{LISTEN_PORT}"); print("Press Ctrl+C to stop.")
    try:
        http_server = WSGIServer(('0.0.0.0', LISTEN_PORT), app, handler_class=WebSocketHandler)
        print(f"gevent WSGIServer listening on port {LISTEN_PORT}...")
        http_server.serve_forever()
    except KeyboardInterrupt: print("\nShutting down...")
    except Exception as e: print(f"Failed to start server: {e}"); sys.exit(1)
