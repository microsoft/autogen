#This is a singleton.  You use it to pass variables around from script to script, on any level.
#Import this script into your top script and define your socket connection, then import this script's variables 
#into the file where you want to use them.

#For example:

#main.py:
#import socket
#import socket_connection_singleton

#s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#s.bind((socket.gethostname(), 1235))
#s.listen(5)
#logging.info("Waiting for connection...")
#clientsocket, address = s.accept()
#socket_connection_singleton.s = s
#socket_connection_singleton.clientsocket = clientsocket


#client.py:

#import socket
#import socket_connection_singleton

#clientsocket = socket_connection_singleton.clientsocket
#clientsocket.send(bytes("Hello, World!", "utf-8"))

s = None
clientsocket = None
address = None
