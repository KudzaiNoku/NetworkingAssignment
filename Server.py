
"""
Server.py - A Python program that represents a simple server

Author[s]: Hannah Mahachi, Somelele Quse, Kudzaishe Nyika
Date: 04 March 2024
"""
# server that accepts multiple clients
from socket import *
import sys
import threading
import time  # may be used to create delays between messages, to reduce network load
import struct

visibilityOptions = { #the two options that a person can be
    0: "private",
    1: "public"
}

Message_type = { # used to decipher what kind of response to give
    0: "COMMAND",  # anything in the command list
    1: "MESSAGE",  # any string
    2: "REGULAR DATA TRANSFER",  # for requesting re-entry
    3: "REQUEST DENIED",  # denying request
    4: "CONNECTION REQUEST" # the server is notifying this client that another client wants to talk to them
}
COMMANDS = ["LIST_CLIENTS", "VISIBILITY", "CONNECT_TO", "TERMINATE",""] #list of commands a client can choose from

serverID = "Server" # The server''s "user_ID"
connected_clients = []  # where all the clients will be listed
user_IDs = []
threads = []
lock = threading.Lock()


def serialize(message_type, user_id, message):
    """
    Encodes messages so that they are received in a certain order. The order imitates the protocol header.
    
    :param message_type: The type of message needing to be sent
    :type message_type: str
    :param user_id: The user_ID of sender
    :type user_id: str
    :param message: The actual message needing to be sent
    :type message: str
    :rtype: bytes
    
    """
    byte_message = f"{message_type},{user_id},{message}"
    # print(byte_message)
    return byte_message.encode('utf-8')


def deserialize(data):
    """
    Decodes data and returns the parts of the data in the correct order. 
    
    :param data: the data needing to be decoded
    :type data: bytes 
    :rtype: tuple of str
    
    """    
    decoded_data = data.decode('utf-8')
    segments = decoded_data.split(',')
    message_type = segments[0]
    user_id = segments[1]
    message = segments[2]
    return message_type, user_id, message


def server_on():
    """
    Switches the server on.
    :rtype: None
    
    """       
    global serverSocket
    if len(sys.argv) != 3:
	    print("Usage: python script.py <host> <port>")
	    return

    host, port = sys.argv[1], int(sys.argv[2])
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind((host, port))  # ready to hear from whoever
    serverSocket.listen()
    print('Listening from ' + str(host) + " " + str(port))

def username_generator(userID, userIDs):
    """
    Generates username for each client, to ensure there are no duplicates stored in user_ID[] list.
    :param userID: the userID initially given by client
    :type userID: str
    :param userIDs: the userID list used by the server
    :type userIDS: list
    :rtype: str
    
    """       
    # takes care of duplicate user IDs
    if userID not in userIDs:
        return userID  # user_ID is unique
    else:
        count = 1
        new_ID = userID + "_" + str(count)

        while new_ID in userIDs:
            count += 1
            new_ID = userID + "_" + str(count)

        return new_ID


def accepting_connections():
    """
    Accepts client connections.
    :rtype: None
    
    """       
    threads = []  # List to store threads

    # once the server starts again, get rid of all the connections and things
    if connected_clients:
        with lock:  # thread safety
            for x, conn in connected_clients:
                conn.close()
            connected_clients.clear()

    # listen for new connections
    while True:
        connection, addr = serverSocket.accept()
        message_type, user_id, visibility = deserialize(connection.recv(2048))

        with lock:
            connected_clients.append(((connection, addr), visibility))

        # Take care of duplicate usernames
        new_userID = username_generator(user_id, user_IDs)
        user_IDs.append(new_userID)

        print("\nUser: " + new_userID + " has joined the chatroom!\nAddress: " + str(addr) + "\nVisibility Status:" + visibility+"\n")

        # Start thread to handle client and store it in the list
        thread = threading.Thread(target=handle_client_commands, args=(connection, addr, new_userID))
        thread.start()
        threads.append(thread)

    # make sure all threads to finish
    for thread in threads:
        thread.join()


def list_connections():
    """
    Lists public clients.
    :rtype: None
    
    """       
    # for listing all connections without checking if they're still connected - this works faster
    list_str = "-------LIST OF AVAILABLE CLIENTS-------\n"
    count = 0
    for i, ((conn, client_addr), visibility) in enumerate(connected_clients):
        if visibility == "1":
            count += 1
            list_str += str(count) + ". " + user_IDs[i] + "\n"
    return list_str



def change_client_visibility(user_id, new_visibility):  # it has to be the number 1 or 0
    """
    Changes client visibility.
    :param userID: the userID of the client whose visibility is going to change
    :type userID: str
    :param new_visibility: the visibility to change the current visibility to
    :type new_visibility: int
    :rtype: None
    
    """       
    print(user_id + " is changing visibility")
    for i, (((conn, client_addr), visibility)) in enumerate(connected_clients):
        if user_IDs[i] == user_id:
            with lock:
                connected_clients[i] = ((conn, client_addr), str(new_visibility))
		# debug
                print(((conn, client_addr), str(new_visibility)))
		# debug
            break
    print("User: " + user_id + " --> Visibility updated to: " + visibilityOptions[new_visibility])


def connect_clients(requestor_id, requested_id):
    """
    Coordinates communication between two clients that may potentially communicate with each other.
    :param requestor_id: the userID of the client requesting to speak to someone
    :type requestor_id: str
    :param requested_id: the userID of the client being requested for a chat
    :type requested_id: str
    :rtype: None
    
    """           
    # Debug
    print("REQUEST RECEIVED")
    # Debug
    # get info of requestor client and requested client
    requestor_socket, requestor_address, requestor_index = get_user_info(requestor_id)
    requested_socket, requested_address, requested_index = get_user_info(requested_id)
   
    # put while-loop so the server is constantly listening
    try:
        message = requestor_id + " wants to speak to you. Type 'Y' to accept, and 'N' to deny."
        requested_socket.sendall(serialize(4, serverID, message))    
        message_type, user_id, response = deserialize(requested_socket.recv(2048))
        if str(response).strip() == "Y":
            # THREAD SAFETY!!! one thread must access connected_clients at a time
            with lock:
                connected_clients[requestor_index] = (connected_clients[requestor_index][0], "0")
                connected_clients[requested_index] = (connected_clients[requested_index][0], "0")
            # send message that the user wants to speak to them
            print("SENDING USER INFO TO USERS")
            
            message = requestor_id + "'s address: " + requestor_address
            # Debug
            print(message)
            # Debug
            requested_socket.sendall(serialize(1, serverID, message))
    
            message = requested_id + "'s address: " + requested_address
            # Debug
            print(message)
            # Debug
            requestor_socket.sendall(serialize(1, serverID, message))
            # stay ready to receive something from the requestor when chat terminates
            print("SENT USER INFO TO USERS")    
        elif str(response).strip() == "N":
            # if the requested denies, tell requestor "USER:" + requestedID + "does not want to speak to you!"
            message = "USER:" + requested_id + " does not want to speak to you!\nPlease view the list of other available clients:\n" + list_connections()
            requestor_socket.sendall(serialize(3, serverID, message))	
    except:
        print("error in communicating with clients.")
        return
    print("RESPONSE FROM REQUESTED IS: " + response)


    # If the requested accepts, change both visibilities to 0 (private),
    # send address info to each, initiate chat


def get_user_info(user_id):
    """
    Gets the index, connection and address of client using their userID.
    :param user_id: The userID of a client
    :type user_id: str
    :rtype: tuple[str,str,int]
    """
    # get user information from user_ID
    user_index = 0
    user_socket = ""
    user_address = ""
    for i, ((conn, client_addr), visibility) in enumerate(connected_clients):
        if user_IDs[i] == user_id:
            user_socket = conn
            user_address = client_addr
            user_index = i
            break
    return user_socket, user_address, user_index


def handle_client_commands(connection, addr, user_id):
    """
    Listens for commands, and ensures that they are handled accordingly, and ensures the graceful disconnection of clients.
    :param connection: The client socket
    :type connection: socket.socket
    :param addr: The client IP and port number (host,port)
    :type addr: tuple
    :param user_id: The client userID
    :type user_id: str
    :rtype: None
    """
    try:
        while True:
            # Receive and process commands from the client
            message_type, user_id, command = deserialize(connection.recv(2048))
	    
            handle_command(command, connection, addr, user_id)
    except:
        print('JHGIGUG')  # will be printed out when the connection is closed
    finally:
        # The code in the 'finally' block will be executed whether an exception occurs or not
        user_socket, user_address, user_index = get_user_info(user_id)
        with lock:
            connection.close()
            connected_clients.remove(connected_clients[user_index])
        print(f"Connection closed for client {addr}")
        user_IDs.remove(user_id)
        # Assuming threads is a list of threads
        # threads[user_index].join()



def LIST_CLIENTS(connection):
    """
    Lists public clients.
    :param connection: The client socket
    :type connection: socket.socket
    :rtype: None
    """    
    try:
        connection.sendall(serialize(2, serverID, list_connections()))
    except:
        print("ISSUES WITH LIST")


def handle_command(command, connection, addr, user_id):
    """
    Handles commands sent from client
    :param command: The command sent from the client
    :type command: str
    :param connection: The client socket
    :type connection: socket.socket
    :param addr: The client IP and port number (host,port)
    :type addr: tuple
    :param user_id: The client userID
    :type user_id: str
    :rtype: None
    """    
    # COMMANDS = {"LIST_CLIENT", "VISIBILITY", "CONNECT_TO", "TERMINATE"}
    if command.split()[0].split('\n')[0] == COMMANDS[0]:  # if the user wants to see the list of available clients
        LIST_CLIENTS(connection)

    elif command.split()[0].split('\n')[0] == COMMANDS[1]:  # if the user wants to change visibility
        response = command.split()[1].lower()
        for i, value in visibilityOptions.items():
            if response.lower() == value:
                new_vis = i
                break

        change_client_visibility(user_id, new_vis)
        message = "Visibility status changed successfully"
        connection.sendall(serialize(2, serverID, message))

    elif command.split()[0].split('\n')[0] == COMMANDS[2]:  # if the user wants to connect to another user
        # DEBUG
        print("CONNECTING...")
        # DEBUG
        requested_id = command.split()[1]  # the requested user name will be the second word of the command entered by the client
        print("CONNECTING " + user_id + " AND " + requested_id)
        connect_clients(user_id, requested_id)

    elif command.split()[0].split('\n')[0] == COMMANDS[3]:
        # debug
        print(user_id + " IS TERMINATING!!!")
        # debug
        message = "Good bye and take care!"
        connection.sendall(serialize(2, serverID, message))
    else:
        print("what is this mf saying: " + command)

    

server_on()
accepting_connections()