# Import necessary libraries
import socket
from tkinter import *
from tkinter.colorchooser import askcolor
from tkinter import ttk
import tkinter as tk
import threading
import os
import sys
import ssl
import optparse

import math

# Set default host and port
HOST = 'localhost'
PORT = 5050

# Set up command-line argument parser
parser = optparse.OptionParser('usage%prog' + '-d <domain>' + '-p <port>')
parser.add_option('-d', dest='domain', type='string', help='specify the method')
parser.add_option('-p', dest='port', type='string', help='specify the url')

# Parse command-line arguments
(options, args) = parser.parse_args()
domain = str(options.domain)
port = int(options.port)

# Function to get secret message
def get_secret_message(username, password):
    # Create SSL context and load certificate
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations('ssl.pem')
    
    # Create a socket and wrap it with SSL
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    c_soc = context.wrap_socket(soc, server_hostname=domain)
    
    # Connect to the server
    c_soc.connect((domain, port))
    print("Connection successful...")
    
    # Send username and password for authentication
    credentials = f"{username},{password}"
    c_soc.sendall(credentials.encode())
    
    # Receive authentication response from the server
    response = c_soc.recv(1024).decode("utf-8")
    print(response)
    
    if response == "Authenticated":
        # Proceed with your application logic after successful authentication
        print("Authentication successful.")
    else:
        print("Authentication failed.")
        sys.exit(1)

    # Close the socket
    c_soc.close()

# Main function
if __name__ == "__main__":
    # Get username and password from user
    username = input("Enter your username: ")
    password = input("Enter your password: ")
    
    # Call function to get secret message
    get_secret_message(username, password)

    # Create a socket for communication with the server
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Connect to the server
        client.connect((HOST, PORT))
    except ConnectionRefusedError:
        print("Server is not active. Cannot Connect.")
        sys.exit(1)

    # Initialize Tkinter window
    root = Tk()
    root.title("Collaborative Whiteboard")
    root.geometry("810x530+150+50")
    root.configure(bg="#f2f3f5")
    root.resizable(False, False)
    start_x = None
    start_y = None
    color = 'black'
    lines = []
    removed_lines = []
    brush_thickness = 2

    # Function to send coordinates of drawing
    def send_coords(event):
        try:
            global start_x, start_y, color, brush_thickness
            x, y = event.x, event.y
            if start_x is not None and start_y is not None:
                coords_color_thickness = f'{start_x},{start_y},{x},{y},{color},{brush_thickness}'
                message = f"{len(coords_color_thickness):<1024}" + coords_color_thickness
                client.sendall(message.encode())
                start_x, start_y = x, y
                lines.append(canvas.create_line(start_x, start_y, x, y, width=brush_thickness, fill=color,capstyle=ROUND,smooth=TRUE))
        except ConnectionResetError as e:
            print(f"Connection reset by server: {e}")
        except Exception as e:
            print(f"Error sending coordinates: {e}")

    # Function to receive messages from server
    def receive_messages():
        while True:
            try:
                length_prefix = client.recv(1024).decode().strip()
                if length_prefix == 'CLEAR' or length_prefix == 'UNDO' or length_prefix == 'REDO':
                    handle_special_command(length_prefix)
                else:
                    message_length = int(length_prefix)
                    data = client.recv(message_length).decode()
                    handle_drawing_command(data)
            except ConnectionResetError as e:
                print("Server is not active. Exiting client.")
                os._exit(1)
            except Exception as e:
                print(f"Error receiving message: {e}")
                os._exit(1)

    # Function to handle drawing commands received from server
    def handle_drawing_command(data):
        try:
            coords_color_thickness = data.split(',')
            x1, y1, x2, y2 = map(int, coords_color_thickness[:4])
            received_color = coords_color_thickness[4]
            received_thickness = int(coords_color_thickness[5])
            line_id = canvas.create_line(x1, y1, x2, y2, width=received_thickness, fill=received_color, capstyle=ROUND, smooth=TRUE)
            lines.append(line_id)
        except Exception as e:
            print(f"Error handling drawing command: {e}")

    # Function to handle special commands like CLEAR, UNDO, REDO
    def handle_special_command(command):
        try:
            if command == 'CLEAR':
                canvas.delete('all')
                lines.clear()
                display_palette()
            elif command == 'UNDO':
                if lines:
                    last_item = lines.pop()
                    line_coords = canvas.coords(last_item)
                    line_color = canvas.itemcget(last_item, "fill")
                    line_thickness = canvas.itemcget(last_item, "width")
                    removed_lines.append((last_item, line_coords, line_color, line_thickness))
                    canvas.delete(last_item)
            elif command == 'REDO':
                if removed_lines:
                    line_to_restore = removed_lines.pop()
                    new_line_id = canvas.create_line(line_to_restore[1], width=line_to_restore[3], fill=line_to_restore[2], capstyle=ROUND)
                    lines.append(new_line_id)
            
        except Exception as e:
            print(f"Error handling special command: {e}")

    # Function to start drawing
    def start_draw(event):
        global start_x, start_y
        start_x, start_y = event.x, event.y

    # Function to stop drawing
    def stop_draw(event):
        global start_x, start_y
        start_x, start_y = None, None

    # Function to change color
    def show_color(new_color):
        global color
        color = new_color

    # Function to clear canvas
    def clear_canvas():
        canvas.delete('all')
        lines.clear()
        display_palette()
        client.sendall(b'CLEAR')

    # Function to undo last action
    def undo():
        if lines:
            last_item = lines.pop()
            line_coords = canvas.coords(last_item)
            line_color = canvas.itemcget(last_item, "fill")
            line_thickness = canvas.itemcget(last_item, "width")
            removed_lines.append((last_item, line_coords, line_color, line_thickness))
            canvas.delete(last_item)
            client.sendall(b'UNDO')

    # Function to redo last action
    def redo():
        if removed_lines:
            line_to_restore = removed_lines.pop()
            new_line_id = canvas.create_line(line_to_restore[1], width=line_to_restore[3], fill=line_to_restore[2], capstyle=ROUND)
            lines.append(new_line_id)
            client.sendall(b'REDO')

    # Function to open color picker dialog
    def open_color_picker():
        global color
        new_color = askcolor()[1]
        if new_color:
            color = new_color
            
    # Create a canvas to display color palette
    colors=Canvas(root, bg="#ffffff", width=40, height=340, bd=0)
    colors.place(x=30, y=10)

    # Function to display color palette
    def display_palette():
        colors_list = ['black', 'grey', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink','white']
        for i, color in enumerate(colors_list):
            id = colors.create_rectangle((12, 10 + i * 30, 32, 30 + i * 30), fill=color)
            colors.tag_bind(id, '<Button-1>', lambda x, color=color: show_color(color))

    # Function to get current brush thickness
    def get_current_value():
        return '{: .2f}'.format(current_value.get())

    # Function to update brush thickness
    def update_brush_thickness(value):
        global brush_thickness
        brush_thickness = round(float(value))

    # Create buttons for various actions
    Button(root, text="Choose Color", bg="#f2f3f5", command=open_color_picker).place(x=10, y=360)
    Button(root, text="Undo", bg="#f2f3f5", command=undo).place(x=5, y=400)
    Button(root, text="Redo", bg="#f2f3f5", command=redo).place(x=55, y=400)
    Button(root, text="Clear", bg="#f2f3f5", command=clear_canvas).place(x=30, y=440)

    # Create canvas for drawing
    canvas = Canvas(root, width=700, height=510, background="white", cursor="cross")
    canvas.place(x=100, y=10)
    canvas.bind('<Button-1>', start_draw)
    canvas.bind('<B1-Motion>', send_coords)
    canvas.bind('<ButtonRelease-1>', stop_draw)
    display_palette()

    # Create slider for brush thickness
    current_value=tk.DoubleVar()
    slider = ttk.Scale(root, from_=0, to=100, orient='horizontal', variable=current_value, command=update_brush_thickness)
    slider.place(x=1, y=480)
    value_label = ttk.Label(root, text=get_current_value())
    value_label.place(x=15, y=500)

    # Function to handle window closing event
    def on_closing():
        root.destroy()  # Destroy the Tkinter window
        print("Client disconnecting.")
        client.close()  # Close the socket connection
        os._exit(0)     # Terminate the entire client process

    # Set up window closing event handler
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start a thread to receive messages from server
    receive_thread = threading.Thread(target=receive_messages, daemon=True)
    receive_thread.start()

    # Start the Tkinter event loop
    root.mainloop()