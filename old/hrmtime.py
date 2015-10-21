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

class Processor:

    
    def __init__(self,params):
        self.sensl = ctypes.WinDLL('HRMTimeAPI.dll')
        self.params = params
        
        self.q = Queue.Queue()
        
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
    
    def master(self):
        ### master
        
        self.stop_flag = False
        
        while self.q.empty() is False or self.stop_flag is False:
            files = self.q.get() # will block until we get one
            print "Starting processing, queue length = %d" % self.q.qsize()
            self.process(files['infile'],files['outfile'])
            
        print "processor is exiting!"
    
    def stop(self):
        self.stop_flag = True
            
    
    def process(self,infile,outfile):
        # process the data into cycles and gates
        
        self.busy = True
        
        proc_start = time.time()
        
        read_buf = numpy.fromfile(infile,dtype=ctypes.c_ulong,count=-1,sep='')
        buflen = len(read_buf)
        
        ptr = 0
        self.proc_output = []
        
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
                    
                    self.last_cycle_index = len(self.proc_output) - 1
                    
                    
                
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
        
        scipy.io.savemat(outfile, { 'ch':output_chs,
                                    'times': output_times,
                                    'gates': output_gates_cycle,
                                    'gates_global': output_gates_global,
                                    'cycles': output_cycles}
                                    )
                                    
        print "Finished saving in %f s" % (time.time() - proc_end)
        
        self.busy = False
        
        sys.stdout.flush()
        
class Converter:
    # class for separate thread to convert to old file format
    
    q = Queue.Queue()
    
    def __init__(self):
        self.sensl = ctypes.WinDLL('HRMTimeAPI.dll')
        
        self.busy = False
        
    
    def master(self):
        ### master
        
        self.stop_flag = False
        
        #while True:
        while self.q.empty() is False or self.stop_flag is False:
            files = self.q.get() # will block until we get one
            print "Starting file conversion, queue length = %d" % self.q.qsize()
            self.process(files['infile'],files['outfile'])
    
    def stop(self):
        self.stop_flag = True
            
    
    def process(self,infile,outfile):
        # process the data into cycles and gates
        
        self.busy = True
        
        proc_start = time.time()
        
        #HRM_STATUS WINAPI HRM_ConvertRAWtoCSV( USHORT mode, #1 for free, 2 for resync
        #                                     USHORT macroBits, # doesn't matter for TT modes
        #                                    BYTE *rawFile,
        #                                    BYTE *csvFile)
        try:
            self.sensl.HRM_ConvertRAWtoCSV(ctypes.c_ushort(1),
                                    ctypes.c_ushort(0),
                                    infile,
                                    outfile)
        except ValueError:
            pass
                                    
        print "Finished converting %s in %f s" % (outfile, time.time() - proc_start)
        
        sys.stdout.flush()
        
        self.busy = False
 
def is_power_of_two(x):
    while (x & 1)==0 and x>0:
        x = x>>1
    return x==1
    
  
##############
## Execution starts here
##############       
        
class HRMTime(LabradServer):
    """Server to program SRS DG535 delay generator (over GPIB) """
    name="HRMTime"
    
    def initServer(self):

        self.sensl = ctypes.WinDLL('HRMTimeAPI.dll')
        
        # initialize HRM module
        self.sensl.HRM_GetDLLVersion.restype = ctypes.c_char_p
        dll_str = self.sensl.HRM_GetDLLVersion()
        print "HRM DLL Version %s" % dll_str
        
        self.sensl.HRM_RefreshConnectedModuleList()
        num_mod = self.sensl.HRM_GetConnectedModuleCount()

        print "Found %d module(s)." % num_mod
        
        handle_buf_type = ctypes.c_int*3
        handle_buf = handle_buf_type(0,0,0)

        # get handle to identify device in future communiations
        status = self.sensl.HRM_GetConnectedModuleList(ctypes.pointer(handle_buf))
        self.h = handle_buf[0]

        sb = ctypes.create_string_buffer(128)
        status = self.sensl.HRM_GetModuleIDRegister(self.h,sb)

        id_str = ''
        for i in sb:
            id_str += i
        
        srr = ctypes.c_ushort(0)

        status = self.sensl.HRM_GetSoftwareRevisionRegister(self.h,ctypes.byref(srr))

        print "Module ID is %s; FPGA Vers. 0x%x" % (id_str,srr.value)

        sys.stdout.flush()
        
        self.running = False
        self.force_stop = False
        
    
    @setting(1,"acquire",save_prefix='s',runtime='v[s]',returns='w')
    def acquire(self,c,save_prefix,runtime):
        ''' acquire for specified time, saving in location/name specified by save_prefix. runtime < 0 indicates run indefinitely
        
        E.g. hrmtime.acquire(r'C:\path\to\files\run1_prefix',T.Value(120.0,'s'))
        '''
        
        if self.running is True:
            print "Acquisition already running!"
            return 0
        
        self.runtime = runtime['s']
      
               
        
        ##############################################
        #### ONLY CHANGE THESE THINGS
        #############
        #SAVE_PATH = r'C:\Users\Rydberg\Dropbox (MIT)\HRMTimeData\2015-07\20150709'
        #SAVE_PREFIX = 'run1_EIT_fpr_1497MHz_fctl_1792MHz_Vpr_2.25V_Vctl_1.3V'
        #SAVE_PREFIX = 'run16a_delaymeas'
        #SAVE_PREFIX = 'test'
        self.save_prefix = save_prefix
        
        #counter_start =0
        #counter_max =-1    # set to < 0 to keep going forever
        self.target_filesize_MB = 2
        #max_filetime = 50 # maximum time to wait for one file, in seconds
        
        self.process = True # whether to also process the clicks into cycles and gates 
        self.save_old_format = False #whether to call HRM convertToCSV library to save files in old format
        
        #self.gate_time_us = 40
        #self.cycle_time_ms = 350
        
        self.process_params = {}
        self.process_params['gate_time_us'] = 40
        self.process_params['cycle_time_ms'] = 350
        self.process_params['min_gates'] = 10 # 10 for usual multi-gate cycles, set to 0 for single gate operation

        
        ##############################################
        
        self.target_filesize = self.target_filesize_MB*2**20
        
        

        print "Starting acquisition to %s for %d s..." % (save_prefix, self.runtime)
        
        self.thd_acq = threading.Thread(target=self._acquire)
        self.running = True
        self.force_stop = False
        self.thd_acq.start()
        
        print time.time()
        
        return 0
    
    @setting(2,'is_running',returns='w')
    def is_running(self,c):
        if self.running:
            return 1
        return 0
        
    @setting(3,'force_stop')
    def force_stop(self,c):
        self.force_stop = True
        
    @setting(100,'kill_me')
    def kill_me(self,c):
        print "Restarting at %s" % sys.argv[0]
        self._stopServer()
        #os.execlp('python ',sys.argv[0])
        #os.spawnl(os.P_NOWAIT,'python '+sys.argv[0])


    def _acquire(self):
        ''' internal function to run acquisition in separate thread '''
        
        print "In _acquire()... at t=%f" % time.time()
        sys.stdout.flush()
        
        

        max_read_size = 16*16*1024
        act_read_size = ctypes.c_ulong(0)
        
        read_buf_type = ctypes.c_ulong*max_read_size
        read_buf = read_buf_type()
        
        total_counts = 0
        
        mem_prog_buf = ctypes.c_ulong(0)
        status_buf = ctypes.c_ushort(0)
        
        addr_at_last_read = 0
        
        self.start = time.time()
        last_update = time.time()
        
        skipped = 0
        loop_counter = 0
        
        counter=0 #counter_start

        t_wait_s = 0.1
        
        to_save = numpy.array([],dtype=ctypes.c_ulong)
        

        if self.process:
            proc = Processor(self.process_params)
            thd = threading.Thread(target=proc.master)
            thd.start()
        
        if self.save_old_format:
            conv = Converter()
            thd_conv = threading.Thread(target=conv.master)
            thd_conv.start()
        
            
        # HRM_STATUS WINAPI HRM_SetFrequencySelectionRegister(HANDLE handle,USHORT fsrData)
        status = self.sensl.HRM_SetFrequencySelectionRegister(self.h, 0x9999)

        # this should be 1 for free-running and 2 for resync mode
        # note that FSR also plays into this somehow...
        tt_mode = ctypes.c_ushort(1)
        

        #HRM_STATUS WINAPI HRM_RunFifoTimeTagging( HANDLE handle,
        #                                            USHORT ESRreg,
        #                                            USHORT microlsb
        #                                            USHORT mode)
        status = self.sensl.HRM_RunFifoTimeTagging(self.h, ctypes.c_ushort(0x5555), ctypes.c_ushort(0), tt_mode)
            
        #t_start = time.time()
        
        continue_after_this = True


        while continue_after_this:

            
            # decide if this will be our last run. Do this here because we want to save whatever data we have
            continue_time_ok = ((time.time() - self.start) < self.runtime or self.runtime < 0)
            continue_after_this = continue_time_ok and (self.force_stop is False)
            
            if continue_time_ok is False:
                print "Stopping acquisition after %d s..." % (time.time() - self.start)
                
            if self.force_stop is True:
                print "Forced acquistion stop after %d s..." % (time.time() - self.start)
            
            loop_counter += 1
            
            
            #HRM_STATUS WINAPI HRM_GetWriteCountRegister(HANDLE handle, ULONG *wrrData)
            status2 = self.sensl.HRM_GetWriteCountRegister(self.h, ctypes.byref(mem_prog_buf) )
            
            addr_delta = (mem_prog_buf.value - addr_at_last_read)
            
            mod_offset = 100
            mod_base = 1024
            
        
            #if is_power_of_two(mem_prog_buf.value & (2**12-1)) or is_power_of_two(mem_prog_buf.value):
            if mem_prog_buf.value % 16 == 0:
                # this is very important code that works around a bug in the SENSL FIFO driver.
                # without this fix the data acquisition will certainly crash after a few seconds
                
                if quiet < 1:
                    print "Skipping! addr=%d" % mem_prog_buf.value
                time.sleep(t_wait_s)
                #continue
                
            else:
                # if pointer is ok, read data
            
                addr_at_last_read = mem_prog_buf.value
                
                #HRM_STATUS WINAPI HRM_GetFifoData(HANDLE handle,
                #                                    USHORT mode, #1 for TT, 2 for TCSPC
                #                                    ULONG max,
                #                                    ULONG *size,
                #                                    ULONG *buffer)
                status = self.sensl.HRM_GetFifoData(self.h,
                                                ctypes.c_ushort(1),
                                                max_read_size,
                                                ctypes.byref(act_read_size),
                                                ctypes.byref(read_buf)
                                                )
                                                
                err = self.sensl.HRM_GetLastError(9999)
                
            
                
                
                #HRM_STATUS WINAPI HRM_GetStatusRegister(HANDLE handle, USHORT *srData)
                status3 = self.sensl.HRM_GetStatusRegister(self.h, ctypes.byref(status_buf))
                
                # this variable is in units of 32-bit integers. The number of bytes is total_counts*4
                # but the number of clicks is total_counts/2, since each click consists of 2 32-bit integers
                total_counts += act_read_size.value
                total_clicks = total_counts/2
                
                if act_read_size.value > 0:
                    to_save = numpy.append(to_save, read_buf[0:act_read_size.value])
                
            
            now = time.time()
            
            if quiet < 1:
                # this is mostly obscure debugging information
                print "Status = %d (%d,%d,%d,%d), total_counts = %d, delta=%d, skipped=%d" % (status, err, status2, status_buf.value, mem_prog_buf.value, total_clicks,addr_delta,skipped)
            elif now - last_update > 3:
                print "Have read %d counts in %.1f seconds, saved %d files" % (total_clicks,now-self.start,counter)
                last_update = now
                
        
            points_for_saving = len(to_save)
            
            if points_for_saving > self.target_filesize/4 or continue_after_this is False:
                # save file and reset to_save array. Do tihs if we have gotten to our target file size or if we are are quitting
                
                filename = self.save_prefix + '_' + str(counter) + '.bin'
                #filepath = os.path.join(SAVE_PATH,filename)
                f = open(filename,'wb')
                
                # it is crucially important to create a struct.Struct instead of just using struct.pack,
                # because of a known and unfixed memory issue in python
                # https://bugs.python.org/issue14596
                # could also use numpy.tofile, but we know this gives the right format...
                tempstruct = struct.Struct('@'+str(points_for_saving)+'I')
                f.write(tempstruct.pack(*to_save))
                #f.write(struct.pack('@'+str(points_for_saving)+'I',*to_save))
                f.close()

                
                print "Saved %d clicks in file %s" % (points_for_saving/8, filename)
                
                counter = counter+1
                
                del to_save
                
                to_save = numpy.array([],dtype=ctypes.c_ulong)
                
                if self.process:
                    proc_filenames = {'infile': filename, 'outfile': filename+'.mat' }
                    proc.q.put(proc_filenames)
                    #thd = threading.Thread(target=proc.process, kwargs={'infile': filepath, 'outfile': filepath + '.mat'} )
                    #thd.start()
                
                if self.save_old_format:
                    conv_filenames = {'infile': filename, 'outfile': filename+'.csv' }
                    conv.q.put(conv_filenames)
                    
                #if now-t_start > max_filetime:
                #    print "Timed out. Stopping acquisition!"
                #    break
                    
                #t_start = now
        
            if status_buf.value == 60936:
                print "FIFO error! Time elapsed = %f" % (time.time() - self.start)
                break
            
            #if counter_max > 0:
            #    if counter >= counter_max:
            #        break
            
            skipped = 0
        
            time.sleep(t_wait_s)
            sys.stdout.flush()
            
            #break
        
        self.running = False
        self.force_quit = False
        
        if self.process is True:
            
            #wait for processor to be done and then kill it
            proc.stop()
            
            print "Waiting for processor to quit"
            thd.join()
            #print "Deleting proc"
            del proc
        
        if self.save_old_format is True:
            
            #wait for processor to be done and then kill it
            conv.stop()
            
            #print "Waiting for processor to quit"
            thd_conv.join()
            #print "Deleting proc"
            del conv
        
        #gc.collect()
    

if __name__ == "__main__":
    from labrad import util
    util.runServer(HRMTime())

#os.execlp('python ',sys.argv[0])
#os.spawnv(os.P_NOWAIT,sys.executable, (sys.executable,sys.argv[0]) )
#os.execv(sys.executable, [sys.executable] + sys.argv)