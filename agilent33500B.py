#
# Server to interface with Agilent 33500B
#

from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting
from Queue import Queue
import socket
import time

# definitions
agilent_IP = '10.0.0.2'
agilent_port = 5024
agilent_timeout =  1   # seconds


class Agilent33500B(LabradServer):
    """Server to interface with Agilent 33500B"""
    name="Agilent33500B"

    # this is just a test
    @setting(1,"Echo", data="?", returns="?")
    def echo(self, c, data):
        """Test echo"""
        return data

    @setting(101,"sendMe",data="s")
    def sendMe(self,c,data):
        self.send(data)
        
    def send(self,data):
        
        data_to_send = data + '\r\n'
        ret = self.s.send(data_to_send)

        if ret != len(data_to_send):
            print "Error sending data: " + data + " (" + repr(ret) + "/" + repr(len(data)) + " bytes sent."

    def initServer(self):
        self.s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        self.s.connect((agilent_IP,agilent_port))
        self.s.settimeout(agilent_timeout)
#
#        # put it in controller mode
#        self.send("++mode 1\n")
#        
#        # and disable read-after-write
#        self.send("++auto 0\n")

    @setting(2,'DC',ch='w',V='v[V]')
    def DC(self,c,ch,V):
        """ set output to DC mode at voltage V """
        
        #self.send("SOUR%d" % ch)
        self.send(":SOUR%d:APPL:DC DEF,DEF, %.4f" % (ch,V['V']))
        self.send(":OUTP%d ON" % ch)
        
    @setting(3,'square_pulse',ch='w',Vhigh='v[V]',period='v[s]',width='v[s]',edge='v[s]')
    def square_pulse(self,c,ch,Vhigh,period,width,edge):
        
        command_strings = []
        
        command_strings.append(r':SOUR%d:FUNC PULS' % ch)
        
        command_strings.append(r':TRIG%d:SOUR EXT' % ch)
        command_strings.append(r':TRIG%d:SLOP POS' % ch)
        command_strings.append(r':TRIG%d:DEL MIN' % ch)
        command_strings.append(r':SOUR%d:BURS:STAT ON' % ch)
        command_strings.append(r':SOUR%d:BURS:NCYC 1' % ch)
        command_strings.append(r':SOUR%d:BURS:MODE TRIG' % ch)
        command_strings.append(r':OUTP%d:LOAD 50' % ch)
        
        command_strings.append(r':SOUR%d:VOLT:RANG:AUTO ON' % ch)
        
        command_strings.append(r':SOUR%d:VOLT:HIGH %.4f V' % (ch,Vhigh['V']))
        command_strings.append(r':SOUR%d:VOLT:LOW %.4f V' % (ch,0.0))
        
        command_strings.append(r':SOUR%d:PULS:PER %.9f s' % (ch,period['s']))
        command_strings.append(r':SOUR%d:FUNC:PULS:TRAN %.9f s' % (ch,edge['s']))
        command_strings.append(r':SOUR%d:PULS:WIDT %.9f s' % (ch,width['s']))
        
        command_strings.append(r':OUTP%d ON' % ch)
        
        command_total = ''
        for s in command_strings:
            command_total += (s + ';')
            
        print command_total
            
        self.send(command_total)
    
    @setting(100,'square_pulse_n',ch='w',Vhigh='v[V]',Vlow='v[V]',period='v[s]',width='v[s]',edge='v[s]',npulse='w')
    def square_pulse_n(self,c,ch,Vhigh,Vlow,period,width,edge,npulse):
        
        command_strings = []
        
        command_strings.append(r':SOUR%d:FUNC PULS' % ch)
        
        command_strings.append(r':TRIG%d:SOUR EXT' % ch)
        command_strings.append(r':TRIG%d:SLOP POS' % ch)
        command_strings.append(r':TRIG%d:DEL MIN' % ch)
        command_strings.append(r':SOUR%d:BURS:STAT ON' % ch)
        command_strings.append(r':SOUR%d:BURS:NCYC %d' % (ch,npulse))
        command_strings.append(r':SOUR%d:BURS:MODE TRIG' % ch)
        command_strings.append(r':OUTP%d:LOAD 50' % ch)
        
        command_strings.append(r':SOUR%d:VOLT:RANG:AUTO ON' % ch)
        
        command_strings.append(r':SOUR%d:VOLT:HIGH %.4f V' % (ch,Vhigh['V']))
        command_strings.append(r':SOUR%d:VOLT:LOW %.4f V' % (ch,Vlow['V']))
        
        command_strings.append(r':SOUR%d:PULS:PER %.9f s' % (ch,period['s']))
        command_strings.append(r':SOUR%d:FUNC:PULS:TRAN %.9f s' % (ch,edge['s']))
        command_strings.append(r':SOUR%d:PULS:WIDT %.9f s' % (ch,width['s']))
        
        command_strings.append(r':OUTP%d ON' % ch)
        
        command_total = ''
        for s in command_strings:
            command_total += (s + ';')
            
        print command_total
            
        self.send(command_total)
        
    @setting(4,'arb_from_file',ch='w',filename='s',Vmin='v[V]',Vmax='v[V]',length='v[s]',ncycles='w',returns='w')
    def arb_from_file(self,c,ch,filename,Vmin,Vmax,length,ncycles=1):
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
            data_scaled = [ int(round(2*32767*(x - data_min)/(data_max - data_min) - 32767)) for x in data ]
            
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
            
            self._sendWf(data_scaled,min_v,max_v,wfm_len,ch,ncycles)
            
            return 1
            
        except Exception as ex:
        
            print "Error reading file %s" % filename
            
            raise ex
            
            return 0
        
        
    def _sendWf(self,wf_data,Vbot,Vtop,ttot,ch,ncycles=1,load=50):
        # function for internal use, takes array of data wf_data,
        # min,max voltages (in Volts)
        # total time of sequence (in seconds)
        # number of cycles
        # and impedance of output (to interpret voltages)
        
        # wf_data should range from 
        

        command_strings = []
        
        command_strings.append(r':OUTP%d OFF' % ch)
        command_strings.append(r':SOUR%d:DATA:VOL:CLE' % ch)
        
        temp = r':SOUR%d:DATA:ARB:DAC MYNAME' % ch
        for pt in wf_data:
            temp += r',%d' % int(pt)
        
        command_strings.append(temp)
        
        command_strings.append(r':SOUR%d:FUNC:ARB MYNAME' % ch)
        command_strings.append(r':TRIG%d:SOUR EXT' % ch)
        command_strings.append(r':TRIG%d:SLOP POS' % ch)
        command_strings.append(r':TRIG%d:DEL MIN' % ch)
        command_strings.append(r':SOUR%d:BURS:STAT ON' % ch)
        command_strings.append((r':SOUR%d:BURS:NCYC '  % ch )+str(ncycles) )
        command_strings.append(r':SOUR%d:BURS:MODE TRIG' % ch)

        # important to set this before specifying voltages
        if load>50:
            command_strings.append(r':OUTP%d:LOAD INF' % ch)
        else:
            command_strings.append(r':OUTP%d:LOAD 50' % ch)
        command_strings.append(r':OUTP%d:POL NORM' % ch)

    
        command_strings.append(r':SOUR%d:VOLT:RANG:AUTO ON' % ch)

        freq = 1.0/ttot
        
        command_strings.append(':SOUR%d:FUNC:ARB:FREQ %f' % (ch,freq))
        command_strings.append(r':SOUR%d:FUNC ARB' % ch)
        command_strings.append(r':SOUR%d:VOLT:HIGH %f' % (ch,Vtop))
        command_strings.append(r':SOUR%d:VOLT:LOW %f' % (ch,Vbot))

        
        command_total = ''
        for s in command_strings:
            command_total += (s + ';')
        command_total += r':OUTP%d ON' % ch
  
        self.send(command_total)

        print "Sent: %s" % command_total



if __name__ == "__main__":
    from labrad import util
    util.runServer(Agilent33500B())