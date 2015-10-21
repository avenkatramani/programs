#
# Server for setting frequency on Opal Kelly FPGAs that control PTS3200 synthesizer
#
# Code was more or less reverse engineered from labview driver... it is not clear
# where the documentation/code for the FPGA interface is
#
# So far, only a minimal set of features are implemented: get and set frequency
# in principle, this allows the slow change to be done in software by the client without
# using the hardware ramping feature
#
# There is no fast scan, and also no support for changing bit files: this has to be
# done from RoyDAQ still. However, there should be no major obstacle to adding this later.
#
# JDT 7/2015
#
#
from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting
from Queue import Queue
import socket
import time, sys, shutil
import threading
from twisted.internet.defer import returnValue,inlineCallbacks
import ctypes
import numpy
#import ok
# in principle, the ok module gives direct interface to Opal Kelly API. However, the python
# version is not as well documented as the C version (plus the C version is used in labview),
# so it doesn't really make sense to use it.


#from common import *

#GPIB address
addr = 22

class PTS(LabradServer):
    """Server to program SRS DG535 delay generator (over GPIB) """
    name="PTS"
    
    def initServer(self):
        # idx 0 = probe, 1 = ctl
        self.serials = ['10440000KE','10440000K8']
        pass
        
    @setting(9,"start_control",returns='w')
    def start_control(self,c):
        """ establish connection to Opal Kelly FPGAs that control PTS synth"""
        
        path_to_lib = r'C:\Program Files\Opal Kelly\FrontPanelUSB\API\okFrontPanel.dll'
        self.oklib = ctypes.WinDLL(path_to_lib)
        
        self.hnd = self.oklib.okFrontPanel_Construct()
        self.nDev = self.oklib.okFrontPanel_GetDeviceCount(self.hnd)
        
        # this is needed to pass strings by reference to c libraries
        buf = ctypes.create_string_buffer(128)

        self.serials_in = []
        
        for i in range(self.nDev):
            self.oklib.okFrontPanel_GetDeviceListSerial(self.hnd,i,buf)
            
            self.serials_in.append(buf.value)
        
        print "Found %d devices with serials %s" % (self.nDev, repr(self.serials_in))
        print "Expected serials %s" % repr(self.serials)

        return self.nDev
    
    @setting(10,"stop_control")
    def stop_control(self,c):

        self.oklib.okFrontPanel_Destruct(self.hnd)
        self.nDev = 0
    
    @setting(11,"is_connected",returns="w")
    def is_connected(self,c):
        
        return getattr(self,'nDev',0)
        #return self.nDev


    # this is just a test
    @setting(1,"Echo", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return data+"ok"
    
    @setting(3,"get_num",returns="w")
    def get_num(self,c):
        """ returns found number of OK devices """
        return self.nDev
    
    @setting(2,"get_freq",devicenum="w",returns="v")
    def get_freq(self,c,devicenum):
        """ get freq. of device with number devicenum """
        
        if devicenum >= self.nDev:
            print "Error: devicenum %d is out of range (nDev=%d)" % (devicenum, self.nDev)
            return T.Value(0,'MHz')
        
        self.oklib.okFrontPanel_OpenBySerial(self.hnd,self.serials[devicenum])
        
        self.oklib.okFrontPanel_UpdateWireOuts(self.hnd)
        
        self.oklib.okFrontPanel_GetWireOutValue.restype = ctypes.c_uint32
        
        val20 = self.oklib.okFrontPanel_GetWireOutValue(self.hnd,ctypes.c_int32(0x20))
        val21 = self.oklib.okFrontPanel_GetWireOutValue(self.hnd,ctypes.c_int32(0x21))
        
        print "val20,val21 = %d,%d" % (val20,val21)
        
        # this encoding is totally insane, but apparently the way the FPGA is written
        # is that these numbers should be converted into hex strings and then interpreted
        # as base-10 strings.
        
        # So, a frequency of 1234.5678 MHz becomes 12345678 * 100 Hz
        # converted into string '12345678'
        # then split into two strings '1234', '5678'
        # then these strings are interpreted as hex numbers 0x1234, 0x5678
        # and these two hex numbers are sent to the card.
        # To retrieve the frequency here, we do this in reverse.
        
        # make hex string
        lowerhex = format(val20,'x')
        upperhex = format(val21,'x')
        
        # re-interpret as decimal string. This could give error if abcdef appears in string...
        lowerint = int(lowerhex,10)
        upperint = int(upperhex,10)
        
        freqMHz = lowerint*0.0001 + upperint
        
        return T.Value(freqMHz,'MHz')
        


    @setting(4,"set_freq",devicenum='w',freq='v[MHz]')
    def set_freq(self,c,devicenum,freq):
        """ get freq. of device with number devicenum """
        
        if devicenum >= self.nDev:
            print "Error: devicenum %d is out of range (nDev=%d)" % (devicenum, self.nDev)
        
        print freq
            
        freqMHz = freq['MHz']
        
        # convert to insane transmission format (see comment in get_freq)
        freq100Hz = int(round(freqMHz*10000))
        
        freq100HzStr = format(freq100Hz,'d')
        
        freqLSB = int(freq100HzStr[-4:],16)
        freqMSB = int(freq100HzStr[:-4],16)
        
        # this is from WireInParamsSlowScanONLYfreq.vi
        
        self.oklib.okFrontPanel_OpenBySerial(self.hnd,self.serials[devicenum])
        
        self.oklib.okFrontPanel_SetWireInValue(self.hnd, 0x05, ctypes.c_uint16(freqMSB), ctypes.c_uint16(0xFFFF))
        self.oklib.okFrontPanel_SetWireInValue(self.hnd, 0x04, ctypes.c_uint16(freqLSB), ctypes.c_uint16(0xFFFF))
        
        self.oklib.okFrontPanel_UpdateWireIns(self.hnd)
        

        # this is the contents of TriggerFreqSlow.vi
        self.oklib.okFrontPanel_SetWireInValue(self.hnd, 0x11, ctypes.c_uint16(1), ctypes.c_uint16(1))
        self.oklib.okFrontPanel_UpdateWireIns(self.hnd)
        
        self.oklib.okFrontPanel_SetWireInValue(self.hnd, 0x11, ctypes.c_uint16(0), ctypes.c_uint16(1))
        self.oklib.okFrontPanel_UpdateWireIns(self.hnd)
    
    @setting(5,"change_freq_slow",freq='v[MHz]')
    def change_freq_slow(self,c,devicenum,freq):
        
        current_freq = self.get_freq(c,devicenum)
        
        current_freq_MHz = current_freq['MHz']
        new_freq_MHz = freq['MHz']
        
        print "change_freq_slow: f0 = %f, f1=%f" % (current_freq_MHz,new_freq_MHz)
        
        if new_freq_MHz == current_freq_MHz:
            return
        
        step_MHz = 1.0
        wait_s = 0.01
        
        while abs(current_freq_MHz - new_freq_MHz) > step_MHz:
            
            df = 0 - numpy.sign(current_freq_MHz - new_freq_MHz)*step_MHz
            
            current_freq_MHz += df
            
            #print "Setting freq to %f " % current_freq_MHz
            
            self.set_freq(c,devicenum,T.Value(current_freq_MHz,'MHz'))
        
        self.set_freq(c,devicenum,T.Value(new_freq_MHz,'MHz'))
        
if __name__ == "__main__":
    from labrad import util
    util.runServer(PTS())

    
