#
# error server
#
from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting
from Queue import Queue
import socket
import time, sys, shutil, os
import threading
from twisted.internet.defer import returnValue,inlineCallbacks

import subprocess


#from common import *


class HRMLauncher(LabradServer):
    """Server to handle error messages """
    name="HRMLauncher"

    # this is just a test
    @setting(1,"Echo", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return data+"ok"
        
    @setting(100,'launch')
    def launch(self,c):
        
        my_name = sys.argv[0] # this is the filename of this script, hrm_launcher
        my_dir = os.path.split(my_name)
        hrm_path = os.path.join(my_dir[0],'hrmtime.py')
        
        #self.proc = subprocess.Popen([sys.executable, r'C:\Users\Rydberg\Dropbox (MIT)\Our Programs\labrad\MIT programs\hrmtime_test.py'])
        self.proc = subprocess.Popen([sys.executable, hrm_path],shell=False)
        #self.proc = subprocess.call([sys.executable, hrm_path],shell=True)
        #proc = subprocess.Popen(sys.executable)
        
        self.launch_time = time.time()
        
        time.sleep(2.0)
        
        #proc.wait()
        #proc.kill()
    
    @setting(99,'time_since_launch',returns='w')
    def time_since_launch(self,c):
        
        return int(time.time() - self.launch_time)
        

    @setting(101,'kill')
    def kill(self,c):
        
        if getattr(self,'proc',None) is not None:
            try:
                self.proc.kill()
            except:
                pass
            pass
        
        time.sleep(2.0)
        sys.stdout.flush()
            
if __name__ == "__main__":
    from labrad import util
    util.runServer(HRMLauncher())

    
