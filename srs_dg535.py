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
addr = 22

class SRS_DG535(LabradServer):
    """Server to program SRS DG535 delay generator (over GPIB) """
    name="SRS_DG535"
    
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
    
    @setting(10,"set_delay_a",data="v[ns]",returns="v")
    def set_delay_a(self,c,data):
        """ set the delay of A after TO """
        
        delay = data['ns']
        
        # This command does three things:
        # TM1 = ext. trigger
        # DT2,1,0 = set A delay to 0 (after trigger)
        # DT3,2,x = set B delay to x (after A)
        
        cmd = "TM1;DT2,1,%.0fe-9" % delay
        print "Sending cmd %s..." % cmd
        
        self.inst.write(cmd)
        return T.Value(delay,'ns')
    
    @setting(2,"set_delay_ab",data="v[ns]",returns="v")
    def set_delay_ab(self,c,data):
        """ set the AB pulse delay, setting A to zero delay after T0 """
        
        delay = data['ns']
        
        # This command does three things:
        # TM1 = ext. trigger
        # DT2,1,0 = set A delay to 0 (after trigger)
        # DT3,2,x = set B delay to x (after A)
        
        cmd = "TM1;DT3,2,%.0fe-9" % delay
        print "Sending cmd %s..." % cmd
        
        self.inst.write(cmd)
        return T.Value(delay,'ns')
    
    @setting(4,"set_delay_bc",data="v[ns]",returns="v")
    def set_delay_bc(self,c,data):
        """ set the BC pulse delay """
        
        delay = data['ns']
        
        # This command does one thing:
        # DT5,3,x = set C delay to x (after B)
        
        cmd = "DT5,3,%.0fe-9" % delay
        print "Sending cmd %s..." % cmd
        
        self.inst.write(cmd)
        return T.Value(delay,'ns')
        
    @setting(3,"set_delay_cd",data="v[ns]",returns="v")
    def set_delay_cd(self,c,data):
        """ set the CD pulse delay """
        
        delay = data['ns']
        
        # This command does one thing:
        # DT6,5,x = set D delay to x (after C)
        
        cmd = "DT6,5,%.0fe-9" % delay
        print "Sending cmd %s..." % cmd
        
        self.inst.write(cmd)
        return T.Value(delay,'ns')
    
        
if __name__ == "__main__":
    from labrad import util
    util.runServer(SRS_DG535())

    
