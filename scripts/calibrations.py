import math
import csv, os, numpy
from datetime import date

allCalibrationData = {}

# example of how to use get_interpolation_from_data
def probe_offset_lock_detuningMHz_in_V(det):
    """ gives voltage for probe AOM offset lock, to achieve a certain detuning from the atomic resonance (in MHz)
        the resonance is at 382 MHz  """

    # updated 130322 - new calibration and using standard system rather than copying interpolated function from mathematica

    return get_interpolation_from_data_x_from_y(det,'probe_lock_V_MHz')


## calibration functions

def get_interpolation_from_data_x_from_y(y, dataset):
    if (dataset in allCalibrationData):
        # it's already loaded
        data=allCalibrationData[dataset]
    else:
        try:
            import_calibration_data(".\\calibrationData\\"+dataset+".csv")
        except IOError:
            # maybe we are in the programs directory
            import_calibration_data(".\\..\\scripts\\calibrationData\\"+dataset+".csv")
        except IOError:
            # maybe we are in the programs directory on Lukin-B02
            import_calibration_data(".\\..\\..\\scripts\\calibrationData\\"+dataset+".csv")
        data=allCalibrationData[dataset]
        
    yData = numpy.transpose(data)[1]

    if (y>max(yData)):
        raise("value %f is out of bounds! maximum value is %f" % (y,max(yData)))
              
    if (y<min(yData)):
        raise("value %f is out of bounds! minimum value is %f" % (y,min(yData)))
        
    for i in (range(len(data)-1)):
        if (y==data[i][1]):
            x=data[i][0]
            break
        if ((y>data[i][1]) and (y<data[i+1][1])):
            x=data[i][0]+(data[i+1][0]-data[i][0])*((y-data[i][1])/(data[i+1][1]-data[i][1]))
            break

    if (y==data[-1][1]):
        x=data[-1][0]
    return x

def import_calibration_data(filename):
    global allCalibrationData
    data=[]
    dataset_name=os.path.basename(filename).split('.')[0]
    q=csv.reader(open(filename,'r'))
    for row in q:
        for i in range(len(row)):
            row[i]=float(row[i])
        data.append(row)

    allCalibrationData[dataset_name] = sorted(data)

#def get_todays_dir():
#    d=date.today()
#    sr="z:\\MOT\\Daily\\"+d.strftime("%y%m")+"\\"+d.strftime("%y%m%d")+"\\"
#    return sr

