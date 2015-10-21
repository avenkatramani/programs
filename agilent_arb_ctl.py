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
addr = 11

class Agilent_Arb(LabradServer):
    """Server to program Agilent 33250A arbitrary waveform generator (over GPIB) """
    name="Agilent_Arb_Ctl"
    
    def initServer(self):
        # runs when server launches. Should establish connection
        rm = visa.ResourceManager()
        
        visa_addr = "GPIB0::%d::INSTR" % addr
        print "Opening connection to VISA address %s" % visa_addr
        
        self.inst = rm.open_resource(visa_addr)

    # this is just a test
    @setting(1,"Echo", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return data+"ok"
        
    @setting(2,'DC',V='v[V]')
    def DC(self,c,V):
        """ set output to DC mode at voltage V """
        
        self.inst.write("APPL:DC DEF,DEF, %.4f" % V['V'])
        self.inst.write("OUTP ON")
        
    @setting(3,'square_pulse',Vhigh='v[V]',period='v[s]',width='v[s]',edge='v[s]',ncycles='w')
    def square_pulse(self,c,Vhigh,period,width,edge,ncycles=1):
        
        command_strings = []
        
        command_strings.append(r':FUNC PULS')
        
        command_strings.append(r':TRIG:SOUR EXT')
        command_strings.append(r':TRIG:SLOP POS')
        command_strings.append(r':TRIG:DEL MIN')
        command_strings.append(r':BURS:STAT ON')
        command_strings.append(r':BURS:NCYC %d' % ncycles)
        command_strings.append(r':BURS:MODE TRIG')
        command_strings.append(r':OUTP:LOAD 50')
        
        command_strings.append(r':VOLT:RANG:AUTO ON')
        
        command_strings.append(r':VOLT:HIGH %.4f V' % Vhigh['V'])
        command_strings.append(r':VOLT:LOW %.4f V' % 0.0)
        
        command_strings.append(r':PULS:PER %.9f s' % period['s'])
        command_strings.append(r':PULS:TRAN %.9f s' % edge['s'])
        command_strings.append(r':PULS:WIDT %.9f s' % width['s'])
        
        command_total = ''
        for s in command_strings:
            command_total += (s + ';')
            
        print command_total
            
        self.inst.write(command_total)
        
    @setting(4,'arb_from_file',filename='s',Vmin='v[V]',Vmax='v[V]',length='v[s]',ncycles='w',returns='w')
    def arb_from_file(self,c,filename,Vmin,Vmax,length,ncycles=1):
        """
        arb_from_file(filename,Vmin,Vmax,length,ncycles)
        
        Reads waveform from file specified by "filename". Outputs to Agilent with Vmin,Vmax,length,ncycles
        specified at input.
        
        If Vmin=Vmax=0, then the waveform amplitude is inferred from the file.
        
        If length=0, the waveform length is inferred from the file. In this case, the file should have two columns,
        where the first is time in microseconds and the second is voltage. The time points should be evenly spaced and start at zero.
        
        Returns 0 for error, 1 for success.
        
        File format: one point per line, comma-separated if times are also present.
            
            [time0,] voltage0
            [time1,] voltage1
            ...
            [timeN,] voltageN
            
        """
        
        try:
        
            f = open(filename,'r')
            
            data_str = list(f)
            f.close()
            
            data_split = [s.split(',') for s in data_str]
            
            #print data_split
            
            times_in_file = len(data_split[0]) > 1
            
            #if length is None and times_in_file is False:
            if length['s']==0 and times_in_file is False:
                print "Error: file does not contain times and length input not specified. How should I know how long the waveform is?"
                return 0
                
            if times_in_file is True:
                times = [float(x[0]) for x in data_split]
                data = [float(x[1]) for x in data_split]
            else:
                data = [float(x[0]) for x in data_split]
                times = []
            
            print "Read %d data points from %s" % (len(data),filename)
            
            #print repr(data)
            
            data_max = max(data)
            data_min = min(data)
            
            # it is faster to download the data as integers instead of a float, so we rescale it to the full
            # DAC range (as outlined in the manual). The data values should go from -2047 to +2047.
            # the Vmin/Vmax commands specify how these map to actual output voltages.
            data_scaled = [ int(round(2*2047*(x - data_min)/(data_max - data_min) - 2047)) for x in data ]
            
            if length['s']==0:
                wfm_len = (times[1] - times[0])*len(times)*1e-6 # assume microseconds, convert to seconds
            else:
                wfm_len = length['s']
            
            #if Vmin is None or Vmax is None:
            if Vmin['V']==0 and Vmax['V']==0:
                min_v = data_min
                max_v = data_max
            else:
                min_v = Vmin['V']
                max_v = Vmax['V']
            
            print "Waveform parameters: (Vmin,Vmax) = (%.3f,%.3f)V, len = %.3f us" % (min_v, max_v, 1e6*wfm_len)

            #print repr(data_scaled)
            
            self._sendWf(data_scaled,min_v,max_v,wfm_len,ncycles)
            
            return 1
            
        except Exception as ex:
        
            print "Error reading file %s" % filename
            
            raise ex
            
            return 0
        
        
    def _sendWf(self,wf_data,Vbot,Vtop,ttot,ncycles=1,load=50):
        # function for internal use, takes array of data wf_data,
        # min,max voltages (in Volts)
        # total time of sequence (in seconds)
        # number of cycles
        # and impedance of output (to interpret voltages)
        
        # wf_data should range from -2047 to 2047
        
        #print wf_data

        #nBytesStr = str(2*array_len)
        #byteStrLen = len(nBytesStr)

        command_string = ":OUTP OFF;:DATA:DAC VOLATILE"
        for pt in wf_data:
            command_string += ", %d" % int(pt)

        
        #command_string = ":OUTP OFF;:FORM:BORD SWAP;:DATA:DAC VOLATILE, #"+str(byteStrLen)+nBytesStr
        print command_string
        #self.gpib.write(self.addr,command_string)
        
        #command_string += struct.pack(str(array_len)+'h',*wf_data)

            
        self.inst.write(command_string)

       # print(len(struct.pack('!'+str(array_len)+'h',*wf_data)))

        #print command_string

        # send this command

        #command_strings = [ command_string ]
        
        command_strings = []
        #command_strings = 

##        command_strings.append(r':DATA:COPY ARB1')

        # send this one
##        command_strings.append(r':FUNC:USER ARB1')
##
##        command_strings.append(r':FUNC USER')
##
        command_strings.append(r':FUNC:USER VOLATILE')
        command_strings.append(r':FUNC:SHAP USER')
        command_strings.append(r':TRIG:SOUR EXT')
        command_strings.append(r':TRIG:SLOP POS')
        command_strings.append(r':TRIG:DEL MIN')
        command_strings.append(r':BURS:STAT ON')
        command_strings.append(r':BURS:NCYC '+str(ncycles))
        command_strings.append(r':BURS:MODE TRIG')

        # important to set this before specifying voltages
        if load>50:
            command_strings.append(r':OUTP:LOAD INF')
        else:
            command_strings.append(r':OUTP:LOAD 50')
        command_strings.append(r':OUTP:POL NORM')

    
        command_strings.append(r':VOLT:RANG:AUTO ON')

        freq = 1.0/ttot
        command_strings.append(':FREQ %f' % freq)

        command_strings.append(r':VOLT:HIGH %f' % Vtop)
        command_strings.append(r':VOLT:LOW %f' % Vbot)

        command_strings.append(r':OUTP ON')

        command_total = ''
        for s in command_strings:
            command_total += (s + ';')
            
        self.inst.write(command_total)

        print "Sent: %s" % command_total

        
if __name__ == "__main__":
    from labrad import util
    util.runServer(Agilent_Arb())

    
