from common import *

        
class initall(phase):
    def dophase(self,cxn,params,tstart):
        
        params['seq'] = int(params['seq'] + 1)
        cxn.registry().set('reg_seq',params['seq'])


    def getlength(self,params,tstart):
        return 0.0


# example
#class radial_freq_meas(phase):
#    # Pulse the dipole trap off twice with a variable time in between to try to measure the radial trap frequency
#    def dophase(self,cxn,params,tstart):
#        t1 = 1.5e-6
#        t2 = 6e-6
#        d['Scope_Trig'].PulseOn(tstart,10e-6)
#        d['Dipole_AOM'].PulseOff(tstart,t1)
#        d['Dipole_AOM'].PulseOff(tstart + t1 + params['t_pulse_off'],t2)
#        # this works well if you make the int_hold pulse about 2us longer than the AOM pulse on each side.
#        d['Dipole_AOM_Int_Hold'].PulseOn(tstart - 2e-6, t1+t2+params['t_pulse_off']+ 4.0e-6)
#        
#
#    def getlength(self,params,tstart):
#        return params['t_pulse_off'] + 20e-6

class runexpt(phase):
    def dophase(self,cxn,params,tstart):

        # here, we actually send commands to hardware, and wait for things to finish
        
        ## save paths
        saveName = ''
        for k in saveParams:
            if type(params[k]) == types.BooleanType:
                saveName += ",%s=%d" % (k,params[k])
            elif type(params[k]) == types.IntType:
                saveName += ",%s=%d" % (k,params[k])
            else:
                saveName += ",%s=%.4f" % (k,params[k])
        
        
        cxn.hrmtime.force_stop()
        
        ###### set pts
        if params['control_PTS'] is True:
            
            params['nDev_PTS'] = cxn.pts.is_connected()
            if params['nDev_PTS'] == 0:
                params['nDev_PTS'] = cxn.pts.start_control()
            
            if params['nDev_PTS'] != 2:
                print "Wrong number of PTS devices recognized: %d instead of 2" % params['nDev_PTS']
            
            
            cxn.pts.change_freq_slow(ptsProbe,T.Value(params['probe_freq_MHz'],'MHz'))
            cxn.pts.change_freq_slow(ptsControl,T.Value(params['ctl_freq_MHz'],'MHz'))
        
        
        ##### set up arbitrary waveform
        
        # times for probe and control shutoff
        # in microseconds
        t_mw = 0.3
        
        t1_start = 0
        t1_end = 0.860
        t2_start = t1_end + t_mw
        t2_end = t2_start + 0.3
        t3_start = t2_end + t_mw
        t3_end = t3_start + 0.4
        t4_start = t3_end + t_mw
        t4_end = t4_start + 1.0
        
        #t_store = 0.860
        #t_ = t_store + 0.35
        #t_read_end = t_read + 1.55 
        #t_final = t_read_end + 0.35
        #t_final_end = t_final + 1.0
        #
        #t_spike = 0.2
        
        pr_offset = 0.025
    
        
        ### control
        
        #cxn.agilent_arb_ctl.square_pulse(T.Value(3.0,'V'),         #Vhigh
        #                                T.Value(860+params['storage_time_ns'],'ns'),     #period
        #                                T.Value(860,'ns'),     #width
        #                                T.Value(5,'ns'),
        #                                2 )     #edge
        
        period = 5.0
        xList = numpy.linspace(0,period,501)
        
        def y(t):
            
            if t < t1_start:
                return 0
            
            elif t < t1_end:
                return params['ctl_store_V']
            elif t < t2_start:
                return 0
                
            elif t < t2_end:
                return params['ctl_store_V']
            elif t < t3_start:
                return 0
            
            elif t < t3_end:
                return params['ctl_store_V']
            elif t < t4_start:
                return 0
            
            elif t < t4_end:
                return params['ctl_store_V']
            
            else:
                return 0

                
        
        yList = [y(t) for t in xList]
        yList[0] = 0


        wfm_path = os.path.join(pathPrefixLocal,saveDir,'wfm_ctl_'+saveName+'.txt')
        f = open(wfm_path,'w')
        
        for i in range(len(xList)):
            f.write("%.5f,%.5f\n" % (xList[i],yList[i]))
        
        f.flush()
        f.close()
        
        cxn.agilent_arb_ctl.arb_from_file(wfm_path,
                                        T.Value(0.0,'V'),
                                        T.Value(3.0,'V'),
                                        T.Value(period,'us'),
                                        1 )
        
        ### probe
        period = 10
        xList = numpy.linspace(0,period,501)
        
        #t0_first = t_store
        w_first = 0.001*params['probe_rms_ns']# 0.23
        t_probe_offset_1 = -0.02 #0.001*params['store_offset_ns']
        t_probe_offset_2 = 0.16
        
        #t0_second = 1.65 #1.9
        #t_readout_hold = 0.0 #0.25
        #t_read_cutoff=0.35
        
        amp_store = params['store_V']
        amp_readout = params['readout_V']
        
        def y(t):
            #if t < t0_first + 2*w_first:
            #    return amp_store*numpy.exp(-(t-t0_first)**2/(2*w_first**2))
            
            if t < t1_end:
                return amp_store*numpy.exp(-(t-t1_end+t_probe_offset_1)**2/(2*w_first**2))
            elif t < t2_start:
                return 0
            
            elif t < t2_end:
                return amp_store*numpy.exp(-(t-t2_end+t_probe_offset_2)**2/(2*w_first**2))
            elif t < t3_start:
                return 0
            else:
                return 0
                
        
        yList = [y(t-pr_offset) for t in xList]
        #yList[-2] = 1
        
        wfm_path = os.path.join(pathPrefixLocal,saveDir,'wfm_'+saveName+'.txt')
        f = open(wfm_path,'w')
        
        for i in range(len(xList)):
            f.write("%.5f,%.5f\n" % (xList[i],yList[i]))
        
        f.flush()
        f.close()
        
        cxn.agilent_arb.arb_from_file(wfm_path,
                                        T.Value(0.0,'V'),
                                        T.Value(3.0,'V'),
                                        T.Value(period,'us'),
                                        1 )
        
        
      ###Microwave Pi Pulse
        pi_offset = 0.01;
        pi_width = 0.01;
        
        def y(t):
            
            if t < t1_end:
                return 0
            
            elif t < t1_end+pi_width:
                return params['ctl_store_V']
                
            elif t < t2_end:
                return 0
                
            elif t < t2_end+pi_width:
                return params['ctl_store_V']
                
            elif t < t3_end:
                return 0
                
            elif t < t3_end+pi_width:
                return params['ctl_store_V']
                       
            else:
                return 0
        
        
        yList = [y(t-pi_offset) for t in xList]
        yList[-2] = 1
        
        wfm_path = os.path.join(pathPrefixLocal,saveDir,'wfm_pi'+saveName+'.txt')
        f = open(wfm_path,'w')
        
        for i in range(len(xList)):
            f.write("%.5f,%.5f\n" % (xList[i],yList[i]))
        
        f.flush()
        f.close()
               
        cxn.agilent33500b.arb_from_file(1,wfm_path,
                                        T.Value(0.0,'V'),
                                        T.Value(3.0,'V'),
                                        T.Value(period,'us'),
                                        1 )
      
        
        #####
        
        #cxn.agilent_arb.square_pulse(T.Value(1.5,'V'),         #Vhigh
        #                                T.Value(38.0,'us'),     #period
        #                                T.Value(params['arb_width_us'],'us'),     #width
        #                                T.Value(3.0,'us') )     #edge
        
        
        
        ###### microwave frequency, power
        cxn.agilente8257d.set_freq(T.Value(params['uw_freq_MHz'],'MHz'))
        cxn.agilente8257d.set_pow(T.Value(params['uw_pow_dBm'],'dBm'))
        

        ###### microwave pulse parameters
        cxn.SRS_DG535.set_delay_a(T.Value(950-0*800,'ns'))
        cxn.SRS_DG535.set_delay_ab(T.Value(params['uw_tpi_ns'],'ns'))
        cxn.SRS_DG535.set_delay_cd(T.Value(params['uw_tpi_ns'],'ns'))
        cxn.SRS_DG535.set_delay_bc(T.Value(params['uw_pulse_sep_ns']-params['uw_tpi_ns'],'ns'))
        
        #cxn.agilent33500b.square_pulse_n(1,T.Value(2.0,'V'),
        #                                        T.Value(0.0,'V'), 
        #                                        T.Value(params['uw_pulse_sep_ns'],'ns'),
        #                                        T.Value(params['uw_tpi_ns'],'ns'),
        #                                        T.Value(10,'ns'),1)
        #
        #
        #cxn.AD9959.ch_profile_two_level(3,
        #                            T.Value(80.0 - params['probe_DDS_offset_MHz'],'MHz'), # TTL low value
          #                          T.Value(80.0,'MHz')                             # high value
          #                          )
                                    
        # let everything settle before starting integration. Mostly for arbitrary wfm
        time.sleep(3.0)
        
        cxn.hrmtime.acquire(os.path.join(pathPrefixRemote,saveDir,'hrm_'+saveName), T.Value(params['acquisition_time_s'],'s') )
        
        print "Started acquisition %s, now waiting for %d seconds..." % (saveName,params['acquisition_time_s'])
        
        sys.stdout.flush()
        
        time.sleep(params['acquisition_time_s'])
        
        hrmtime_wait_counter = 0
        while cxn.hrmtime.is_running() == 1:
            hrmtime_wait_counter += 1
            if hrmtime_wait_counter % 10 == 0:
                print "Waiting for hrm acquisition to finish..."
                
            time.sleep(0.1)
        
        #save_params
        #save_waveform
        
        

        
########### Actual execution starts here ##########
## general variables
cxn = labrad.connect("localhost",password="")
params={}

# get the last sequence number from the registry
try:
    reg_seq = cxn.registry().get('reg_seq')
    params['seq'] = int(math.ceil(long(reg_seq)*0.01)*100+100)
    reload(sys.modules['channels'])
    reload(sys.modules['calibrations'])

except:
    params['seq'] = 100
    cxn.registry().set('reg_seq',params['seq'])
    

pathPrefixLocal = r'Z:\RoyOutput\Dropbox (MIT)\HRMTimeData'
pathPrefixRemote = r'C:\Users\RoyOutput\Dropbox (MIT)\HRMTimeData'

saveDir = r'2015-10\20151014\run6'
nRepeats = 1

# elements from params which should be added to saved file names
#saveParams = ['seq','two_phot_MHz','s_or_p','ctl_read_V','readout_V']
saveParams = ['seq','uw_freq_MHz','uw_tpi_ns','probe_rms_ns','store_offset_ns']

# params def
params['acquisition_time_s'] = 20
params['control_PTS'] = False
params['use_HRMTime'] = True

params['ctl_store_V'] = 1.0
params['ctl_read_V'] = 1.0 #0.65
params['ctl_spike_V'] = 1.0
prfreqs = numpy.linspace(1620,1750,131)
#prfreqs = numpy.union1d(numpy.linspace(1620,1750,66),numpy.linspace(1661,1701,21))

readout_V_pts = [0,0.189024, 0.219065, 0.246743, 0.272724, 0.297432, 0.321162,
0.344129, 0.409947, 0.473348, 0.536506, 0.601512, 0.671173, 0.750863,
0.85866]

readout_V_pts = [0,0.189024, 0.272724,
0.344129, 0.409947, 0.473348, 0.536506, 0.601512, 0.671173, 0.750863,
0.85866]

iterlist = [

    #['ctl_freq_MHz',[2436.9]],# + numpy.linspace(5,25,5)],
    #['probe_freq_MHz',[1677]],
    #['uw_freq_MHz',numpy.linspace(-1,1,30)+11383.823],
    ['uw_freq_MHz',[3718.2 -1000]],
    #['uw_tpi_ns',[1000]],
    ['uw_tpi_ns',[130]],
    ['uw_pow_dBm',[5]],
    ['readout_V',[0*0.25]],#Zero this to remove middle pulse
    ['store_V',[0.25]],
    ['t_store_offset_us',[0.0]],
    ['arb_width_us',[14]],
    ['ctl_read_V',[1.0]],
    ['probe_rms_ns',[60]],
    ['uw_pulse_sep_ns',[1900]],
    ['store_offset_ns',numpy.linspace(-120,220,18)],

    #['two_phot_MHz',[0]],#,numpy.linspace(-3,3,7)],
    #['s_or_p',[1,0]],

    
   # ['storage_time_ns',numpy.linspace(200,7000,17)],

]


def itercond(params):
    
#    print "Set ctl delay to %f (pulse blaster time = %f)" % (params['ctl_probe_delay_ns'],800+params['ctl_probe_delay_ns'])
#    raw_input() # wait for user to press enter

  #  if params['ctl_read_V'] != 1.0 and params['s_or_p']==0:
   #     return False
    
    #params['probe_freq_MHz'] = 1677 - params['two_phot_MHz']
    #params['probe_DDS_offset_MHz'] = (1.0*params['two_phot_MHz'])/2.0

#    if params['s_or_p'] == 0:
#        # parameters for 99S1/2 two-photon
#        params['uw_freq_MHz'] = 3675.96
#        params['uw_tpi_ns'] = 208
#        params['uw_pow_dBm'] = 2
#    
#    else:
#        # parameters for 99P3/2
#        params['uw_freq_MHz'] = 3717.71
#        params['uw_tpi_ns'] = 180
#        params['uw_pow_dBm'] = -8

    return True



# copy this script to location where data is saved, prefixed with sequence number
scriptname=inspect.getfile(inspect.currentframe())
shutil.copyfile(scriptname,os.path.join(pathPrefixLocal,saveDir,str(params['seq'])+'_'+os.path.basename(scriptname)))



def meas(params):

    #example    
    #phases=[S,[P,[S,startmeas,ramp_bfield_up,optpumpprep,raman_cooling],ramp_probe_up],move_to_tip,hold_at_tip,[P,[S,move_back_to_load,blaster,ramp_dipole_to_load_depth,ramp_bfield_down],ramp_probe_down]]

    phases = [S]

    t_beg = 0
    t_meas_len = t_beg + dophaseloop(phases,cxn,params,t_beg,False)

#    params['t_raman_end'] = t_beg + dophaseloop([S,startmeas,ramp_bfield_up,optpumpprep,raman_cooling],cxn,params,t_beg,False)
    
    params['t_meas_end'] = t_meas_len # total length
    
    #print "measurement length=",t_meas_len
    initall().dophase(cxn,params,t_beg)
    
    dophaseloop(phases,cxn,params,t_beg,True)

    runexpt().dophase(cxn,params,t_beg)


for i in range(0,nRepeats):
    # this is the minimal thing
    doloop(meas,params,iterlist,itercond)

cxn.disconnect()

#execfile("716600_pc_current__reprate_pc16.py")