#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 17:06:22 2019

@author: vra24
"""

import socket, sys, traceback, json, time, os, termios, tty, struct, random
from threading import Thread, Lock

# GLOBAL VARIABLES 
lock = Lock()           # LOCK FOR SYNCHRONIZING GLOBAL VARIABLES
listReceived = False    # FLAG FOR CLIENT LIST RECEIVED FROM SERVER
endgame = False         # FLAG FOR ON GOING SIMULATION
clientList = {}         # LIST OF CLIENTS
mypos = 0               # MY POSITION
myspeed = 0             # MY SPEED
maxspeed = 1.0          # MAX SPEED
frontpos = -1           # FRONT POSITION (IF NO FRONT CAR, SET TO -1)
maxheadway = 151        # MAX HEADWAY
minheadway = 150        # MIN HEADWAY

#-----------------------------------------------------------------------------
# MAIN
#-----------------------------------------------------------------------------
def initialize():
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostbyname('cray')
    port = 6789
    os.system('clear')
    
    # ATTEMPTING TO CONNECT TO SERVER
    try:
        print("SYSTEM: Attempting to connect to server.")
        sockfd.connect((host, port))
    except sockfd.timeout:
        print("Connection error: timeout {}")
        sockfd.close()
        sys.exit()
    
    # RECEIVE ID 
    myID = requestMyID(sockfd, 0)
    
    # IF LEAD CAR, DETECT INPUT FROM KEYBORAD
    if int(myID) == 1:
        detect_key_press(sockfd)
        
    # RECEIVE LIST OF CLIENTS FROM SERVER
    receive_list(sockfd)
    
    # START SIMULATION
    connect_to_peers(myID, port, sockfd)
        
#-----------------------------------------------------------------------------
# REQUESTING MY ID TO SERVER     
#-----------------------------------------------------------------------------
def requestMyID(sockfd, reqOpt, BUFSIZE = 4096):
    # SENDING REQUEST 
    try:
        sockfd.sendall(str(reqOpt).encode("utf-8"))
    except:
        print("Could not request server for 'myID'")
        sys.exit()
        
    # RECEIVING MYID
    try:
        myID = sockfd.recv(BUFSIZE).decode("utf-8")
        print("SYSTEM: Connection with the server was successful.")
        print("SYSTEM: My position (ID) is : " + myID)
        return myID
    except:
        print("Could not receive my ID from server")
        sys.exit()

#-----------------------------------------------------------------------------
# READ USER INPUT FROM TERMINAL WINDOW
#-----------------------------------------------------------------------------
def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    # READ A CHARACTER AND RETURN
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

#-----------------------------------------------------------------------------
# LEADCAR RECEIVING USER-PRESSED KEYBORAD INPUT FROM PROMPT
#-----------------------------------------------------------------------------
def detect_key_press(sockfd):
    button_delay = 0.002
    print("******************************************************************************************")
    print("NOTE TO USER: Press c/C to continue accepting client and s/S to stop accepting clients")
    print("******************************************************************************************")
    while True:
        # KEY PRESSED BY USER 
        key = getch()
        
        # IF 's/S', REQUEST CLIENT LIST FROM SERVER
        if key == "s" or key == "S":
            print("SYSTEM: Requesting server to send client list to all clients")
            try:
                sockfd.send('s'.encode("utf-8"))
            except:
                print("Could not request server to send client list")
                sys.exit()
            break
        
        # IF 'c/C', LET SERVER ACCPET MORE CLIENT 
        elif key == "c" or key == "C":
            print("Receiving more client..")
            try:
                sockfd.send('c'.encode("utf-8"))
            except:
                print("Could not accept more client")
                sys.exit()
        time.sleep(button_delay)

#-----------------------------------------------------------------------------
# RECEIVE CLIENT LIST FROM SERVER
#-----------------------------------------------------------------------------
def receive_list(sockfd, BUFSIZE = 4096):
    global clientList, numClients, lock
    try:
        # RECEIVE LIST
        jsonList = sockfd.recv(BUFSIZE).decode("utf-8")
        
        # INITIALIZE GLOBAL VARIABLES (CLIENTLIST, NUMCLIENTS)
        lock.acquire()
        clientList = json.loads(jsonList)
        lock.release()
        
        # PRINT CLIENT LIST
        print(clientList)
    except:
        print("Could not receive list")
        sys.exit()
        
#-----------------------------------------------------------------------------
# START SIMULATION
#-----------------------------------------------------------------------------
def connect_to_peers(myID, port, sockfd, BUFSIZE = 4096):
    global clientList, mypos, endgame, numClients, sleepTime
    
    # REQUEST INITIAL LOCATION TO SERVER
    try:
        print("SYSTEM: Requesting server for 'start position'")
        sockfd.sendall("xpos".encode("utf-8"))
    except:
        print("Could not request server for 'start position'")
        sys.exit()
        
    # RECEIVE INITIAL LOCATION FROM SERVER
    try:
        start_x = sockfd.recv(BUFSIZE).decode("utf-8")
        print("SYSTEM: My start position is : " + start_x)
        
        # INTIALIZE GLOBAL VARIABLE (MYPOS)
        lock.acquire()
        mypos = int(start_x)
        lock.release()
    except:
        print("Could not receive my start position")
        sys.exit()

    carinfront = False
    caronback = False
    print("SYSTEM: Attempting to connect to other peers (neighbour cars).")
    
    # CONNECT TO THE CAR BEHIND ME, HAS ID = MYID + 1
    behindID = str(int(myID) + 1)
    # IF THERE IS CAR BEHIND ME, INITIALIZE SOCKET AND BIND
    if behindID in clientList.keys():
        mySock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mySock1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        myHost, myPort = clientList[myID]
        myPort = port + int(myID)
        try:
            mySock1.bind((myHost, myPort))
            caronback = True
        except:
            print("Bind failed. Error : " + str(sys.exc_info()))
        mySock1.listen(1)
        behindSock, behindAddr = mySock1.accept()
        
    # CONNECT TO THE CAR IN FRONT OF ME, HAS ID = myID - 1
    frontID = str(int(myID) - 1)
    # IF THERE IS CAR IN FRONT OF ME, INITIALIZE SOCKET AND CONNECT
    if frontID in clientList.keys():
        mySock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        frontHost, frontPort = clientList[frontID]
        frontPort = port + int(frontID)
        print("Connecting to server with id " + frontID)
        connected = False
        # WAITING FOR CONNECTION
        while not connected:
            try:
                mySock2.connect((frontHost, frontPort))
                carinfront = True
                connected = True
            except:
                pass
    
    print("SYSTEM: Connection with peers is successful.")

    # IF THERE IS CAR IN FRONT, SET TMPFSOCK TO SOCKET WITH FRONT CAR
    if carinfront:
        tmpfsock = mySock2
    # ELSE, SET TMPFSOCK TO SERVER SOCKET
    else:
        tmpfsock = sockfd
        
    # IF THERE IS CAR ON BACK, SET TMPBSOCK TO SOCKET WITH BACK CAR
    if caronback:
        tmpbsock = behindSock
    # ELSE, SET TMPBSOCK TO SERVER SOCKET
    else:
        tmpbsock = sockfd
    
    
    #=============================================================================
    #                               THREADS
    #=============================================================================
    
    # THREAD OF RECEIVING USER INPUT (ACCELERATE, DECELERATE, STOP, QUIT)
    try:
        t1 = Thread(target=usrinput, name = "thread_1", args=(carinfront, caronback, tmpfsock, tmpbsock), daemon = True)
        t1.start()
    except:
        print("Thread didn't start: usrinput()")
        traceback.print_exc()
        
    # IF THERE IS A CAR IN FRONT
    if carinfront:
        # RECV FROM FRONT CAR: CONTINUOUSLY LISTEN FOR FRONT CAR POSITION
        try:
            t2 = Thread(target=updatefpos, name = "thread_2", args=(caronback, tmpfsock, tmpbsock), daemon = True)
            t2.start()
        except:
            print("Thread didn't start: updatefpos()")
            traceback.print_exc()
    
    # IF THERE IS A CAR ON BACK
    if caronback:
        # SEND TO BACK CAR: CONTINOUSLY SEND MY POSITION TO CAR ON BACK
        try:
            t3 = Thread(target=sendbpos, name = "thread_3", args=(tmpbsock,), daemon = True)
            t3.start()
        except:
            print("Thread didn't start: sendbpos()")
            traceback.print_exc()
        
        # RECV FROM BACK CAR: CONTINOUSLY RECEIVE ON USER INPUT OF BACK CAR (ACC, DCC, STOP, QUIT)
        try:
            t4 = Thread(target=detectbevent, name = "thread_4", args=(carinfront, tmpbsock, tmpfsock), daemon = True)
            t4.start()
        except:
            print("Thread didn't start: detectbevent()")
            traceback.print_exc()
    
    # SEND TO SERVER: CONTINOUSLY SEND MY POSITION AND SPEED TO SERVER 
    try:
        t5 = Thread(target=sendserver, name = "thread_5", args=(sockfd,), daemon = True)
        t5.start()
    except:
        print("Thread didn't start: sendserver()")
        traceback.print_exc()
        
    #=============================================================================
    #                              MAIN THREAD
    #=============================================================================
    while True:
        # IF SIMULATION IS OVER, BREAK
        if endgame:
            break
        
        # UPDATE CURRENT POSITION
        setpos()
        # CALCULATE HEADWAY DISTANCE
        headway = getheadway()
        
        # IF HEADWAY IS TOO BIG, ACCELERATE
        if headway == 1:
            accelerateH(headway, 0.1)
        # IF HEADWAY IS TOO SMALL, DECELERATE
        elif headway == -1:      
            decelerate()
        # IF CRASH HAPPENED
        if headway == -10:
            print("SYSTEM: CAR CRASH!!!!")
            # LET OTHER CARS TO QUIT
            if carinfront:
                try:
                    message = json.dumps("Q")
                    tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                    print("SYSTEM: Send front to QUIT")
                except:
                    print("Send front to QUIT in main failed")
            if caronback:
                try:
                    message = json.dumps("Q")
                    tmpbsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                    print("SYSTEM: Sending back to QUIT")
                except:
                    print("Send to back QUIT from main failed")
            print("Quitting now...")
            # SET GLOBAL VARIABLE (ENDGAME) TO TRUE TO END SIMULATION
            lock.acquire()
            endgame = True
            lock.release()
            break
    
    # CLOSING CLIENT SOCKETS
    if carinfront:
        mySock2.close()
    if caronback:
        behindSock.close()
    
    # CLOSING SERVER SOCKET
    try:
        sendlist = {}
        sendlist[0] = -9
        sendlist[1] = -9
        msg = json.dumps(sendlist)
        sockfd.sendall(str(msg).encode("utf-8"))
    except:
        traceback.print_exc()
        sockfd.close()
        sys.exit()
    sockfd.close()
    
    # END THE PROGRAM
    print("SYSTEM: Exiting the program..")
    sys.exit()

#-----------------------------------------------------------------------------
# SEND TO SERVER
#-----------------------------------------------------------------------------
def sendserver(sock, BUF=1024):
    global endgame, mypos
    while True:
        # IF SIMULATION ENDED, BREAK
        if endgame:
            break
        # SEND SERVER MY POSITION AND SPEED 
        try:
            sendlist = {}
            sendlist[0] = mypos
            sendlist[1] = myspeed
            msg = json.dumps(sendlist)
            sock.sendall(str(msg).encode("utf-8"))
            
            # ACKNOWLEDGEMENT FROM SERVER
            ack = sock.recv(BUF).decode("utf-8")
            if not ack:
                print("SYSTEM: Acknowledgement from server not received")
        except:
            traceback.print_exc()
            sys.exit()

#-----------------------------------------------------------------------------
# RECV FROM BACK
#-----------------------------------------------------------------------------
def detectbevent(carinfront, tmpbsock, tmpfsock):
    global endgame, lock
    while True:
        # IF SIMULATION ENDED, BREAK
        if endgame:
            break
        # RECEIVE EVENT FROM BACK
        try:
            size = struct.unpack("i", tmpbsock.recv(struct.calcsize("i")))[0]
            data=""
            while len(data) < size:
                msg = tmpbsock.recv(size - len(data)).decode("utf-8")
                if not msg:
                    break
                data += msg
            # IF BACK CAR NEEDS ME TO ACCELERATE 
            if data == "\"A\"":
                print("\nSYSTEM: Acceleration from back car")
                 
                # IF THERE IS CAR IN FRONT OF ME, PROPAGATE MESSAGE
                if carinfront:
                    print("SYSTEM: Send front car to accelerate")
                     
                    message = json.dumps("A")
                    tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                accelerate(0.1)
            # IF BACK CAR NEEDS ME TO DECELERATE
            elif data == "\"D\"":
                print("SYSTEM: Deceleration from back car")
                 
                # IF THERE IS A CAR IN FRONT OF ME, PROPAGATE MESSAGE
                if carinfront:
                    print("SYSTEM: Send front car to decelerate")
                     
                    message = json.dumps("D")
                    tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                decelerate()
            # IF BACK CAR NEEDS ME TO STOP
            elif data == "\"S\"":
                print("SYSTEM: Stop from back car")
                 
                print("SYSTEM: Please wait 3 seconds before pressing q/Q to quit")
                 
                # IF THERE IS CAR IN FRONT OF ME, TELL IT TO STOP
                if carinfront:
                    try:
                        message = json.dumps("S")
                        tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                        print("SYSTEM: Send front to Stop")
                         
                    except:
                        print("Send to front Stop from detectbevent failed")
                         
                # STOP
                stop()
            # IF BACK CAR NEEDS ME TO QUIT
            elif data == "\"Q\"":
                print("SYSTEM: Quit from back car")
                 
                # IF THERE IS CAR IN FRONT OF ME, TELL IT TO QUIT
                if carinfront:
                    try:
                        message = json.dumps("Q")
                        tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                        print("SYSTEM: Send front to Quit")
                         
                    except:
                        print("Send to front Quit from detectbevent failed")
                         
                # UPDATE GLOBAL VARIABLE (ENDGAME) TO END SIMULATION
                lock.acquire()
                endgame = True
                lock.release()
                break
        except:
            pass

#-----------------------------------------------------------------------------
# SEND TO BACK
#-----------------------------------------------------------------------------
def sendbpos(sock):
    global endgame, mypos
    while True:
        # IF SIMULATION ENDED, BREAK
        if endgame:
            break
        # SEND MY POSITION TO BACK
        try:
            msg = json.dumps(mypos)
            sock.send(struct.pack("i", len(msg))+msg.encode("utf-8"))
        except:
            traceback.print_exc()
            sys.exit()
        time.sleep(0.001)

#-----------------------------------------------------------------------------
# RECEIVE FROM FRONT 
#-----------------------------------------------------------------------------
def updatefpos(caronback, tmpfsock, tmpbsock):
    global frontpos, endgame, lock
    while True:
        # IF SIMULATION ENDED, BREAK
        if endgame:
            break
        # RECEIVE MESSAGE FROM FRONT
        try:
            size = struct.unpack("i", tmpfsock.recv(struct.calcsize("i")))[0]
            data = ""
            while len(data) < size:
                msg = tmpfsock.recv(size - len(data)).decode("utf-8")
                if not msg:
                    break
                data += msg
            # IF FRONT CAR NEEDS ME TO STOP
            if data == "\"S\"":
                print("SYSTEM: Stop from front car\nSYSTEM: Please wait 3 seconds before pressing q/Q to quit")
                # IF THERE IS CAR ON BACK, TELL IT TO STOP
                if caronback:
                    try:
                        message = json.dumps("S")
                        tmpbsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                        print("SYSTEM: Sending back to Stop")
                    except:
                        print("Send to back Stop from updatefpos failed")
                # STOP 
                stop()
            # IF FRONT CAR NEEDS ME TO QUIT 
            elif data == "\"Q\"":
                print("SYSTEM: Quit from front car")
                # IF THERE IS CAR ON BACK, TELL IT TO QUIT
                if caronback:
                    try:
                        message = json.dumps("Q")
                        tmpbsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                        print("SYSTEM: Sending back to Quit")
                    except:
                        print("Send to back Quit from updatefpos failed")
                # UPDATE GLOBAL VARIABLE (ENDGAME) TO END SIMULATION
                lock.acquire()
                endgame = True
                lock.release()
                break
            # IF MESSAGE WAS POSITION OF FRONT CAR, UPDATE GLOBAL VARIABLE (FRONTPOS)
            else:
                lock.acquire()
                frontpos = (float(data))
                lock.release()
        except:
            pass

#-----------------------------------------------------------------------------
# READ USER INPUT (ACTIONS: ACCELERATE, DECELERATE, STOP, QUIT)
#-----------------------------------------------------------------------------
def usrinput(carinfront, caronback, tmpfsock, tmpbsock):
    global endgame, myspeed, frontpos, mypos, lock, myspeed, maxspeed
    button_delay = 0.002
    while True:
        # IF SIMULATION ENDED, BREAK
        if endgame:
            break
        # DETECT USER INPUT FROM TERMINAL
        key = getch()
        # IF KEY WAS 'd/D', ACCELERATE
        if (key == 'd' or key == 'D'):
            print("SYSTEM: Accelerating..")
            # ACCELERATE
            accelerate(0.1)
            # CALCULATE HEADWAY
            headway = getheadway()
            # IF THERE IS A CAR IN FRONT
            if carinfront:
                # IF HEADWAY IS TOO SMALL, LET FRONT CAR TO ACCELERATE
                if headway == -1:
                    print("SYSTEM: Headway is too small, Send front car to accelerate")
                    message = json.dumps("A")
                    tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
        # IF KEY WAS 'a/A', DECELERATE
        elif (key == 'a' or key == 'A'):
            print("SYSTEM: Decelerating...")
            # DECELERATE
            decelerate()
            # CALCULATE HEADWAY
            headway = getheadway()
            # IF THERE IS CAR IN FRONT
            if carinfront:
                # IF HEADWAY IS TOO BIG, LET FRONT CAR TO DECELERETAE
                if headway == 1:
                    print("SYSTEM: Headway is too big, Send front car to decelerate")
                    message = json.dumps("D")
                    tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
        # IF KEY WAS 's/S', STOP
        elif (key == 's' or key == 'S'):
            print("SYSTEM: Stopping...")
            # IF THERE IS CAR IN FRONT, LET FRONT CAR TO STOP
            if carinfront:
                try:
                    message = json.dumps("S")
                    tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                    print("SYSTEM: Send front to Stop")
                except:
                    print("Send to front Stop failed in usrinput")
                     
            # IF THERE IS CAR ON BACK, LET BACK CAR TO STOP
            if caronback:
                try:
                    message = json.dumps("S")
                    tmpbsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                    print("SYSTEM: Send back to Stop")
                except:
                    print("Send to back Stop failed in usrinput")
            # STOP
            stop()
            print("SYSTEM: Please wait 3 seconds before pressing q/Q to quit")
        # IF KEY WAS 'q/Q', QUIT
        elif (key == 'q' or key == 'Q'):
            print("SYSTEM: Ending simulation...")
            # IF THERE IS CAR IN FRONT, LET FRONT CAR TO QUIT
            if carinfront:
                try:
                    message = json.dumps("Q")
                    tmpfsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                    print("SYSTEM: Send front to Quit")
                except:
                    print("Send to front Quit failed in usrinput")
            # IF THERE IS CAR ON BACK, LET BACK CAR TO QUIT
            if caronback:
                try:
                    message = json.dumps("Q")
                    tmpbsock.send(struct.pack("i", len(message))+message.encode("utf-8"))
                    print("SYSTEM: Send back to Quit")
                except:
                    print("Send to back Quit failed in usrinput")
                     
            # UPDATE GLOBAL VARIABLE (ENDGAME) TO END SIMULATION
            lock.acquire()
            endgame = True
            lock.release()
            break
        time.sleep(button_delay)

#-----------------------------------------------------------------------------
# ACCELERATE ON USER INPUT (EVENT)
#-----------------------------------------------------------------------------
def accelerate(acc_change):
    global myspeed, maxspeed, lock
    # UPDATE GLOBAL VARIABLE (MYSPEED) 
    lock.acquire()
    # IF MY SPEED IS LESS THAN MAX SPEED, INCREASE SPEED
    if myspeed < maxspeed:
        myspeed += acc_change
    lock.release()

#-----------------------------------------------------------------------------
# ACCELERATE WITH REGRADS TO HEADWAY
#-----------------------------------------------------------------------------
def accelerateH(headway, acc_change):
    global maxheadway, myspeed, maxspeed, lock
    # UPDATE GLOBAL VARIABLE (MYSPEED)
    lock.acquire()
    # IF HEADWAY IS NOT TOO BIG, INCREASE SPEED
    if headway < maxheadway:
        myspeed += acc_change
    lock.release()

#-----------------------------------------------------------------------------
# DECELERATE
#-----------------------------------------------------------------------------
def decelerate():
    global myspeed, lock
    # UPDATE GLOBAL VARIABLE (MYSPEED)
    lock.acquire()
    # IF I'M MOVING, DECREASE SPEED
    if myspeed > 0:
        myspeed -= 0.1
    # ELSE, SET SPEED TO 0
    else:
        myspeed = 0
    lock.release()

#-----------------------------------------------------------------------------
# STOP
#-----------------------------------------------------------------------------
def stop():
    global myspeed
    # WHILE MY SPEED IS GREATER THAN 0, DECELERATE
    while myspeed > 0:
        decelerate()

#-----------------------------------------------------------------------------
# SET CURRENT POSITION
#-----------------------------------------------------------------------------
def setpos():
    global myspeed, mypos, lock
    # UPDATE ON GLOBAL VARIABLE (MYSPEED, MYPOS)
    lock.acquire()
    # IF SPEED IS NEGATIVE, SET TO 0
    if myspeed < 0:
        myspeed = 0
    # UPDATE MY POSITION 
    mypos = (mypos + (myspeed * (random.random()/50000)))
    lock.release()

#-----------------------------------------------------------------------------
# CALCULATE HEADWAY
# RETURNING    0 IF I'M LEADCAR OR HEADWAY IS OKAY
#              1 IF HEADWAY IS TOO BIG
#             -1 IF HEADWAY IS TOO SMALL
#            -10 IF CRASH
#-----------------------------------------------------------------------------
def getheadway():
    global frontpos, mypos, maxheadway, minheadway, lock
    
    # IF THERE IS NO FRONT CAR
    if frontpos == -1:
        return 0
    
    # CALCULATE HEADWAY USING FRONTPOS AND MYPOS
    lock.acquire()
    headway = frontpos - mypos
    lock.release()
    
    # HEADWAY TOO BIG
    if headway > maxheadway:     
        return 1
    # HEADWAY TOO SMALL
    elif headway < minheadway:
        # CRASH
        if headway <= 0:
            return -10
        else:
            return -1
    # ACCEPTIBLE HEADWAY
    else:   
        return 0


#=============================================================================
if __name__ == "__main__":
    initialize()
