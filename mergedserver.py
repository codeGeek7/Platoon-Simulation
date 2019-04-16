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
dataList = {}
lock = Lock()
prev = None
speed = {}

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
    port = 6789
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
    sockfd.listen(10)
    clientID = 0
    
    leadConn, leadAdd = sockfd.accept()
    print("Connection received from " + str(leadAdd[0]) + ":" + str(leadAdd[1]))
    clientID += 1
    add_client_to_list(leadConn, clientID, leadAdd)
    recvOpt = leadConn.recv(1).decode("utf-8")
    if recvOpt == "0":
        send_client_ID(leadConn, clientID)

    while True:
        menu = leadConn.recv(1).decode("utf-8")
        if menu == "c":
            clientConn, clientAdd = sockfd.accept()
            clientID += 1
            add_client_to_list(clientConn, clientID, clientAdd)
            clientIP = str(clientAdd[0])
            clientPort = str(clientAdd[1])
            print("Connection received from " + clientIP + ":" + clientPort)
            recvOpt = clientConn.recv(1).decode("utf-8")
            if recvOpt == "0":
                send_client_ID(clientConn, clientID)
        elif menu == "s":
            print("Sending client list..")
            send_client_list(clientList, clientSockList)
            break
        
    start_simulation(clientList, clientSockList)

    sockfd.close()
    
            
#-----------------------------------------------------------------------------
# Function to send client ID when appropriate request is received
def send_client_ID(clientConn, clientID):
    clientConn.sendall(str(clientID).encode("utf-8"))
    
#-----------------------------------------------------------------------------
# Function to add a client connection and information to list
def add_client_to_list(clientConn, clientID, clientAdd):
    global clientList, clientSockList
    lock.acquire()
    clientList[clientID] = clientAdd
    clientSockList[clientID] = clientConn
    lock.release()

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
#    time.sleep(1)
    global dataList, lock, prev, speed
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
#                print(key, qqq)
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
    d = 1000
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
#                time.sleep(0.01)
                gameDisplay.blit(carImg, carRect)
                pygame.display.flip()
            startOfGame = False
        
        with lock:
#            print("{} and sum = {}".format(speed, sum(speed.values())))
            if sum(speed.values()) == 0:
                treeSpeed = 0
            else:
                treeSpeed = 25
            
            for i in range(len(tree)):
                tree[i] -= treeSpeed
                
            if prev < d:
                for i in range(len(dataList)):
                    carRect.center = (float(dataList[i]), start_y)
                    gameDisplay.blit(carImg, carRect)
                    pygame.display.update()
            else:
        
                for p in range(len(dataList)):
                    headway = []
                    headway.append(float(0))
                    for o in range(len(dataList) - 1):
                        headway.append((float(dataList[o]) - float(dataList[o+1])))
                    xp = 1200 - p*headway[p] 
                    carRect.center = (xp, start_y)
                    gameDisplay.blit(carImg, carRect)
                    pygame.display.update()
                    
                    
            for j in range(len(tree)):
                if tree[j] < 0:
                    tree[j] = 1600
            

#        with lock:
#            print([float(dataList[0]) - float(dataList[1]), float(dataList[1]) - float(dataList[2])])
#            print("POSITIONS RECEIVED: {}".format([float(value) for key, value in dataList.items()]))
            
        pygame.display.flip()
        clock.tick(120)
        gameDisplay.fill(white)
        

def receivePos(client_sock,key, BUFSIZE = 8196):
    global lock, dataList, prev, speed
    while True:
        lock.acquire()
        jsonPosList = client_sock.recv(BUFSIZE).decode("utf-8")
        speedPosList = json.loads(jsonPosList)
#        print(speedPosList['0'])
#        print(speedPosList['1'])
        dataList[key-1] = float(speedPosList['0'])
        speed[key-1] = float(speedPosList['1'])
#        print("Client {} : {}, {}".format(key, dataList[key-1], speed[key-1]))
        prev = float(dataList[0])
        lock.release()
        time.sleep(0.01)

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
