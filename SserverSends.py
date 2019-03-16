#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 17:06:22 2019

@author: vra24
"""

import socket, sys, traceback, json, pygame, curses, time
from threading import Thread
clientList = {}
clientSockList = {}
isKeyPressed = False

#-----------------------------------------------------------------------------
def initialize():
    server_connect()

#-----------------------------------------------------------------------------
def server_connect():
    local_hostname = socket.gethostname()
    host = socket.gethostbyname(local_hostname)
    port = 6666
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT
    # state, without waiting for its natural timeout to expire
    try:
        sockfd.bind((host, port))
    except:
        print("Bind failed. Error : " + str(sys.exc_info()))
        sys.exit()

    sockfd.listen(3)
    clientID = 0
    
     # infinite loop - do not reset for every requests
    
    while True:
        print("Awaiting client connection...")
        clientConn, clientAdd = sockfd.accept()
        clientID += 1
        add_client_to_list(clientConn, clientID, clientAdd)
        clientIP = str(clientAdd[0])
        clientPort = str(clientAdd[1])
        print("Connected with " + clientIP + ":" + clientPort)
        try:
            Thread(target = detect_isKeyPress).start()
            Thread(target=client_thread, args=(clientConn, clientID, clientPort, clientIP, clientAdd)).start()
        except:
            print("Thread did not start.")
            traceback.print_exc() 
    sockfd.close()
    
#-----------------------------------------------------------------------------
def client_thread(clientConn, clientID, clientPort, clientIP, clientAdd, BUFSIZE = 4096):
    global isKeyPressed
#   Receive request options from client for handling requests
#   0 : Send server assigned client id, stored in 'myID'
#   1 : Send list of connected clients to all clients if 'lead car' has
#       requested and stop accepting more client connections
    while True:
        recvOpt = clientConn.recv(BUFSIZE).decode("utf-8")
        if recvOpt == '0':
            send_client_ID(clientConn, clientID)
        
        if recvOpt == '1':
            if isKeyPressed == False:
                # respond no
                clientConn.sendall('-'.encode("utf-8"))
            else:
                clientConn.sendall('+'.encode("utf-8"))
                send_client_list(clientList, clientConn)
                # send list 
                


#-----------------------------------------------------------------------------
def send_client_ID(clientConn, clientID):
    clientConn.sendall(str(clientID).encode("utf-8"))
    
#-----------------------------------------------------------------------------
def add_client_to_list(clientConn, clientID, clientAdd):
    clientList[clientID] = clientAdd
    clientSockList[clientID] = clientConn
    
#-----------------------------------------------------------------------------
def send_client_list(clientList, clientConn):
    print("Sending list...")
    jsonList = json.dumps(clientList)
    clientConn.sendall(str(jsonList).encode("utf-8"))

#-----------------------------------------------------------------------------
def detect_for_S(stdscr):
    # check for 'S' key press
    stdscr.nodelay(True)    # do not wait for input when calling getch
    return stdscr.getch()

#-----------------------------------------------------------------------------
def detect_isKeyPress():
    global isKeyPressed
    while True:
        if curses.wrapper(detect_for_S) == 83:
            isKeyPressed = True
            break
        else:
            time.sleep(1)
            pass


#=============================================================================
if __name__ == "__main__":
    initialize()