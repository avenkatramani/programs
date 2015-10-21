#
# Server to interface with Agilent 33500B
#

from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting
from Queue import Queue
import socket
import time

# definitions
agilent_IP = '10.0.0.3'
agilent_port = 5025
agilent_timeout =  1   # seconds


class AgilentE8257D(LabradServer):
    """Server to interface with Agilent E8257D"""
    name="AgilentE8257D"

    # this is just a test
    @setting(1,"Echo", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return data

    def send(self,data):
        ret = self.s.send(data)

        if ret != len(data):
            print "Error sending data: " + data + " (" + repr(ret) + "/" + repr(len(data)) + " bytes sent."

    def initServer(self):
        self.s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        self.s.connect((agilent_IP,agilent_port))
        self.s.settimeout(agilent_timeout)

    @setting(2,"set_freq",freq="v")
    def set_freq(self,c,freq):
        
        freq_GHz = freq['GHz']
        
        cmd = ":FREQ %.12f GHz\r\n;:OUTP ON\r\n" % freq_GHz
        
        print cmd
        self.send(cmd)
        
    
    @setting(3,"set_pow",power="v")
    def set_pow(self,c,power):
        """ Set the output power. Accepts input in dBm only. """
        pow_dBm = power['dBm']
        
        cmd = ":POW %.6f dBm\r\n;:OUTP ON\r\n" % pow_dBm
        
        print cmd
        self.send(cmd)




if __name__ == "__main__":
    from labrad import util
    util.runServer(AgilentE8257D())