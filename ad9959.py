import visa

import struct

from labrad import types as T, util
from labrad.server import LabradServer, Signal, setting
from Queue import Queue
import socket
import time, sys, shutil
import threading
from twisted.internet.defer import returnValue,inlineCallbacks
import visa



class AD9959_reg:

    reg = {}
    
    CLK_FREQ = 491.060 # in MHz

    # control function register

    # using parallel mode addresses
##    reg['clk_div_disable'] =    {'val': 0, 'len': 1, 'offset': 6, 'reg': 0}
##    reg['synclk_disable'] =     {'val': 0, 'len': 1, 'offset': 5, 'reg': 0}
##    reg['mixer_pd'] =           {'val': 1, 'len': 1, 'offset': 4, 'reg': 0}
##    reg['phd_pd'] =             {'val': 1, 'len': 1, 'offset': 3, 'reg': 0}
##    reg['pd'] =                 {'val': 0, 'len': 2, 'offset': 2, 'reg': 0}
##    reg['SDIO_input'] =         {'val': 0, 'len': 2, 'offset': 1, 'reg': 0}
##    reg['lsb_first'] =          {'val': 0, 'len': 2, 'offset': 0, 'reg': 0}
##
##    reg['freq_sweep_en'] =      {'val': 0, 'len': 1, 'offset': 7, 'reg': 1}
##    reg['sine_out_en'] =        {'val': 0, 'len': 1, 'offset': 6, 'reg': 1}
##    reg['cp_offset'] =          {'val': 0, 'len': 1, 'offset': 5, 'reg': 1}
##    reg['phd_div_N'] =          {'val': 0, 'len': 2, 'offset': 3, 'reg': 1}
##    reg['cp_pol'] =             {'val': 0, 'len': 1, 'offset': 2, 'reg': 1}
##    reg['phd_div_M'] =          {'val': 0, 'len': 2, 'offset': 0, 'reg': 1}
##
##    reg['aclr_freq_acc'] =      {'val': 0, 'len': 1, 'offset': 7, 'reg': 2}
##    reg['aclr_phi_acc'] =       {'val': 0, 'len': 1, 'offset': 6, 'reg': 2}
##    reg['load_dftw'] =          {'val': 0, 'len': 1, 'offset': 5, 'reg': 2}
##    reg['clrr_freq_acc'] =      {'val': 0, 'len': 1, 'offset': 4, 'reg': 2}
##    reg['clr_phi_acc'] =        {'val': 0, 'len': 1, 'offset': 3, 'reg': 2}
##    reg['fast_lock_en'] =       {'val': 0, 'len': 1, 'offset': 1, 'reg': 2}
##    reg['fast_lock_FTW'] =      {'val': 0, 'len': 1, 'offset': 0, 'reg': 2}
##
##    reg['fdm_cp_cur'] =         {'val': 0, 'len': 2, 'offset': 6, 'reg': 3}
##    reg['fclm_cp_cur'] =        {'val': 0, 'len': 3, 'offset': 3, 'reg': 3}
##    reg['wclm_cp_cur'] =        {'val': 0, 'len': 3, 'offset': 0, 'reg': 3}
    
    # using serial mode addresses
    # CSR
    reg['ch3_en'] =             {'val': 1, 'len': 1, 'offset': 7, 'reg': 0}
    reg['ch2_en'] =             {'val': 1, 'len': 1, 'offset': 6, 'reg': 0}
    reg['ch1_en'] =             {'val': 1, 'len': 1, 'offset': 5, 'reg': 0}
    reg['ch0_en'] =             {'val': 1, 'len': 1, 'offset': 4, 'reg': 0}
    reg['req0'] =               {'val': 0, 'len': 1, 'offset': 3, 'reg': 0}
    reg['SDIO_input'] =         {'val': 0, 'len': 2, 'offset': 1, 'reg': 0}
    reg['lsb_first'] =          {'val': 0, 'len': 1, 'offset': 0, 'reg': 0}

    # FR1
    reg['ref_pd'] =             {'val': 0, 'len': 1, 'offset': 7, 'reg': 1}
    reg['ext_pd'] =             {'val': 0, 'len': 1, 'offset': 6, 'reg': 1}
    reg['sync_clk_dis'] =       {'val': 0, 'len': 1, 'offset': 5, 'reg': 1}
    reg['ref_pd'] =             {'val': 0, 'len': 1, 'offset': 4, 'reg': 1}
    reg['open32'] =             {'val': 0, 'len': 2, 'offset': 2, 'reg': 1}
    reg['manual_hw_sync'] =     {'val': 0, 'len': 1, 'offset': 1, 'reg': 1}
    reg['manual_sw_sync'] =     {'val': 0, 'len': 1, 'offset': 0, 'reg': 1}
    
    reg['open15'] =             {'val': 0, 'len': 1, 'offset': 15, 'reg': 1}
    reg['ppc'] =                {'val': 0, 'len': 3, 'offset': 12, 'reg': 1}
    reg['ru_rd'] =              {'val': 0, 'len': 1, 'offset': 10, 'reg': 1}
    reg['mod_level'] =          {'val': 0, 'len': 2, 'offset': 8, 'reg': 1}
    
    reg['vco_gain'] =           {'val': 1, 'len': 1, 'offset': 23, 'reg': 1}
    reg['pll_div'] =            {'val': 20, 'len': 5, 'offset': 18, 'reg': 1}
    reg['cp_ctl'] =             {'val': 0, 'len': 2, 'offset': 16, 'reg': 1}
    
    # FR2
    reg['ach_sweep_auto_clr'] = {'val': 0, 'len': 1, 'offset': 15, 'reg': 2}
    reg['ach_sweep_clr'] =      {'val': 0, 'len': 1, 'offset': 14, 'reg': 2}
    reg['ach_phase_auto_clr'] = {'val': 0, 'len': 1, 'offset': 13, 'reg': 2}
    reg['ach_phase_clr'] =      {'val': 0, 'len': 1, 'offset': 12, 'reg': 2}
    reg['open1011'] =           {'val': 0, 'len': 2, 'offset': 10, 'reg': 2}
    reg['open98'] =             {'val': 0, 'len': 2, 'offset': 8, 'reg': 2}
    
    reg['auto_sync_en'] =       {'val': 0, 'len': 1, 'offset': 7, 'reg': 2}
    reg['multi_sync_en'] =      {'val': 0, 'len': 1, 'offset': 6, 'reg': 2}
    reg['multi_sync_status'] =  {'val': 0, 'len': 1, 'offset': 5, 'reg': 2}
    reg['multi_sync_mask'] =    {'val': 0, 'len': 1, 'offset': 4, 'reg': 2}
    reg['open32_2'] =           {'val': 0, 'len': 2, 'offset': 2, 'reg': 2}
    reg['sys_clk_off'] =        {'val': 0, 'len': 2, 'offset': 0, 'reg': 2}
    
    # CFR
    reg['afp_sel'] =            {'val': 0, 'len': 2, 'offset': 22, 'reg': 3}
    reg['open1612'] =           {'val': 0, 'len': 6, 'offset': 16, 'reg': 3}
    
    reg['lin_sweep_nodwell'] =  {'val': 0, 'len': 1, 'offset': 15, 'reg': 3}
    reg['lin_sweep_en'] =       {'val': 0, 'len': 1, 'offset': 14, 'reg': 3}
    reg['srr_ioud'] =           {'val': 0, 'len': 1, 'offset': 13, 'reg': 3}
    reg['open1112'] =           {'val': 0, 'len': 2, 'offset': 11, 'reg': 3}
    reg['req0_2'] =             {'val': 0, 'len': 1, 'offset': 10, 'reg': 3}
    reg['dac_fs_ctl'] =         {'val': 3, 'len': 2, 'offset': 8, 'reg': 3}
    
    reg['dig_pd'] =             {'val': 0, 'len': 1, 'offset': 7, 'reg': 3}
    reg['dac_pd'] =             {'val': 0, 'len': 1, 'offset': 6, 'reg': 3}
    reg['matched_delay'] =      {'val': 0, 'len': 1, 'offset': 5, 'reg': 3}
    reg['sweep_auto_clr'] =     {'val': 0, 'len': 1, 'offset': 4, 'reg': 3}
    reg['sweep_clr'] =          {'val': 0, 'len': 1, 'offset': 3, 'reg': 3}
    reg['phase_auto_clr'] =     {'val': 0, 'len': 1, 'offset': 2, 'reg': 3}
    reg['phase_clr'] =          {'val': 0, 'len': 1, 'offset': 1, 'reg': 3}
    reg['sin_out_en'] =         {'val': 1, 'len': 1, 'offset': 0, 'reg': 3}
    
    # FTW0
    reg['cftw_0'] =             {'val': 0, 'len': 32, 'offset': 0, 'reg': 4}
    
    # CPOW0
    reg['open_1415'] =          {'val': 0, 'len': 2, 'offset': 14, 'reg': 5}
    reg['cpow_0'] =             {'val': 0, 'len': 14, 'offset': 0, 'reg': 5}
    
    # ACR
    reg['arr'] =                {'val': 0, 'len': 8, 'offset': 16, 'reg': 6}
    
    reg['inc_dec_step'] =       {'val': 0, 'len': 2, 'offset': 14, 'reg': 6}
    reg['open_14'] =            {'val': 0, 'len': 1, 'offset': 13, 'reg': 6}
    reg['amp_mult_en'] =        {'val': 0, 'len': 1, 'offset': 12, 'reg': 6}
    reg['rurd_en'] =            {'val': 0, 'len': 1, 'offset': 11, 'reg': 6}
    reg['arr_ioud'] =           {'val': 0, 'len': 1, 'offset': 10, 'reg': 6}
    
    reg['asf'] =                {'val': 0, 'len': 10, 'offset': 0, 'reg': 6}
    
    # LSRR
    reg['fsrr'] =               {'val': 0, 'len': 8, 'offset': 8, 'reg': 7}
    reg['rsrr'] =               {'val': 0, 'len': 8, 'offset': 0, 'reg': 7}
    
    # RDW
    reg['rdw'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 8}
    
    # FDW
    reg['fdw'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 9}
    
    reg['cw1'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0xA}
    reg['cw2'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0xB}
    reg['cw3'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0xC}
    reg['cw4'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0xD}
    reg['cw5'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0xE}
    reg['cw6'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0xF}
    reg['cw7'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x10}
    reg['cw8'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x11}
    reg['cw9'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x12}
    reg['cw10'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x13}
    reg['cw11'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x14}
    reg['cw12'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x15}
    reg['cw13'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x16}
    reg['cw14'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x17}
    reg['cw15'] =                {'val': 0, 'len': 32, 'offset': 0, 'reg': 0x18}
    
    reglen = [8, #0
            24,#1
            16,#2
            24,#3
            32,#4
            16,#5,
            24,#6
            16,#7
            32,#8
            32,#9
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32,
            32] #0x18
    

    def get_register_val(self,regnum):
        # start with the control bits
        regstr = 0

        # now add the data...
        for k in self.reg.keys():
            v = self.reg[k]
            if v['reg'] == regnum:

                if (0 <= int(v['val']) <= 2**v['len']):
                    regstr += 2**v['offset'] * int(v['val'])
                else:
                    print "Illegal %s: %d (should have length %d)..." % (k, int(v['val']), v['len'])
        #print struct.pack('>I',int(regstr))
        
        #return struct.pack('b',int(regstr))
        return int(regstr)
    
    def get_register_cmd(self,regnum):
        # returns value of string to be sent over USB
        # format is array of bytes, with one bit of data per byte
        # 000<addr><data> where addr is 5 bytes and data is the length of the register
        
        array = [0,0,0]
        
        addr_array = [min(1,regnum & 2**n) for n in [4,3,2,1,0]]
        array.extend(addr_array)
        
        data = self.get_register_val(regnum)
        
        loop_idx = [x for x in range(self.reglen[regnum]) ]
        
        data_array = [int(min(1,data & 2**n)) for n in loop_idx[::-1] ]
        
        array.extend(data_array)
        
        return array

    def cmd_to_str(self,cmd):
        
        cmd_str = ''
        for x in cmd:
            cmd_str += format(x,'c')
        
        return cmd_str

    def print_regs(self):
        
        for i in range(0,4):
            print "=== Register %d ===" % i
            for k in self.reg.keys():
                

                v = self.reg[k]
                if v['reg'] == i:
                    print "%s: %d (offset: %d)" % (k, v['val'], v['offset'])

    def get_register_str(self,regnum,endian='small'):
        #regstr = regnum
        regstr = 0
        # now add the data...
        for k in self.reg.keys():
            v = self.reg[k]
            if v['reg'] == regnum:

                if (0 <= int(v['val']) <= 2**v['len']):
                    regstr += 2**v['offset'] * int(v['val'])
                else:
                    print "Illegal %s: %d (should have length %d)..." % (k, int(v['val']), v['len'])


        # need to know how long the register is, and this works fine
        if (regnum % 2) == 0 and regnum != 0:
            reglen = 16
        else:
            reglen = 32

        addrnum = 0*128 + regnum #0*128 specifies write mode

        if endian=='small':
            # this probably also needs to be modified to handle 16/32 bit registers, but we have no plans to use it at the moment...
            return struct.pack('<I',int(regstr))
        elif endian=='big':
            print "%d,%d" % (regnum,regstr)
            return struct.pack('>I',int(regstr))
        elif endian=='text':
            # will also have it tack the address on to the beginning
            if reglen == 32:
                return [addrnum, (regstr >> 24) & 255, (regstr >> 16) & 255, (regstr >> 8) & 255, (regstr >> 0) & 255]
            else:
                return [addrnum, (regstr >> 8) & 255, (regstr >> 0) & 255]
        else:
            unknown_endian_requtest = 1/0

#    def set_freq_profile(self, profile, freq):
#        """ given a profile number, set the FTW to freq (in MHz) """
#        FTW=(long)((freq/self.CLK_FREQ)*(2**32))
#
#        if profile == 0:
#            self.reg['ftw0']['val'] = FTW
#        if profile == 1:
#            self.reg['ftw1']['val'] = FTW
#        if profile == 2:
#            self.reg['ftw2']['val'] = FTW
#        if profile == 3:
#            self.reg['ftw3']['val'] = FTW
#
#        return FTW

#    def set_phase_profile(self, profile, phase):
#        """ given a profile number, set the FTW to freq (in MHz) """
#        POW=(long)(phase*2**14)
#
#        if profile == 0:
#            self.reg['pow0']['val'] = POW
#        if profile == 1:
#            self.reg['pow0']['val'] = POW
#        if profile == 2:
#            self.reg['pow0']['val'] = POW
#        if profile == 3:
#            self.reg['pow0']['val'] = POW

    def __setitem__(self,key,val):
        self.reg[key]['val'] = val
    
    def __getitem__(self,key):
        return self.reg[key]['val']

    def __init__(self):

        pass


class AD9959(LabradServer):
    """Server to program AD9959 4ch evaluation board (over USB) """
    name="AD9959"
    
    
    @setting(1,"ch_profile_two_level",ch="w",freq1="v[MHz]",freq2="v[MHz]")
    def ch_profile_two_level(self,c,ch,freq1,freq2):
        """ configures device for two-level frequency modulation with profile pins. Programs
        specified channel (ch) to two frequencies, where freq1 is active when profile pin is LOW"""
        
        visa_str = r'USB0::0x0456::0xEE25::NI-VISA-50004::RAW'
        #visa_str = r'USB0::0x0456::0xEE24::NI-VISA-10001::RAW'
        
        bulk_in = 0x3FFF01A3
        bulk_out = 0x3FFF01A2
        
        endpt_data_write = 0x04
        endpt_data_read = 0x88
        
        endpt_ctl_write = 0x01
        endpt_ctl_read = 0x81
        
        freq_MHz = 70.0
        freq2_MHz = 90.0
        sysclk_MHz = 491.060
        
        FTW = int(round(((2**32)*(freq1['MHz']/sysclk_MHz))))
        FTW2 = int(round(((2**32)*(freq2['MHz']/sysclk_MHz))))
        #ch = 3
                
        regs = AD9959_reg()
    
        regs['ch0_en'] = 0
        regs['ch1_en'] = 0
        regs['ch2_en'] = 0
        regs['ch3_en'] = 0
        
        if ch==0:
            regs['ch0_en'] = 1
        elif ch==1:
            regs['ch1_en'] = 1
        elif ch==2:
            regs['ch2_en'] = 1
        elif ch==3:
            regs['ch3_en'] = 1
        else:
            print "channel %d out of range!" % ch
            return 0
        
        regs['cftw_0'] = FTW
        
        regs['afp_sel'] = 2     # 0 = disabled, 1=amp, 2=freq, 3=phase
        regs['mod_level'] = 0    # 0 = 2-level, 1 = 4-level, 2 = 8-level, 3 = 16-level
        regs['ppc'] = 0         # doesn't matter for 2-level mod
        
        regs['cw1'] = FTW2
        
        rm = visa.ResourceManager()
        inst = rm.open_resource(visa_str)
        
        inst.write_termination = ''
        
        inst.set_visa_attribute(bulk_out,endpt_data_write)
        inst.set_visa_attribute(bulk_in,endpt_data_read)
        
        
        cmd_0 = regs.get_register_cmd(0)
        cmd_str_0 = regs.cmd_to_str(cmd_0)
        
        n = inst.write(cmd_str_0)
        print "Wrote %d bytes: %s" % (n[0],cmd_str_0)
        
        cmd_1 = regs.get_register_cmd(1)
        cmd_str_1 = regs.cmd_to_str(cmd_1)
        n = inst.write(cmd_str_1)
        print "Wrote %d bytes: %s" % (n[0],cmd_str_1)
        
        cmd_3 = regs.get_register_cmd(3)
        cmd_str_3 = regs.cmd_to_str(cmd_3)
        n = inst.write(cmd_str_3)
        print "Wrote %d bytes: %s" % (n[0],cmd_str_3)
        
        cmd_4 = regs.get_register_cmd(4)
        cmd_str_4 = regs.cmd_to_str(cmd_4)
        n = inst.write(cmd_str_4)
        print "Wrote %d bytes: %s" % (n[0],cmd_str_4)
        
        cmd_d = regs.get_register_cmd(0xA)
        cmd_str_d = regs.cmd_to_str(cmd_d)
        n = inst.write(cmd_str_d)
        print "Wrote %d bytes: %s" % (n[0],cmd_str_d)
        
        inst.set_visa_attribute(bulk_out,endpt_ctl_write)
        inst.set_visa_attribute(bulk_in,endpt_ctl_read)
        
        cmd_clear = '\x0C\x00'
        n = inst.write(cmd_clear)
        print "Wrote %d bytes: %s" % (n[0],cmd_clear)
        
        ret = inst.read()
        print "Read %s" % ret
        
        cmd_set = '\x0C\x10'
        n = inst.write(cmd_set)
        print "Wrote %d bytes: %s" % (n[0],cmd_set)
        
        ret = inst.read()
        print "Read %s" % ret

if __name__ == "__main__":
    from labrad import util
    util.runServer(AD9959())

    
