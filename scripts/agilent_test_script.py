import labrad
cxn = labrad.connect()
cxn #Gives available servers
#cxn.manager #Gives different parts of "manager" server
#cxn.manager.echo("hi there") #Test connection to manager server
