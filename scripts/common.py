######
# common functions for our scripts
#####


import sys, time, random, types
import numpy
sys.path.append('..\programs')
import math, inspect, shutil

# force these to be reloaded every time
for mod in sys.modules.values():
    if (mod=='channels' or mod=='calibrations'):
        reload(mod)
          
import labrad
from labrad import types as T, units as U

from calibrations import *
from channels import *


# this one loops over sets of parameters, calling fn(params) for each combination
# the form of iters is [ [key1, values1], [key2, values2]...]
def doloop(fn,params,iters = [],cond = lambda x: True):

    if len(iters) < 1:
        
        if cond(params) is True:
            fn( params )

    else:
        thislist = iters[0][1]
        thiskey = iters[0][0]

        for val in thislist:
            params[thiskey] = val
            doloop(fn,params,iters[1:],cond)

class phase:
    def __init__(self):
        pass
    def getlength(self,params,tstart):
        return 0.0
    def dophase(self,cxn,params,tstart):
        pass

S=0
P=1
def dophaseloop(lst,cxn,params,sttim,run=True):
    innertime=sttim
    maxlen=0
    for p in lst[1:]:
        if type(p)==type([]):
            plen=dophaseloop(p,cxn,params,innertime,run)
        else:
            plen=p().getlength(params,innertime)
            if lst[0]==S:
                print "class:",p.__name__,"  takes:",plen,"  start:",innertime
                if (run==True):
                    p().dophase(cxn,params,innertime)
            else:
                print "class:",p.__name__,"  takes:",plen,"  start:",sttim
                if (run==True):
                    p().dophase(cxn,params,sttim)
        if lst[0]==S:
            innertime=innertime+plen
        if plen>maxlen:
            maxlen=plen
    if lst[0]==S:
        return innertime-sttim
    else:
        return maxlen
        

# write params to file
def writeparams(paramsFile,params):
    csvfile=open(paramsFile,'w')

    dlen=len(params)
    pi=iter(params)
    for i in range(len(params)):
        key=pi.next()
        csvfile.write(key),
        if (type(params[key])==types.ListType or type(params[key])==type(numpy.ndarray([0]))):
            for j in params[key]:
                csvfile.write(","+str(j))
        else:
            csvfile.write(","+str(params[key]))
        csvfile.write("\n")
        
    csvfile.close()

