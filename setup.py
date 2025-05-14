import json
import os
import bcrypt

CONFIG_FILE = 'config.json'
DEFAULT_PORT = 417

def generate_hashed_password(password):
    """Hashes a password using bcrypt."""
    # bcrypt salts automatically
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def setup():
    print("--- Void Nodes Server Panel Setup ---")
    print("This will configure the panel settings.")

    # Ask for password
    while True:
        password = input("Enter a password for the panel: ")
        if not password:
            print("Password cannot be empty. Please try again.")
        else:
            break

    hashed_password = generate_hashed_password(password)

    # Ask for port (optional, default is 417)
    try:
        port_input = input(f"Enter port for the panel (default: {DEFAULT_PORT}): ")
        port = int(port_input) if port_input else DEFAULT_PORT
    except ValueError:
        print(f"Invalid port number. Using default port: {DEFAULT_PORT}")
        port = DEFAULT_PORT

    config = {
        'password_hash': hashed_password,
        'port': port
    }

    # Save configuration
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuration saved to {CONFIG_FILE}")
        print(f"Panel password hash generated.")
        print(f"Panel will run on port {port}")
    except IOError as e:
        print(f"Error saving configuration file: {e}")
        print("Setup failed.")
        return

    print("\nSetup complete!")
    print("You can now run the panel using: python app.py")
    print(f"Access it via your server's IP address on port {port} (e.g., http://your_server_ip:{port})")
    print("\nRemember to open the specified port in your firewall if necessary.")

if __name__ == "__main__":
    if os.path.exists(CONFIG_FILE):
        print(f"Configuration file '{CONFIG_FILE}' already exists.")
        overwrite = input("Overwrite existing configuration? (y/N): ").lower()
        if overwrite != 'y':
            print("Setup aborted.")
            exit()

    setup()
