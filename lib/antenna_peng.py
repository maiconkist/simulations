import math
import numpy
import util
import controller
from antenna import *
from user import *


class AntennaPeng(Antenna):

    def __init__(self, id, type, pos, radius, grid, bw = 1.4):
        Antenna.__init__(self, id, type, pos, radius, grid, bw)


    def init_peng(self, rbs, antennas):
        self.K = rbs
        self.N = len(self._ues)

        if self.N < 1:
            return

        self.others = antennas
        self.cnir = numpy.zeros((self.N, self.K))
        self.a = numpy.zeros((self.N, self.K))
        self.p = numpy.zeros((self.N, self.K))
        self.h = numpy.zeros((self.N, self.K))
        self.w = numpy.zeros((self.N, self.K))
        self.c = numpy.zeros((self.N, self.K))

        self.energy_efficient        = []
        self.energy_efficient.append(0)

        self.data_rate               = 0
        self.total_power_consumition = 0
        
        self.pm                      = Antenna.PMmax / self.N

        # Multiplicadores Lagrange 
        self.betan                   = numpy.zeros((self.N, 2))
        for n in range(0, self.N):
            for l in range(0, 2):
                self.betan[n][l] = 1 

        self.lambdak                 = numpy.zeros((self.K, 2))
        for k in range(0, self.K):
            for l in range(0, 2):
                self.lambdak[k][l] = 1

        self.upsilonl = [1,1]
        self.sub_betan = 1
        self.sub_lambdak = 1
        self.sub_upsilonl = 1

    def update_antennas(self, antennas):
        self.others = antennas

    def obtain_matrix(self):
        # Obtain CNIR, W and H

        self.interference_calc(self._grid)
        #print "CNIR"
        #print numpy.matrix(self.cnir)
        #print numpy.matrix(self.p)
        #raw_input("")
        for n in range(0, self.N):
            for k in range (0, self.K):
                #self.cnir[n][k] = self.power_interfering(self._ues[n], k,
                #        self.others)
                self.w[n][k] = self.waterfilling_optimal(n, k)
                #h1 = self.cnir[n][k] * self.w[n][k]
                #h2 = ((1 + self.betan[n][0]) * numpy.log(h1))
                #h3 = ((1 + self.betan[n][0]) / numpy.log(2)) 
                #h4 = (1 - (1 / h1))

                #if h2 < 1:
                #    h2 = 0
                #if h4 < 1:
                #    h4 = 0

                #self.h[n][k] = h2 - (h3 * h4)
        
        #self.a = numpy.zeros((self.N, self.K))
        nn = 0
        for k in range(0, self.K):
            n_max = -9999
            for n in range(0, self.N):
                if n_max < self.h[n][k]:
                    nn = n
                    n_max = self.h[n][k]
            self.a[nn][k] = 1

            #Obtain P
            #p = self.w[nn][k] - (1 / self.cnir[nn][k])

            #if p > 0:
            #    self.p[nn][k] = p

    def waterfilling_optimal(self, n, k):
        p1 = (Antenna.B0 * (1 + self.betan[n][0])) 
        p2 = math.log((self.energy_efficient[len(self.energy_efficient)-1]
            * Antenna.EFF) + (self.lambdak[k][0] * Antenna.DR2M * Antenna.HR2M) + 
            self.upsilonl[0])
        return p1 / p2

    ################################
    # Subgrad calculation
    def sub_c(self):
        for n in range(0, self.N):
            for k in range(0, self.K):
                self.c[n][k] = self.a[n][k] * self.B0 * math.log(1
                        + (self.cnir[n][k] * self.p[n][k]))

    def obtain_sub_betan(self, n):
        soma = 0
        for k in range(0, self.K):
            soma += self.c[n][k]

        if ((n > 0) and n < (self.N)):
            self.sub_betan = soma - 1474#Antenna.NR
        else:
            self.sub_betan = soma - 737#((((64/1000) *1024) / 2) / 8) * 180#Antenna.NER

    def obtain_sub_lambdak(self, k):
        soma = 0
        for n in range (0, self.N):
            if self._ues[n]._type == User.LOW_RATE_USER:
                self.sub_lambdak = 0
            else:
                soma += self.a[n][k] * self.p[n][k] * self.DR2M * self.HR2M
        self.sub_lambdak = Antenna.D_0 - soma

    def obtain_sub_upsilonl(self):
        soma = 0
        for n in range(0, self.N):
            for k in range (0, self.K):
                soma += self.a[n][k] * self.p[n][k]
        self.sub_upsilonl = Antenna.PRmax - soma
       
    #################################
    # Lagrange
    def obtain_lagrange_betan(self, n):
        self.obtain_sub_betan(n)
        #print("self.betan["+ str(n) +"][0]: " + str(self.betan[n][0]))
        #print("E_BETA: " + str(Antenna.E_BETA))
        #print("self.sub_betan: " + str(self.sub_betan))
        #raw_input("")
        result = self.betan[n][0] - (Antenna.E_BETA * self.sub_betan)
        if result > 0:
            self.betan[n][1] = result
        else:
            self.betan[n][1] = 0

    def obtain_lagrange_lambdak(self, k):
        self.obtain_sub_lambdak(k)
        result = self.lambdak[k][0] - (self.E_LAMBDA
                * self.sub_lambdak)
        if result > 0:
            self.lambdak[k][1] = result
        else:
            self.lambdak[k][1] = 0

    def obtain_lagrange_upsilonl(self):
        self.obtain_sub_upsilonl()
        result = self.upsilonl[0] - (self.E_UPSILON
                * self.sub_upsilonl)
        if result > 0:
            self.upsilonl[1] = result
        else:
            self.upsilonl[1] = 0

    def update_lagrange(self):
        self.sub_c()
        #print "cnir:"
        #print numpy.matrix(self.cnir)
        #print "p:"
        #print numpy.matrix(self.p)
        #raw_input("")

        for n in range(0, self.N):
            self.obtain_lagrange_betan(n)

        for k in range(0, self.K):
            self.obtain_lagrange_lambdak(k)

        self.obtain_lagrange_upsilonl()
       
    def max_dif(self):
        max_beta = -9999
        max_lambdak = -9999
        for n in range(0, self.N):
            if self.betan[n][0] > 0 :
                beta = (self.betan[n][1] - self.betan[n][0]) / self.betan[n][0]
            else:
                beta = (self.betan[n][1] - self.betan[n][0])

            if beta > max_beta:
                max_beta = beta

        for k in range(0, self.K):
            lambdak = (self.lambdak[k][1] - self.lambdak[k][0]) / self.lambdak[k][0]
            if lambdak > max_lambdak:
                max_lambdak = lambdak
   
        if self.upsilonl[0] != 0:
            max_upsilonl = (self.upsilonl[1] - self.upsilonl[0]) / self.upsilonl[0]
        else:
            max_upsilonl = self.upsilonl[1] - self.upsilonl[0]

        print ("max_beta: " + str(max_beta) + " ,max_lambdak: "
                + str(max_lambdak) + " ,max_upsilonl: " + str(max_upsilonl))
        return max(max_beta, max_lambdak, max_upsilonl)

    def swap_l(self):
        for n in range(0, self.N):
            self.betan[n][0] = self.betan[n][1]
    
        for k in range(0, self.K):
            self.lambdak[k][0] = self.lambdak[k][1]
        
        self.upsilonl[0] = self.upsilonl[1]

    ##########################
    # Calculo do EE
    #########################
    def obtain_data_rate(self):
        for n in range(0, self.N):
            for k in range (0, self.K):
                self.data_rate += self.a[n][k] * Antenna.B0 * math.log(1
                        + (self.cnir[n][k]*self.p[n][k]))

    def obtain_power_consumition(self):
        result = 0
        for n in range(0, self.N):
            for k in range(0, self.K):
                result += (self.a[n][k] * self.p[n][k])           
        self.total_power_consumition = (self.EFF * result) + self.PRC + self.PBH
                                
    def obtain_energy_efficient(self):
        self.obtain_data_rate()
        self.obtain_power_consumition()
        self.energy_efficient.append(self.data_rate/self.total_power_consumition)


    ##############################
    #
    def interference_calc(self, grid):
        for ue in range (0, self.N):
            for rb in range (0, self.K):
                self.cnir[ue][rb] = self.power_interfering(self._ues[ue], rb, self.others)
                self.p[ue][rb] = self.calculate_p(ue, rb)
        

    def power_interfering(self, ue, rb, antennas):
        interference = 0
        Gt = 0.1                       #transmission antenna gain
        Gr = 0.1                       #receiver antenna gain
        Wl = (3/19.0)                  #Comprimento de onda considerando uma frequencia de 1.9 GHz
        for ant in antennas:
            if (ue._connected_antenna._id != ant._id and hasattr(ant, 'a') and sum(ant.a[:,[rb]])>0):
                index = numpy.argmax(ant.a[:,[rb]])
                R  =  util.dist(ue, ant)
                interference += ant.a[index,rb] * ant.p[index,rb] * (Gt * Gr * ( Wl / math.pow((4 * math.pi * R), 2)))

        return interference


    def calculate_p(self, ue, rb):
        #Obtain P in W                                                                                
        #p = self.waterfilling_optimal(n,k) - (1 / self._cnir[n][k])  
        N = 0.000000000001             #ruido
        Pr = N * (math.pow(2,4.5234)-1)#receivedpower 
        Gt = 0.1                       #transmission antenna gain
        Gr = 0.1                       #receiver antenna gain
        Wl = (3/19.0)                  #Comprimento de onda considerando uma frequencia de 1.9 GHz
        R  = util.dist(self._ues[ue], self) #distance between antennas 
        Ar = self.cnir[ue, rb]            #interference plus pathloss
        p = (Pr + Ar) / (Gt * Gr * ( Wl / math.pow((4 * math.pi * R), 2)))                                            
        return p

