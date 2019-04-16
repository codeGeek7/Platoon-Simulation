#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 17:06:22 2019

@author: vra24
"""

import socket, sys, traceback, json, time, os, termios, tty, struct
from threading import Thread, Lock
lock = Lock()
listReceived = False
endgame = False
clientList = {}
mypos = 0
myspeed = 0
maxspeed = 2
frontpos = -1
maxheadway = 155
minheadway = 150
display_width = 1600
numClients = 0
sleepTime = 0

#-----------------------------------------------------------------------------
def initialize():
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostname()
    port = 6789
    os.system('clear')
    try:
        sockfd.connect((host, port))
    except:
        print("Connection error")
        sys.exit()
    
    myID = requestMyID(sockfd, 0)
    if int(myID) == 1:
        # detect for 'S' input on keyboard, If detected then request server to send list
        detect_key_press(sockfd)
    receive_list(sockfd)
    connect_to_peers(myID, port, sockfd)
        
#-----------------------------------------------------------------------------
def requestMyID(sockfd, reqOpt, BUFSIZE = 4096):
    print("Attempting to connect to server...")
    try:
        sockfd.sendall(str(reqOpt).encode("utf-8"))
    except:
        print("Could not request server for 'myID'")
        sys.exit()
        
    try:
        myID = sockfd.recv(BUFSIZE).decode("utf-8")
        print("SYSTEM: CONNECTION WITH SERVER HAS BEEN ESTABLISHED.")
        print("My ID is : " + myID)
        return myID
    except:
        print("Could not receive my ID from server")
        sys.exit()
        
#-----------------------------------------------------------------------------
def detect_key_press(sockfd):
    button_delay = 0.2
    print("Press c/C to continue accepting client and s/S to stop accepting clients")
    while True:
        key = getch()
        if key == "s" or key == "S":
            print("Requesting server to send client list to all clients")
            try:
                sockfd.send('s'.encode("utf-8"))
            except:
                print("Could not request server to send client list")
                sys.exit()
            break
        elif key == "c" or key == "C":
            print("Receiving more client..")
            try:
                sockfd.send('c'.encode("utf-8"))
            except:
                print("Could not accept more client")
                sys.exit()
        time.sleep(button_delay)

#-----------------------------------------------------------------------------
def receive_list(sockfd, BUFSIZE = 4096):
    global clientList, numClients, lock
    try:
        jsonList = sockfd.recv(BUFSIZE).decode("utf-8")
        clientList = json.loads(jsonList)
        print(clientList)
        with lock:
            numClients = len(clientList)
    except:
        print("Could not receive list")
        sys.exit()
        
#-----------------------------------------------------------------------------
def connect_to_peers(myID, port, sockfd, BUFSIZE = 4096):
    global clientList, mypos, endgame, numClients, sleepTime
    
    # receive initial location from server
    try:
        print("Requesting server for 'start position'")
        sockfd.sendall("xpos".encode("utf-8"))
    except:
        print("Could not request server for 'start position'")
        sys.exit()
        
    try:
        start_x = sockfd.recv(BUFSIZE).decode("utf-8")
        print("My start position is : " + start_x)
        mypos = int(start_x)
    except:
        print("Could not receive my start position")
        sys.exit()

    carinfront = False
    caronback = False
    print("Attempting to connect to other peers...")
    # CONNECT TO THE CAR BEHIND ME, HAS ID = myID + 1
    behindID = str(int(myID) + 1)
    if behindID in clientList.keys():
        mySock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mySock1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        myHost, myPort = clientList[myID]
        myPort = port + int(myID)
        print("Attempting to binding to server with ID: " + behindID)
        try:
            mySock1.bind((myHost, myPort))
            caronback = True
        except:
            print("Bind failed. Error : " + str(sys.exc_info()))
        mySock1.listen(1)
        behindSock, behindAddr = mySock1.accept()
        print("Connected with " + str(behindAddr[0]) + " : " + str(behindAddr[1]))
        
    # CONNECT TO THE CAR IN FRONT OF ME, HAS ID = myID - 1
    frontID = str(int(myID) - 1)
    if frontID in clientList.keys():
        mySock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        frontHost, frontPort = clientList[frontID]
        frontPort = port + int(frontID)
        print("Connecting to server with id " + frontID)
        connected = False
        while not connected:
            try:
                mySock2.connect((frontHost, frontPort))
                carinfront = True
                connected = True
            except:
                pass
    
    BUF = 20
    socklist = []
    if carinfront:
        socklist.append(mySock2)
    if caronback:
        socklist.append(behindSock)
        
    # if there is a car in front
    if carinfront:
        # construct bidirectional communication on user input [ACCEPT USR INPUT && SEND TO FRONT CAR]
        try:
            Thread(target=usrinput, args=(mySock2, socklist, BUF)).start()
        except:
            print("Thread didn't start")
            traceback.print_exc()
    # FIND A WAY TO NOT SEND AN ARGUMENT IF THIS IS THE LEAD CAR!! 
    
        # continously update front car position [RECV FROM FRONT CAR]
        try:
            Thread(target=updatefpos, args=(mySock2, socklist, BUF)).start()   
        except:
            print("Thread didn't start")
            traceback.print_exc()
    else:
        # accept user input [ACCEPT USR INPUT]
        try:
            Thread(target=usrinput, args=(behindSock, socklist, BUF)).start()
        except:
            print("Thread didn't start")
            traceback.print_exc()
    
    # continously send mypos to back car
    if caronback:
        # [SEND TO BACK CAR]
        try:
            Thread(target=sendbpos, args=(behindSock, BUF)).start()
        except:
            print("Thread didn't start")
            traceback.print_exc()
        
        # [RECV FROM BACK CAR]
        try:
            Thread(target=detectbevent, args=(behindSock, socklist, 1)).start()
        except:
            print("Thread didn't start")
            traceback.print_exc()
            
    try:
        with lock:
            if numClients < 4:
                sleepTime = 0.2
            elif 4 <= numClients < 7:
                sleepTime = 0.4
            elif 7 <= numClients < 11:
                sleepTime = 0.6
        Thread(target=sendserver, args=(sockfd, BUF)).start()
    except:
        print("Thread didn't start")
        traceback.print_exc()
    
    while not endgame:
        setpos()
        headway = getheadway()
        if headway == 0:
            continue
        elif headway == 1:
#            print("ACCELERATING from main")
            accelerate(0.05)
        elif headway == -1:      
#            print("DECELERATING from main")
            decelerate()
        
        # stop convoy if there was a crash 
        if headway == -10:
            print("CRASH!!!!")
#            lock.acquire()
            endgame = True
#            lock.release()
            break
    
    socklist.append(sockfd)
#    broadcast(socklist, "Q")
    
    sys.exit()

#=============================================================================
# SEND SERVER
def sendserver(sock, BUF):
    global endgame, mypos, sleepTime
    while not endgame:
        try:
            # CHANGE IS MADE HERE!!!!!!!!!!!!!!!!!!!!!!!!!
            sendlist = {}
            sendlist[0] = mypos
            sendlist[1] = myspeed
#            sendlist = [mypos, myspeed]
            msg = json.dumps(sendlist)
            sock.sendall(str(msg).encode("utf-8"))
            time.sleep(sleepTime)
#            sock.send(str(mypos).encode("utf-8"))
        except:
            traceback.print_exc()
            sys.exit()

#-----------------------------------------------------------------------------
# RECV FROM BACK
def detectbevent(sock, socklist, BUF):
    global endgame
    while not endgame:
        try:
            msg = sock.recv(BUF).decode("utf-8")
            if msg == "A":
                print("ACC from back car")
                accelerate(0.1)
            elif msg == "D":
                print("DCC from back car")
                decelerate()
            elif msg == "S":
                print("STOP from back car")
                for sockelem in socklist:
                    if sockelem != sock:
                        newlist = [sockelem]
                        broadcast(newlist, "S")
                stop()
            elif msg == "Q":
                print("QUIT from back car")
#                lock.acquire()
                endgame = True
                break
#                lock.release()
            else:
                pass
        except:
            pass

#-----------------------------------------------------------------------------
# SEND TO BACK
def sendbpos(sock, BUF):
    global endgame, mypos
    while not endgame:
        try:
            msg = json.dumps(mypos)
            sock.send(struct.pack("i", len(msg))+msg.encode("utf-8"))
#            sock.send(str(mypos).encode("utf-8"))
        except:
            traceback.print_exc()
            sys.exit()
        time.sleep(0.05)

#-----------------------------------------------------------------------------
# RECEIVE FROM FRONT 
# WHEN BROADCASTED TO STOP OR QUIT, IT IS NOT IN STRUCT FORMAT! FIX!
def updatefpos(sock, socklist, BUF):
    global frontpos, endgame
    while not endgame:
        try:
            size = struct.unpack("i", sock.recv(struct.calcsize("i")))[0]
            data = ""
            while len(data) < size:
                msg = sock.recv(size - len(data)).decode("utf-8")
                if not msg:
                    continue
                data += msg
            if data == "Q":
                print("QUIT from front car")
#                lock.acquire()
                endgame = True
                break
            elif data == "S":
                print("STOP from front car")
                for sockelem in socklist:
                    if sockelem != sock:
                        newlist = [sockelem]
                        broadcast(newlist, "S")
                stop()
#                lock.release()
            else:
#            msg = sock.recv(BUF).decode("utf-8")
                lock.acquire()
                frontpos = (float(data))
#            print("frontpos", frontpos)
                lock.release()
        except:
            pass
        

#-----------------------------------------------------------------------------
def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

#-----------------------------------------------------------------------------
# NOTE: lead car has frontpos = -1, never returning headway of -1
def usrinput(sock, socklist, BUF):
    global endgame, myspeed, frontpos, mypos
    button_delay = 0.1
    while True:
        key = getch()
        # accelerate
        if (key == "d"):
            print("Accelerating..")
            headway = getheadway()
            print("Front pos: ", frontpos)
            print("My pos: ", mypos)
            print("Myspeed: ", myspeed)
            # if headway is too small let car in front knows
            if headway == -1:
                print("HEADWAY TOO SMALL")
                sock.send("A".encode("utf-8"))
            elif headway == 1:
                print("HEADWAY TOO BIG")
            accelerate(0.1)
            time.sleep(button_delay)
        # decelerate
        elif (key == "a"):
            print("Decelerating...")
            headway = getheadway()
            print("Front pos: ", frontpos)
            print("My pos: ", mypos)
            print("Myspeed: ", myspeed)
            if headway == 1:
                print("HEADWAY TOO BIG")
                sock.send("D".encode("utf-8"))
            elif headway == -1:
                print("HEADWAY TOO SMALL")
            decelerate()
            time.sleep(button_delay)
        # stop
        elif (key == "s"):
            print("Stopping...")
            print("Front pos: ", frontpos)
            print("My pos: ", mypos)
            print("Myspeed: ", myspeed)
            headway = getheadway()
            broadcast(socklist, "S")
            stop()
#            while (myspeed > 0):
#                headway = getheadway()
#                if headway == 1:
#                    print("HEADWAY TOO BIG")
#                    sock.send("D".encode("utf-8"))
#                decelerate()
            time.sleep(button_delay)
        # quit NEEDS MODIFICATION! LET ALL OTHERS KNOW TO QUIT
        elif (key == "q"):
            print("Ending game...")
#            lock.acquire()
            endgame = True
#            lock.release()
            time.sleep(button_delay)
            break
        else:
            time.sleep(button_delay)
            pass
        time.sleep(button_delay)

#-----------------------------------------------------------------------------
def accelerate(acc_change):
    global myspeed, maxspeed
    lock.acquire()
#    print("ACCEL")
    if myspeed < maxspeed:
        myspeed += acc_change
    lock.release()

#-----------------------------------------------------------------------------
def decelerate():
    global myspeed
    lock.acquire()
#    print("DECEL")
    if myspeed > 0:
        myspeed -= 0.1
    else:
        myspeed = 0
    lock.release()

#-----------------------------------------------------------------------------
def stop():
    global myspeed
    while myspeed > 0:
        decelerate()

#-----------------------------------------------------------------------------
def setpos():
    global myspeed, mypos
    lock.acquire()
    if myspeed < 0:
        myspeed = 0
    mypos = (mypos + (myspeed * (1/36000)))
    lock.release()
    # THIS NEEDS TO BE FIXED SO THAT UPDATED POSITION IS WITHIN THE WINDOW

# calculate headway AND
# return    0 if okay
#           1 if too big
#          -1 if too small

#-----------------------------------------------------------------------------
def getheadway():
    global frontpos, mypos, maxheadway, minheadway
    
    # calculate headway using frontpos
    if frontpos == -1:
        return 0
    
    lock.acquire()
    headway = frontpos - mypos
#    time.sleep(1)
    lock.release()
    
    # if headway is too big call accelerate
    if headway > maxheadway:     
        return 1
        
    # if headway is too small call decelerate
    elif headway < minheadway:
        if headway <= 0:
            return -10
        else:
            return -1
    else:   # if headway is within the boundary
        return 0

#-----------------------------------------------------------------------------
def broadcast(socks, msg):
    for sock in socks:
        sock.send(msg.encode("utf-8"))
        

#=============================================================================
if __name__ == "__main__":
    initialize()
