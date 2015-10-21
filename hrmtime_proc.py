# HRMTime server for LabRAD
#
# This is basically a repackaging of the original HRMTime software in python written in Jan. 2015
# However, that program was killed and restarted for each acquisition, which we didn't want to do
# for the labrad implementation. Instead, we would rather keep the same process running, and just
# start a new thread for each acquisition.

# This turns out to have a significant memory leak problem, which was probably also present in
# the old python code. The effect of the memory leak is essentially that all of the counts that are
# read in stay in memory forever. This is tolerable over ~ 1 hour, but not overnight. It may have
# caused problems with some of the longer acquisitions we tried to do before

# As far as I can tell this is not a bug in the python code, because python is very good at
# memory management and garbage collection. In particular, it does not have anything to do with the
# separate process/conversion threads, because the problem persists when those are off. So, it is
# almost certainly a memory leak in the HRMTime library, which is not surprising. It's not going to be
# worthwhile to track it down.

# The fix is to keep killing and restarting the process. We will do this by launching the server
# from another server hrm_launcher, which has methods launch() and kill() to start and stop the 
# underlying HRMTime server. These should be run at least every hour, although there is not necessarily
# any reason not to run them more frequently, other than the fact that there might be small delays.


# Map of program control
#
# HRMTime class
# HRMTime.acquire()
# --> starts thread with HRMTime._acquire()
# ----> creates Processor()/Converter() classes if necessary, starts threads for them
# --> _acquire() runs until acquisition is finished or HRMTime.force_stop() is run
# 
# Note that the Processor()/Converter() classes are persistent for one _acquire() run,
# but should be re-instantiated on a new run. This means that the global cycle count
# will start over with every new call to HRMTime.acquire(), which is what we want.

# JDT 7/15


import ctypes, os, time, struct, numpy, sys, threading, scipy.io, Queue, readline, gc

from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting
import socket
import time, sys, shutil
import threading
from twisted.internet.defer import returnValue,inlineCallbacks
import ctypes


        
quiet = 1 # 0=lots of info, 1=some info, 2=minimal info

os.environ['PATH'] = 'C:\Program Files (x86)\sensL\HRM-TDC\HRM_TDC DRIVERS' + ';' + os.environ['PATH']

class HRMProcessor(LabradServer):
    name = "HRMProcessor"
    
    def initServer(self):
        self.sensl = ctypes.WinDLL('HRMTimeAPI.dll')
        
    
    @setting(2,"restart")
    def restart(self,c):
        #self.params = params
        
        #self.q = Queue.Queue()
        
        # variables for processing
        self.nCh = 4
        
        self.last_tt = numpy.zeros((self.nCh,2),dtype=ctypes.c_ulong)
        
        self.first_cycle = numpy.zeros((self.nCh,))
        
        self.times = numpy.zeros((self.nCh,), dtype=ctypes.c_double)
        
        self.last_gate = numpy.zeros((self.nCh,),dtype=ctypes.c_double)
        self.num_gates_global = numpy.zeros((self.nCh,),dtype=ctypes.c_ulong)
        self.num_cycles = numpy.zeros((self.nCh,),dtype=ctypes.c_ulong)
        self.num_gates_cycle = numpy.zeros((self.nCh,),dtype=ctypes.c_ulong)
        
        self.num_gates_arr = [ [], [], [], [] ]
        
        self.ch_buf = ctypes.c_char()
        self.gap_buf = ctypes.c_double()
        
        # this will be a list of (ch, time, gate, cycle) tuples
        self.proc_output = []
        
        self.busy = False        
        
        self.params = {}
        self.params['cycle_time_ms'] = 300
        self.params['gate_time_us'] = 40
        self.params['min_gates'] = 10
    
    @setting(1,"process",infile='s',outfile='s')
    def process(self,c,infile,outfile):
        # process the data into cycles and gates
        
        self.busy = True
        
        proc_start = time.time()
        
        read_buf = numpy.fromfile(infile,dtype=ctypes.c_ulong,count=-1,sep='')
        buflen = len(read_buf)
        
        ptr = 0
        
        #self.proc_output = []
        
        while ptr < buflen:
        #while ptr < min(100, act_read_size.value):
            # go through all of the newly-read clicks
            micro = read_buf[ptr]
            macro = read_buf[ptr+1]
            ch = micro & 0b11
            
            ptr += 2
            
            # HRM_STATUS WINAPI HRM_GetTimeTagGap( ULONG pMacro,
            #                                     ULONG pMicro,
            #                                    ULONG cMacro,
            #                                    ULONG cMicro,
            #                                    BYTE *channel
            #                                    double *gap)
            
            #if ch==0:
            #    print "micros: last=%d, cur=%d" % (self.last_tt[ch][0] >> 2, micro >> 2)
            #    print "macros: last=%d, cur=%d" % (self.last_tt[ch][1], macro)
            #
            status = self.sensl.HRM_GetTimeTagGap(ctypes.c_ulong(self.last_tt[ch][1]),
                                            ctypes.c_ulong(self.last_tt[ch][0]),
                                            ctypes.c_ulong(macro),
                                            ctypes.c_ulong(micro),
                                            ctypes.byref(self.ch_buf),
                                            ctypes.byref(self.gap_buf)
                                            )
            self.last_tt[ch][1] = macro
            self.last_tt[ch][0] = micro
            
            self.times[ch] += 1e-6 * self.gap_buf.value # convert from ps to us
            
            #print repr(times)
            
            dt = self.times[ch] - self.last_gate[ch]
            
            #if ch==0:
            #    print "ch=%d, dt=%f" % (ch,dt)
            
            if dt > self.params['cycle_time_ms']*1e3/2.0:
                
                if self.num_gates_global[ch] >= self.params['min_gates']: # was > 10 for multigate # 0 for single gate
                    # start of a new cycle
                    if ch==0:
                        if quiet < 1:
                            print "Finished cycle %d on ch=%d with %d gates, ptr=%d" % (self.num_cycles[ch], ch, self.num_gates_cycle[ch]+1,ptr)
                    
                    self.num_gates_arr[ch].append(self.num_gates_cycle[ch]+1)
                    
                    self.num_gates_cycle[ch] = 0
                    
                    self.num_cycles[ch] += 1
                    self.num_gates_global[ch] += 1
                    
                    self.last_cycle_index = len(self.proc_output)
                    
                    
                
                else:
                    # junk at the beginning... do not count gates or cycles so far
                    self.num_gates_global[ch] = 0
                    self.num_gates_cycle[ch] = 0
                    
                # reset timer at start of every cycle so it doesn't overflow
                self.times[ch] = 0
                self.last_gate[ch] = 0 
                
                #self.last_gate[ch] = self.times[ch]
                
            elif dt > self.params['gate_time_us']*0.75:
                # start of new gate in same cycle
                self.num_gates_cycle[ch] += 1
                self.num_gates_global[ch] += 1
                
                self.last_gate[ch] = self.times[ch]
            
            else:
                # real click
                
                if self.num_cycles[ch] > 0:
                    # dont' save junk at beginning
                    #proc_output[ch].append( (dt, num_gates_cycle[ch], num_gates_global[ch], num_cycles[ch]) )
                    self.proc_output.append( (ch, dt, self.num_gates_cycle[ch], self.num_gates_global[ch], self.num_cycles[ch]) )
                
        
        proc_end = time.time()
        print "Finished processing in %f s" % (proc_end - proc_start)
        print "Have found (on ch0) %d cycles with (min,max)=(%d,%d) gates per cycle" % (self.num_cycles[0],min(self.num_gates_arr[0]),max(self.num_gates_arr[0]))
        
        output_chs = numpy.array( [x[0] for x in self.proc_output[:self.last_cycle_index]],dtype=ctypes.c_ubyte)
        output_times = numpy.array( [x[1] for x in self.proc_output[:self.last_cycle_index]],dtype=ctypes.c_double)
        output_gates_cycle = numpy.array( [x[2] for x in self.proc_output[:self.last_cycle_index]],dtype=ctypes.c_ushort)
        output_gates_global = numpy.array( [x[3] for x in self.proc_output[:self.last_cycle_index]],dtype=ctypes.c_ulong)
        output_cycles = numpy.array( [x[4] for x in self.proc_output[:self.last_cycle_index]],dtype=ctypes.c_ushort)
        
        # keep the rest of the list for next time
        self.proc_output = self.proc_output[self.last_cycle_index:]
        
        scipy.io.savemat(outfile, { 'ch':output_chs,
                                    'times': output_times,
                                    'gates': output_gates_cycle,
                                    'gates_global': output_gates_global,
                                    'cycles': output_cycles}
                                    )
                                    
        print "Finished saving in %f s" % (time.time() - proc_end)
        
        self.busy = False
        
        sys.stdout.flush()
 

if __name__ == "__main__":
    from labrad import util
    util.runServer(HRMProcessor())

#os.execlp('python ',sys.argv[0])
#os.spawnv(os.P_NOWAIT,sys.executable, (sys.executable,sys.argv[0]) )
#os.execv(sys.executable, [sys.executable] + sys.argv)