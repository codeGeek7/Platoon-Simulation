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
    host = socket.gethostbyname('fourier')
#    host = socket.gethostname()
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
            isListReady = request_client_list(sockfd, reqOpt)
            if isListReady == 1:
                receive_list(sockfd)
            else:
                pass
#                reqOpt = 2
        
        if reqOpt == 2:
            break
        
#-----------------------------------------------------------------------------
def requestMyID(sockfd, reqOpt, BUFSIZE = 4096):
    try:
#        print("Requesting server for 'myID'")
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
#        print("Requesting server for 'client list'")
        sockfd.sendall(str(reqOpt).encode("utf-8"))
        time.sleep(1)
    except:
        print("Could not request server for 'client list'")
        sys.exit()
    
    try:
        response = sockfd.recv(BUFSIZE).decode("utf-8")
        if response == '-':
            # List is not ready yet, so pass
            return 0
        elif response == '+':
            # PREPARE TO RECEIVE LIST
            return 1
    except:
        print("Could not receive list from server")
        sys.exit()

#-----------------------------------------------------------------------------
def receive_list(sockfd, BUFSIZE = 4096):
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
