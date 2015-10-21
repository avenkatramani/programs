import numpy

period = 20

xList = numpy.linspace(0,20,1001)

t0_first = 1
w_first = 0.23

t0_second = 2.1

t_readout_hold = 0.05

amp_store = 0.3
amp_readout = 1

def y(t):
        
    if t < 1.5:
        return amp_store*numpy.exp(-(t-t0_first)**2/(2*w_first**2))
    elif t < t0_second:
        return amp_readout*numpy.exp(-(t-t0_second)**2/(2*w_first**2))
    elif t < t0_second + t_readout_hold:
        return amp_readout
    else:
        readout_falling_center = t0_second + t_readout_hold
        return amp_readout*numpy.exp(-(t-readout_falling_center)**2/(2*w_first**2))

yList = [y(t) for t in xList]
yList[-2] = 1

f = open('wfm.txt','w')

for i in range(len(xList)):
    f.write("%.5f,%.5f\n" % (xList[i],yList[i]))

f.close()