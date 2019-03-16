#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 17:06:22 2019

@author: vra24
"""

import socket, sys, traceback, json, pygame, curses, time
from threading import Thread
isKeyPressed = False

#-----------------------------------------------------------------------------
def initialize():
    global isKeyPressed
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    port = 6666

    try:
        sockfd.connect((host, port))
    except:
        print("Connection error")
        sys.exit()
        
#   Request server for information with the following request options
#   0 : Request server assigned client id, stored in 'myID'
#   1 : Request server for list of connected clients.
    reqOpt = 0
    while True:
        if reqOpt == 0:
            myID = requestMyID(sockfd, reqOpt)
            reqOpt = 1
        
        if reqOpt == 1:
            if int(myID) == 1:
                # detect for 'S' input on keyboard in a separate thread
                # If 'S' is detected then request server to send client list
                Thread(target = detect_key_press, args = (myID, sockfd)).start()
                
#                Thread(target = c1_requests_server_to_send_list, args = (sockfd)).start()
            elif int(myID) > 1:
                # ask server if it will send list
                # if yes then receive, else pass
                request_client_list(sockfd, reqOpt)
#                reqOpt = 2
        
        if reqOpt == 2:
            break
        
#-----------------------------------------------------------------------------
def requestMyID(sockfd, reqOpt, BUFSIZE = 4096):
    try:
        print("Requesting server for 'myID'")
        sockfd.sendall(str(reqOpt).encode("utf-8"))
    except:
        print("Could not request server for 'myID'")
        sys.exit()
        
    try:
        myID = sockfd.recv(BUFSIZE).decode("utf-8")
        print("My ID is : " + myID)
        return myID
    except:
        print("Could not receive my ID from server")
        sys.exit()
    
#-----------------------------------------------------------------------------
def request_client_list(sockfd, reqOpt, BUFSIZE = 4096):
    try:
        print("Requesting server for 'client list'")
        sockfd.sendall(str(reqOpt).encode("utf-8"))
        time.sleep(1)
    except:
        print("Could not request server for 'client list'")
        sys.exit()
    
    try:
        response = sockfd.recv(BUFSIZE).decode("utf-8")
        if response == '-':
            # List is not ready yet, so pass
            pass
        elif response == '+':
            # PREPARE TO RECEIVE LIST
            receive_list(sockfd, BUFSIZE)
    except:
        print("Could not receive list from server")
        sys.exit()
    
#-----------------------------------------------------------------------------
def detect_send_client_list(stdscr):
    # check for 'S' key press
    stdscr.nodelay(True)    # do not wait for input when calling getch
    return stdscr.getch()

#-----------------------------------------------------------------------------
def detect_key_press(myID, sockfd):
    global isKeyPressed
    while True:
        if curses.wrapper(detect_send_client_list) == 83:
            isKeyPressed = True
            c1_requests_server_to_send_list(sockfd)
            break
        else:
            time.sleep(1)
            pass
        

def c1_requests_server_to_send_list(sockfd):
    global isKeyPressed
    if isKeyPressed == True:
    # SHOULD THIS BE AN IF STATEMENT OR A WHILE LOOP WITH BREAK???
        try:
            print("Requesting server to send client list to all clients")
            sockfd.sendall('/'.encode("utf-8"))
            time.sleep(1)
        except:
            print("Could not request server to send client list")
            sys.exit()
    else:
        pass

def receive_list(sockfd, BUFSIZE):
    try:
        jsonList = sockfd.recv(BUFSIZE).decode("utf-8")
        clientList = json.loads(jsonList)
        print(clientList)
    except:
        print("Could not receive list")
        sys.exit()
#=============================================================================
if __name__ == "__main__":
    initialize()
