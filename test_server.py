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


#from common import *


class ErrorServer(LabradServer):
    """Server to handle error messages """
    name="ErrorServer"

    # this is just a test
    @setting(1,"Echo", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return data+"ok"
        
    @setting(100,'test',in1='w',in2='v[MHz]',returns='v')
    def test(self,c,in1,in2):
        print in1
        print in2
        
        return T.Value(0,'s')

        
if __name__ == "__main__":
    from labrad import util
    util.runServer(ErrorServer())

    
