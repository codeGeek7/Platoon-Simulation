#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 17:06:22 2019

@author: vra24
"""
#-----------------------------------------------------------------------------
# IMPORT PACKAGES
import socket, sys, traceback, json, pygame, curses, time, os, struct, random
from threading import Thread, RLock, Lock

#-----------------------------------------------------------------------------
# DECLARE GLOBAL VARIABLES
clientList = {}
clientSockList = {}
sendList = False
dontAcceptClients = False
dataList = {}
#data = None
lock = Lock()
prev = None

#-----------------------------------------------------------------------------
############################ FUNCTION DEFINITIONS ############################

#-----------------------------------------------------------------------------
# Function to start server
def initialize():
    os.system('clear')
    server_connect()

#-----------------------------------------------------------------------------
# Function to accept client connections and start pygame simulation
def server_connect():
    global dontAcceptClients
    local_hostname = socket.gethostname()
    host = socket.gethostbyname(local_hostname)
    port = 6777
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT
    # state, without waiting for its natural timeout to expire
    try:
        sockfd.bind((host, port))
    except:
        print("Bind failed. Error : " + str(sys.exc_info()))
        sys.exit()

    print("SYSTEM: SERVER IS READY TO ACCEPT CLIENT CONNECTIONS.")
    sockfd.listen(5)
    clientID = 0
     # infinite loop - do not reset for every requests
    i = 0
#    while not dontAcceptClients:
    threadL = []
    while i < 3:
        clientConn, clientAdd = sockfd.accept()
        clientID += 1
        add_client_to_list(clientConn, clientID, clientAdd)
        clientIP = str(clientAdd[0])
        clientPort = str(clientAdd[1])
        print("Connection received from " + clientIP + ":" + clientPort)
        try:
            idThread = Thread(target=client_thread, args=(clientConn, clientID, clientPort, clientIP, clientAdd))
            threadL.append(idThread)
            idThread.start()
#            if clientID == 1:
#            idThread.join()
        except:
            print("Thread did not start.")
            traceback.print_exc()
        i+=1

#    for i in threadL:
#        i.start()
#        i.join()
        
    start_simulation(clientList, clientSockList)

    sockfd.close()
    

#-----------------------------------------------------------------------------
# Function to handle each client connection using threading
def client_thread(clientConn, clientID, clientPort, clientIP, clientAdd, BUFSIZE = 4096):
    global clientSockList
    global dontAcceptClients
#    recvOpt = clientConn.recv(BUFSIZE).decode("utf-8")
#    if recvOpt == '0':
    if clientConn.recv(BUFSIZE).decode("utf-8") == '0':
        send_client_ID(clientConn, clientID)
        
#    elif recvOpt == '/':
    if clientID == 1:
        if clientConn.recv(BUFSIZE).decode("utf-8") == '/':
            send_client_list(clientList, clientSockList)
            dontAcceptClients = True
        time.sleep(0.1)
            
#-----------------------------------------------------------------------------
# Function to send client ID when appropriate request is received
def send_client_ID(clientConn, clientID):
    clientConn.sendall(str(clientID).encode("utf-8"))
    
#-----------------------------------------------------------------------------
# Function to add a client connection and information to list
def add_client_to_list(clientConn, clientID, clientAdd):
    clientList[clientID] = clientAdd
    clientSockList[clientID] = clientConn

#-----------------------------------------------------------------------------    
# Function to send cliend list when appropriate request is received
def send_client_list(clientList, clientSockList):
    jsonList = json.dumps(clientList)
    for client in clientSockList:
        clientSockList[client].sendall(str(jsonList).encode("utf-8"))
#    clientConn.sendall(str(jsonList).encode("utf-8"))

#-----------------------------------------------------------------------------
# Function to start pygame simulation
def start_simulation(clientList, clientSockList, BUFSIZE = 4096):
    time.sleep(1)
    global dataList, lock, prev
    print("\nSYSTEM: STARTING THE PLATOON SIMULATION.")

    display_width = 1600
    display_height = 1000
    start_x = list(range(1,len(clientList)+1))
    start_x = [item*150 - 50 for item in start_x]
    start_x.reverse()
    start_y = display_height/2
    
    # Send initial positions to all clients
    for key, value in clientSockList.items():
        try:
            qqq = value.recv(BUFSIZE).decode("utf-8")
            if qqq == "xpos":
                print(key, qqq)
                value.sendall(str(start_x[key-1]).encode("utf-8"))
            else:
                print(key, qqq)
        except:
            print("Could not send the position to client")
            sys.exit()
            
    pygame.init()
    
    white = (255, 255, 255)
    black = (0,0,0)
    green = (0, 102, 0)
    
    carImg = pygame.image.load('car2.png')
    carImg = pygame.transform.scale(carImg, (100,50))
    carRect = carImg.get_rect()

    gameDisplay = pygame.display.set_mode((display_width, display_height))
    pygame.display.set_caption('Simulator')
    gameDisplay.fill(white)
    clock = pygame.time.Clock()
    
    simulationExit = False
    
    treeSep = 200
    tree = [treeSep*(i+1) for i in range(1600//treeSep)]
    treeSpeed = 0
    y1 = 350
    y2 = 650
    prevPos = []
    d = 800
    limit = list(range(1,11))
    limit = [float(i*d) for i in limit]

    
    startOfGame = True
    threadList = []
    for key, value in clientSockList.items():
        threadList.append(Thread(target = receivePos, args = (value,key)))
        dataList[key-1] = ""
    for i in range(len(clientList)):
        threadList[i].start()
#        threadList[i].join()
#    time.sleep(0.5)

    while not simulationExit:
        for event in pygame.event.get():
            if event.type == pygame.K_ESCAPE:
                pygame.quit()
                quit()
                
        draw_background(gameDisplay, display_width, black, green, tree, y1, y2)
        

        if startOfGame == True:
            for i in range(len(clientList)):
                carRect.center = (start_x[i], start_y)
                time.sleep(0.5)
                gameDisplay.blit(carImg, carRect)
                pygame.display.flip()
            startOfGame = False
        
        with lock:
            if prev < d:
                for i in range(len(dataList)):
        #            postn = int(dataList[key-1],10)
        #            print("#{}# HERE".format(dataList[i]))
        #                print(float(dataList[i]))
                    carRect.center = (float(dataList[i]), start_y)
                    gameDisplay.blit(carImg, carRect)
                    pygame.display.flip()
                        
                if float(dataList[0]) - float(dataList[1])  > 150:
                    treeSpeed = 10
                    for j in range(len(tree)):
                        tree[j] -= treeSpeed
                        
#                for j in range(len(dataList)):
#                    prevPos.append(float(dataList[j]))
            
            else:
                for i in range(len(limit)):
                    if limit[i] < float(dataList[0]) <= limit[i+1]:
                        low = limit[i]
                lowIndex = limit.index(low)

        
                for p in range(len(dataList)):
#                    print("{}: {}".format(i, low))
#                    if i != len(dataList)-1:
#                        carRect.center = ( low - low*lowIndex - i*abs(float(dataList[i]) - float(dataList[i+1])), start_y)
#                        carRect.center = (float(dataList[i]) - (float(dataList[i]) - low*(lowIndex+1)) - i*150*random.randrange(10000)/10000000000, start_y)
                    headway = []
                    headway.append(float(0))
                    for o in range(len(dataList) - 1):
                        headway.append((float(dataList[o]) - float(dataList[o+1])))
#                        headway.append(float(round(150 + random.randrange(4))))
                    print("HEADWAYS: {}".format(headway))
                    xp = 800 - p*headway[p] 
#                    + (random.randrange(10000)/1000000)
#                    print("{} : {}".format(p,xp))
                    carRect.center = (xp, start_y)
                    gameDisplay.blit(carImg, carRect)
                    pygame.display.update()
                    
                treeSpeed = 10
                for j in range(len(tree)):
                    tree[j] -= treeSpeed
                
                
#            if abs(float(dataList[0]) - prevPos[0]) < 0.01 or abs(float(dataList[1]) - prevPos[1]) < 0.01 or abs(float(dataList[2]) - prevPos[2]) < 0.01:
#                treeSpeed = 0
#                for k in range(len(tree)):
#                    tree[k] -= treeSpeed
                    
            for j in range(len(tree)):
                if tree[j] < 0:
                    tree[j] = 1600
            

        with lock:
#            print([float(dataList[0]) - float(dataList[1]), float(dataList[1]) - float(dataList[2])])
            print("POSITIONS RECEIVED: {}".format([float(value) for key, value in dataList.items()]))
            
        pygame.display.flip()
        clock.tick(120)
        gameDisplay.fill(white)
        

def receivePos(client_sock,key):
    global lock, dataList, prev
    while True:
        lock.acquire()
        dataList[key-1] = ""
        size = struct.unpack("i", client_sock.recv(struct.calcsize("i")))[0]
        while len(dataList[key-1]) < size:
            msg = client_sock.recv(size - len(dataList[key-1])).decode("utf-8")
            if not msg:
                continue
            dataList[key-1] += msg
#        print("Client {} : {}".format(key, dataList[key-1]))
        prev = float(dataList[0])
        lock.release()
        time.sleep(0.005)

def draw_background(gameDisplay, display_width, black, green, tree, y1, y2):
    road_1 = (120, 120, 120)
    road_2 = (128, 128, 128)    
    road_3 = (136, 136, 136)
    road_4 = (144, 144, 144)
    road_5 = (152, 152, 152)
    road_6 = (160, 160, 160)
    road_7 = (168, 168, 168)
    road_8 = (176, 176, 176)
    road_9 = (184, 184, 184)
    road_10 = (192, 192, 192)
    
    ground_1 = (0, 192, 0)
    ground_2 = (0, 204, 0)
    ground_3 = (0, 217, 0)
    ground_4 = (0, 230, 0)
    ground_5 = (0, 243, 0)
    ground_6 = (0, 255, 0)
    
    
    pygame.draw.rect(gameDisplay, road_1, (0, 400, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_2, (0, 410, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_3, (0, 420, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_4, (0, 430, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_5, (0, 440, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_6, (0, 450, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_7, (0, 460, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_8, (0, 470, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_9, (0, 480, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_10, (0, 490, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_10, (0, 500, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_9, (0, 510, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_8, (0, 520, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_7, (0, 530, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_6, (0, 540, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_5, (0, 550, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_4, (0, 560, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_3, (0, 570, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_2, (0, 580, display_width, 10), 0)
    pygame.draw.rect(gameDisplay, road_1, (0, 590, display_width, 10), 0)
    
    pygame.draw.rect(gameDisplay, ground_6, (0, 0, display_width, 50), 0)
    pygame.draw.rect(gameDisplay, ground_5, (0, 50, display_width, 50), 0)
    pygame.draw.rect(gameDisplay, ground_4, (0, 100, display_width, 50), 0)
    pygame.draw.rect(gameDisplay, ground_3, (0, 150, display_width, 50), 0)
    pygame.draw.rect(gameDisplay, ground_2, (0, 200, display_width, 100), 0)
    pygame.draw.rect(gameDisplay, ground_1, (0, 300, display_width, 100), 0)
    
    pygame.draw.rect(gameDisplay, ground_1, (0, 600, display_width, 100), 0)
    pygame.draw.rect(gameDisplay, ground_2, (0, 700, display_width, 100), 0)
    pygame.draw.rect(gameDisplay, ground_3, (0, 800, display_width, 50), 0)
    pygame.draw.rect(gameDisplay, ground_4, (0, 850, display_width, 50), 0)
    pygame.draw.rect(gameDisplay, ground_5, (0, 900, display_width, 50), 0)
    pygame.draw.rect(gameDisplay, ground_6, (0, 950, display_width, 50), 0)
        
    pygame.draw.line(gameDisplay,black, (0,400),(display_width,400), 4)
    pygame.draw.line(gameDisplay,black, (0,600),(display_width,600), 4)
    
    for j in range(len(tree)):
        pygame.draw.circle(gameDisplay, green, (tree[j],y1), 25, 0)
        pygame.draw.circle(gameDisplay, green, (tree[j]+50,y2), 25, 0)



 
#-----------------------------------------------------------------------------
################################ MAIN FUNCTION ###############################
if __name__ == "__main__":
    initialize()
