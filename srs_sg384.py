#
# error server
#
from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting
from Queue import Queue
import socket
import time, sys, shutil
import threading
from twisted.internet.defer import returnValue,inlineCallbacks
import visa


#from common import *

#GPIB address
addr = 20

class SRS_SG384(LabradServer):
    """Server to handle error messages """
    name="SRS_SG384"
    
    def initServer(self):
        # runs when server launches. Should establish connection
        rm = visa.ResourceManager()
        
        visa_addr = "GPIB0::%d::INSTR" % addr
        print "Opening connection to VISA address %s" % visa_addr
        
        self.inst = rm.open_resource(visa_addr)
    
    def stopServer(self):
        self.inst.close()


    # this is just a test
    @setting(1,"Echo", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return data+"ok"
    
    @setting(2,"set_freq",data="v",returns="v")
    def set_freq(self,c,data):
        """ set the output frequency """
        
        freqGHz = data['GHz']
        
        cmd = "FREQ %.17f GHz" % freqGHz
        
        print "Sending cmd %s..." % cmd
        
        self.inst.write(cmd)
        
        return T.Value(freqGHz,'GHz')
    
    @setting(3,"set_pow",data="v",returns="v")
    def set_pow(self,c,data):
        """ set the output power (accepts dBm as units) """
        
        powdbm = data['dBm']
        
        cmd = "AMPR %.4f dBm" % powdbm
        
        print "Sending cmd %s..." % cmd
        
        self.inst.write(cmd)
        
        return T.Value(powdbm,'dBm')

        
if __name__ == "__main__":
    from labrad import util
    util.runServer(SRS_SG384())

    
