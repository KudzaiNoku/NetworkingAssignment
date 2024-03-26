
"""
KudzaiClient.py - A Python program that acts as a client

Author: Kudzaishe Nyika
Date: 04 March 2024
"""
from socket import *
import sys
import struct
import threading
from queue import Queue
import time

COMMANDS = ["LIST_CLIENTS", "VISIBILITY", "CONNECT_TO", "TERMINATE", "CANCEL","\n"]

visibilityOptions = {  # using numbers to prevent spelling errors
    0: "private",
    1: "public"
}
Message_types = {
    0: "COMMAND",
    1: "MESSAGE",
    2: "CONTROL",  # for requesting re-entry
    3: "REQUEST DENIED" , # denying request
    4: "CONNECTION REQUEST" # the server is notifying this client that another client wants to talk to them
}


lock = threading.Lock()
#message_queue = Queue()


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


def on_and_connect():
    """
    Turns on the client and connects it to the server.
    :rtype: None
    """
    try:
        host, port, visibility, user_id = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    except:
        print("NOT ENOUGH ARGUMENTS")
        sys.exit(0)

    global clientSocket, userID

    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect((host, port))

    # CHANGE THE NEXT TO LINES TO USE THE SERIALIZE/DESERIALIZE WHAT_WHATS
    # send visibility status
    for i, value in visibilityOptions.items():
        if visibility.lower() == value:
            current_visibility = i
            break
    userID = user_id
    print("UserID: " + userID)
    # use serialization here
    clientSocket.sendall(serialize(1, userID, str(current_visibility)))
    # send command

    print("CONNECTION ESTABLISHED!")



def validate_command(command):
    """
    Validates commands entered by a user.
    :param command: The command entered by the user
    :type command: str
    :rtype: bool
    """
    valid_command = False
    if (command.split()[0].split('\n')[0]).upper() in COMMANDS:
        valid_command = True   
    return valid_command


def send_commands(command):
    """
    Sends commands to server.
    :param command: The command entered by the user
    :type command: str
    :rtype: bool
    
    """    
    command_keyword = (command.split()[0].split('\n')[0]).upper()

    if command_keyword in [COMMANDS[4], COMMANDS[5]]:
        print("NO COMMAND")
        return False
    # if the user wanted to see the list
    elif command_keyword == COMMANDS[0]:  # if you just want a list
        clientSocket.send(serialize(0, userID, command.upper()))
        return True
    # if the user wants to change visibility
    elif command_keyword == COMMANDS[1]:
        response = command.split()[1].lower()
        while response not in ["public", "private", "cancel"]:
            message = "Invalid visibility option. Please type either PUBLIC or PRIVATE. Say CANCEL to exit this request."
            response = (input("Enter PUBLIC or PRIVATE: ")).lower()
        if response == "cancel":
            return False

        clientSocket.send(serialize(0, userID, command.split()[0].upper() + " " + response))
        return True
    elif command_keyword == COMMANDS[2]:  # if you wanna connect with someone
        # Debug
        print("SENDING: " + command_keyword + " " + command.split()[1])
        # Debug
        clientSocket.send(serialize(0, userID, command_keyword + " " + command.split()[1]))
        print("WAITING FOR REPLY...\n")
        return True
    return True


 
def receive_response(message_type, user_id, response):
    """
    Processes the response received from the server based on the command sent.
    :param message_type: The message type received from server
    :type command: str
    :param user_id: The username of the client receiving server response
    :type command: str
    :param response: The actual response from the server
    :type command: str
    :rtype: None
    """    
    # someone sent YOU a request
    if message_type == 4:
        prep_for_chat(userID, response)
        # threading.Thread(target=prep_for_chat, args=(userID, response)).start()
    elif message_type == 3:
        print("CLIENT NOT AVAILABLE")
    
    elif message_type == 1:
        print(response)
        # ip_address, port_str = response.split(":")[1].strip()
    
    else:
        print("From ", user_id + ":\n", response)

 
    
def prep_for_chat(userID, response):
    """
    Asks client if they want to chat, and performs actions based on client's reply 
    :param user_id: The username of the client receiving request
    :type command: str
    :param response: The server response
    :type command: str
    :rtype: None
    """        
    
    print("REQUEST RECEIVED!!:\n" + response)
    reply = input("Enter reply: ")

    while reply not in ["Y", "N"]:
        reply = input("Invalid reply, say Y or N: ")  # validate response before sending to the server

    if reply == "N":
        print("All good! Proceed with your commands.")
        clientSocket.send(serialize(1, userID, reply))

    else:
        clientSocket.send(serialize(1, userID, reply))
        print("REPLY SENT")
        message_type, user_id, response = deserialize(clientSocket.recv(2048))
        # DEBUG
        print(response)
        ip_address, port_str = response.split(":")[1].strip()
        port = int(port_str)
        print("YOU MAY CHAT NOW")
        chat(ip_address, port)        


def chat(destination_ip, destination_port):
    """
    Manages a chat between two clients
    :param destination_ip: IP address of the client you're talking to
    :type destination_ip: str
    :param destination_port: Port number of client you're talking to
    :type destination_ip: str
    :rtype: None
    
    """
    # Using IPv4 and UDP protocol
    me = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    source_ip = clientSocket.getsockname()[0]
    source_port = clientSocket.getsockname()[1]
    
    # Creating socket
    me.bind((source_ip, source_port))
    chat_is_on = True
    sent = 0
    received = 0

    # Function for receiving messages
    def receiveMessage():
        while chat_is_on:
            if sent == 1 and received == 1:
                print("Chat closed.")
                break
            data = me.recvfrom(1024)
            data = data[0].decode()
            if data[-len("bye"):] == "bye":
                received = 1
                print(f'{data}')
        print("Receiving thread stopped")

    def sendMessages():
        print("...start chat")
        if sent == 1 and received == 1:
            print("Chat closed.")
            chat_is_on = False
        while chat_is_on:
            in_message = input("")
            if in_message == "bye":
                sent = 1
            message = "<" + userID + ">: " + in_message
            me.sendto(message.encode(), (destination_ip, destination_port))
        print("Sending thread stopped")

    receive = threading.Thread(target=receiveMessage)
    send = threading.Thread(target=sendMessages)

    receive.start()
    send.start()

    #receive.join()
    #send.join()

def communicate_with_server():
    """
    Sends commands to the server and processes them accordingly.
    :rtype: None
    """        
    while True:
        command = input("Enter command: ")

        # Check if the command is valid
        while not validate_command(command):
            print("Command not recognized, please try again. CANCEL to exit this request")
            command = input("Enter command: ")

        if (command.split()[0].split('\n')[0]).upper() == COMMANDS[3]:
            # if you want to TERMINATE
            clientSocket.send(serialize(0, userID, command.upper()))
            # DEBUG
            print("TERMINATION REQUEST SENT")
            # DEBUG
            #clientSocket.close()
            break
        else:
            if send_commands(command):  # send command to server
                # Continuously check queue for response
                message_type, user_id, response = deserialize(clientSocket.recv(2048))

                #print("MESSAGE TYPE: " + message_type)

                receive_response(message_type, user_id, response)
            else:
                continue
	    
    clientSocket.close()

on_and_connect()
communicate_with_server()