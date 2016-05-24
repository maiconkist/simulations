#########################################################
# @file     energy_efficient_n_bs.py
# @author   Gustavo de Araujo
# @date     17 Mar 2016
#########################################################

from peng import *
from antenna import *
from user import *
from bbu import *
from controller import *
from util import *
from grid import *
from cluster import *
import csv
import random
import numpy
import scipy

###############################
#Grid definitions
###############################
DEBUG                   = True
DMACROMACRO             = 500
DMACROUE                = 30    #35
DMACROCLUSTER           = 90    #105
DSMALLUE                = 5
DSMALLSMALL             = 10
DROPRADIUS_MC           = 250
DROPRADIUS_SC           = 500
DROPRADIUS_SC_CLUSTER   = 70
DROPRADIUS_UE_CLUSTER   = 70
DSMALLUE                = 5

###############################
#Test Variables
###############################
n_sites      = 7
n_ues        = 60
uesindoor    = 0.2
uessmallcell = 2/3

###################################
#Functions
###################################

########################################
def build_scenario(n_bbu, n_bs, n_clusters, n_rrh, n_ue):
    grid = Grid(size=(2000,2000))
    macrocells_center = list()

    cntrl = Controller(grid, control_network=False)
    grid.add_controller(cntrl)

    for i in range(n_bbu):
        bbu = BBU(pos=grid.random_pos(), controller=cntrl, grid=grid)
        grid.add_bbu(bbu)

    macrocells(grid, DMACROMACRO, n_bs,  macrocells_center)

    if not(n_rrh < 1):
        clusters(grid, macrocells_center, n_clusters, n_rrh)

    users(grid, macrocells_center, n_bs, n_clusters, n_ue)

    return grid

##########################
def users(grid, macrocells_center, n_bs, n_clusters, n_ue):
    count_ue = 0
    p_users = list()

    for i in range(0, n_bs):
        reset = 1001
        count_ue = 0
        while (count_ue <= n_ue):
            p_is_ok = True
            if reset > 1000:
                count_ue = 0
                reset = 0
                p_users = list()

            if n_clusters > 0:
                cluster = grid._clusters[random.randint((i*n_clusters),
                            ((i*n_clusters) + n_clusters)-1)]

            #Define type of user
            if random.random() < 0.666 and n_clusters > 0:
                p = generate_xy(cluster._pos, DROPRADIUS_UE_CLUSTER, 0)
                p_is_ok = is_possition_ok(p, cluster._pos, DSMALLSMALL)
            else:
                p = generate_xy(macrocells_center[i], DMACROMACRO*0.425, DMACROUE)
            
            #Distribution
            if not(p_is_ok):
                    reset = reset + 1
            else:
                count_ue = count_ue + 1
                p_users.append(p)

        for j in range(0,len(p_users) -1):
            if random.random() < 0.3:
                user_type = User.HIGH_RATE_USER
            else:
                user_type = User.LOW_RATE_USER
            u = User(j, p_users[j], None, grid, user_type)
            grid.add_user(u)

########################################
def clusters(grid, macrocells_center, n_clusters, n_antennas):
    count_antennas = 0
    count_clusters = 0
    p_antennas = list()
    p_clusters = list()
    p_local_clusters = list()
    p_local_antennas = list()
    reset = 0;

    for i in range(0, len(macrocells_center)):
        count_clusters = 0
        print("Create macrocells cluster and rhh: " + str(i))

        while (count_clusters < n_clusters):
            #Generate antennas
            reset = 0;
            count_antennas = 0

            pos = generate_xy(macrocells_center[i],
                    DMACROMACRO*0.425, DMACROCLUSTER)
            p_local_clusters.append(pos)

            while (count_antennas <= n_antennas):
                #If it is impossible to allocate the antennas
                #then clean the clusters and do it again
                if reset > 1000:
                    print "rest"
                    count_antennas = 0
                    count_clusters = 0
                    p_local_clusters = list()
                    p_local_antennas = list()
                    pos = generate_xy(macrocells_center[i],
                        DMACROMACRO*0.425, DMACROCLUSTER)
                    p_local_clusters.append(pos)
                    reset = 0

                p = generate_xy(pos, DROPRADIUS_SC_CLUSTER*0.425, 0)
               
                if (is_possition_ok(p, p_local_antennas, DSMALLSMALL) and 
                        (is_possition_ok(p, pos, DSMALLSMALL))):
                    count_antennas = count_antennas + 1
                    p_local_antennas.append(p)
                else:
                    reset = reset + 1
            
            count_clusters = count_clusters + 1

        for j in range(0,len(p_local_antennas) -1):
            p_antennas.append(p_local_antennas[j])
        
        for k in range(0,len(p_local_clusters)):
            p_clusters.append(p_local_clusters[k])
            
    for l in range(0, len(p_clusters)):
        cluster = Cluster(l+1, p_clusters[l], grid)
        grid.add_cluster(cluster)

    for t in range(0, len(p_antennas)):
        rrh = Antenna(t+1, Antenna.RRH_ID, p_antennas[t], None, grid)
        grid.add_antenna(rrh)

########################################
def is_possition_ok(p, vector, min_distance):
    result = True
    if len(vector) != 0:
        for i in range(0, len(vector)):
            d = euclidian(p,vector[i])
            if  (d < min_distance) or (d == 0):
                result = False
    return result

######################################## 
def generate_xy(center, radius, min_distance):
    pos = [None] * 2 
    not_done = True
    while not_done:
        pos[0] = radius * (1 - 2 * random.random()) + center[0]
        pos[1] = radius * (1 - 2 * random.random()) + center[1]
        not_done = euclidian(pos, center) < min_distance

    return pos

######################################## 
def euclidian(a,b):
   return scipy.spatial.distance.euclidean(a,b)

########################################
def macrocells(grid, radius, n_bs, macrocells_center):
    center = numpy.array([grid.size[0]/2, grid.size[1]/2])
    index = 0

    #Center Antenna
    macrocells_center.append((grid.size[0]/2, grid.size[1]/2))
    bs = Antenna(0, Antenna.BS_ID, center, None, grid)
    grid.add_antenna(bs)

    #Others
    for i in range (0, n_bs-1):
       v = (2 * i) + 1
       #It is not cool initiazile variables in loops...
       #But it only works like this :(
       p_antenna = [None] * 2
       p_antenna[0] = center[0] + radius * math.cos(v*math.pi/6)
       p_antenna[1] = center[1] + radius * math.sin(v*math.pi/6)
       macrocells_center.append(p_antenna)
       bs = Antenna(i+1, Antenna.BS_ID, p_antenna, None, grid)
       grid.add_antenna(bs)

########################################
# Main
########################################
if __name__ == "__main__":

    # Trying to create a new file or open one
    f = open('resumo.csv','w')
    f.write('TOTAL_BS,TOTAL_RRH,TOTAL_UE,USED_RRH,USER_NOT_MEET,EE,SE\n')
    f.close()

    bbu = 2 
    bs = 1 
    cluster = 2
    rrh = 10
    ue = 30

    #Build Scenario
    print "Create scenario"
    arq = open("results.txt","w")
    arq.write("Macros,rrhs,usuarios,scenario,iteracao,c,p,ee,temp\n")


    for i in range (0, 3):
        grid = build_scenario(bbu, bs, cluster, rrh, ue)
        peng = Peng(bs, ue, i)
        peng.run(grid, arq)

    arq.close()
    util.plot_grid(grid)
