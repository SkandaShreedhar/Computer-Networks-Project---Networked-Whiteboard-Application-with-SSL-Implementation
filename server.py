import socket  # Import socket module for network communication
import threading  # Import threading module for concurrent execution
import time  # Import time module for managing time-related operations
import ssl  # Import SSL module for secure communication

HOST = '127.0.0.1'  # Define host IP address
PORT = 5050  # Define port number for the server
INACTIVITY_TIMEOUT = 30  # Define inactivity timeout for server shutdown

# Sample username and password for demonstration purposes
VALID_USERNAME = "user"
VALID_PASSWORD = "password"

# SSL context setup using certificate and private key
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
if(context):
    print("SSL is established")
context.load_cert_chain('ssl.pem', 'private.key')

# Establish a socket connection and bind it to the host and port
with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
    sock.bind((HOST, PORT))  # Bind socket to host and port
    print("Server is ready......!")  # Print message indicating server readiness
    sock.listen(3)  # Listen for incoming connections with a maximum of 3 connections
    with context.wrap_socket(sock, server_side=True) as ssock:  # Wrap socket with SSL context
        conn, addr = ssock.accept()  # Accept incoming connection
        print(f"Server is connected to {addr}")  # Print connected client address
        
        # Receive username and password for authentication
        credentials = conn.recv(1024).decode().split(',')  # Receive and decode credentials
        username = credentials[0]  # Extract username
        password = credentials[1]  # Extract password
        
        # Authenticate username and password
        if username == VALID_USERNAME and password == VALID_PASSWORD:  # Check if credentials are valid
            conn.sendall(b"Authenticated")  # Send authentication success message
        else:
            conn.sendall(b"Authentication failed")  # Send authentication failure message
            conn.close()  # Close connection
            exit()  # Exit program
        
        conn.sendall(bytes("Welcome to the server!", 'utf-8'))  # Send welcome message to client
        ssock.close()  # Close SSL socket

# Create a new socket for server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the server socket to the host and port
server.bind((HOST, PORT))

clients = []  # List to hold connected clients
clients_lock = threading.Lock()  # Lock for thread safety when accessing clients list

server_active = True  # Flag to indicate server activity

# Function to handle individual client connections
def handle_client(client, address):
    global server_active  # Access global server_active flag
    while server_active:
        try:
            data = client.recv(10240).decode()  # Receive data from client
            if not data:  # Check if no data is received
                break  # Break the loop if no data is received
            with clients_lock:  # Acquire lock for thread safety
                for c in clients:  # Iterate through connected clients
                    c.sendall(data.encode())  # Send data to each client
        except ConnectionResetError:  # Handle connection reset error
            break  # Break the loop on connection reset error
        except Exception as e:  # Handle other exceptions
            print(f"Error handling client {address}: {e}")  # Print error message
            break  # Break the loop on other exceptions

    with clients_lock:  # Acquire lock for thread safety
        if client in clients:  # Check if client is in the clients list
            clients.remove(client)  # Remove client from the list
    print(f"Client {address} disconnected.")  # Print message indicating client disconnection
    client.close()  # Close client connection

# Function to start the server
def start_server():
    global server_active  # Access global server_active flag
    server.listen()  # Start listening for connections
    print(f'Server is listening on {HOST}:{PORT}')  # Print message indicating server listening status

    while server_active:  # Continue running while server is active
        try:
            server.settimeout(1)  # Set a timeout for the accept call
            client, address = server.accept()  # Accept incoming connection
            server.settimeout(None)  # Disable the timeout after the connection is accepted
            print(f'Connection established with {address}')  # Print message indicating connection establishment
            with clients_lock:  # Acquire lock for thread safety
                clients.append(client)  # Add client to the clients list
            thread = threading.Thread(target=handle_client, args=(client, address), daemon=True)  # Create a new thread for client handling
            thread.start()  # Start the client handling thread
        except socket.timeout:  # Handle timeout exception
            pass  # Continue accepting connections if timeout occurs
        except Exception as e:  # Handle other exceptions
            if server_active:  # Check if server is still active
                print(f"Error accepting connection: {e}")  # Print error message
            break  # Break the loop on other exceptions
    server.close()  # Close the server socket

# Function to monitor client activity and shutdown server if no activity is detected
def monitor_activity():
    global server_active  # Access global server_active flag
    global clients  # Access global clients list
    while server_active:  # Continue running while server is active
        time.sleep(INACTIVITY_TIMEOUT)  # Sleep for specified inactivity timeout
        with clients_lock:  # Acquire lock for thread safety
            if not clients:  # Check if no clients are connected
                print(f"No clients connected for {INACTIVITY_TIMEOUT} seconds. Shutting down server.")  # Print message 
                # indicating server shutdown due to inactivity
                server_active = False  # Set server_active flag to False
                exit()  # Exit the program

# Create and start server and activity monitoring threads
server_thread = threading.Thread(target=start_server, daemon=True)
activity_thread = threading.Thread(target=monitor_activity, daemon=True)

server_thread.start()  # Start the server thread
activity_thread.start()  # Start the activity monitoring thread

server_thread.join()  # Wait for server thread to finish
activity_thread.join()  # Wait for activity monitoring thread to finish
