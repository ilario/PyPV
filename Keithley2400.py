# Keithley 2400 Python library
#
# Copyright (C) 2015 Daniel Fernandez Pinto
#               2015-2016 Ilario Gelmetti <iochesonome@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
from visa import *
from time import sleep

class K2400():
    """ Keithley 2400 instrument class. """
    def __init__( self, address=24 ):
        rm = ResourceManager()
        instrumentName =str("GPIB::{0}::INSTR").format(address)
        self.ctrl = rm.open_resource(instrumentName)
        print(self.ctrl.query("*IDN?"))

    def reset(self):
        """ resets instrument """
        self.ctrl.write("*rst; status:preset; *cls")

    def close(self):
        """ closes the VISA instance (I think) """
        self.ctrl.close()

    def waitForMeasurementDone( self ):
        measurementDone = False
        notPassed = self.ctrl.query(":STAT:OPER:COND?")
        while measurementDone == False:
            try:
                query = self.ctrl.query(":STAT:OPER:COND?") 
                if query != notPassed:
                    measurementDone = True
                    print "passed measurement"
            except:
                sleep(0.1)
                measurementDone = False
                print "no measurement done"

    def splitData(self, inputData):
        voltage = []
        current = []
        for i in range(0, len(inputData)/5):
            voltage.append(inputData[i*5])
            current.append(inputData[i*5+1])
        return {'voltage':voltage, 'current':current} 

    def measureCurrent( self, numberOfPoints, compliance, setVoltage, integrationTime):    
        self.ctrl.write("*RST")
        self.ctrl.write(":SOUR:VOLT %lf" % setVoltage)
        self.ctrl.write(":SENS:FUNC 'CURR'")
        self.ctrl.write(":SENS:CURR:NPLC %lf" % integrationTime)
        self.ctrl.write(":SENS:CURR:PROT %lf" % compliance)
        self.ctrl.write(":TRAC:FEED SENS")
        self.ctrl.write(":TRAC:POIN %d" % numberOfPoints)
        self.ctrl.write(":TRAC:FEED:CONT NEXT")
        self.ctrl.write(":TRIG:COUN %d" % numberOfPoints)
        self.ctrl.write(":OUTP ON")
        self.ctrl.write(":INIT")
        self.waitForMeasurementDone()
        data = self.ctrl.query_ascii_values(":TRACE:DATA?")
        self.ctrl.write(":OUTP OFF")
        self.ctrl.write("*RST")
        data = self.splitData(data)
        return data
        

    def measureVoltage( self, numberOfPoints, compliance, setCurrent, integrationTime):
        self.ctrl.write("*RST")
        self.ctrl.write(":SOUR:FUNC CURR")
        self.ctrl.write(":SOUR:CURR:MODE FIXED")
        self.ctrl.write(":SENS:FUNC 'VOLT'")
        self.ctrl.write(":SENS:VOLT:PROT %lf" % compliance)
        self.ctrl.write(":SOUR:CURR:RANG MIN")
        self.ctrl.write(":SOUR:CURR:LEV %lf" % setCurrent)
        self.ctrl.write(":SENS:VOLT:NPLC %lf" % integrationTime)
        self.ctrl.write(":TRAC:FEED SENS")
        self.ctrl.write(":TRAC:POIN %d" % numberOfPoints)
        self.ctrl.write(":TRAC:FEED:CONT NEXT")
        self.ctrl.write(":TRIG:COUN %d" % numberOfPoints)
        self.ctrl.write(":OUTP ON")
        self.ctrl.write(":INIT")
        self.waitForMeasurementDone()
        data = self.ctrl.query_ascii_values(":TRACE:DATA?")
        self.ctrl.write(":OUTP OFF")
        self.ctrl.write("*RST")
        data = self.splitData(data)
        return data

    def measureIV( self, startVoltage, endVoltage, step, compliance, scaleValue, integrationTime, delayTime):

        self.ctrl.write("*RST")
        self.ctrl.write(":SENS:FUNC \"CURR\"")
        self.ctrl.write(":SENS:CURR:PROT %lf" % compliance)
        if scaleValue:
            self.ctrl.write(":SENS:CURR:RANG %lf" % scaleValue)
        else:
            self.ctrl.write(":SENS:CURR:RANG:AUTO ON")
        self.ctrl.write(":SOUR:FUNC VOLT")
        self.ctrl.write(":SOUR:VOLT:START %lf" % startVoltage)
        self.ctrl.write(":SOUR:VOLT:STOP %lf" % endVoltage)
        self.ctrl.write(":SOUR:VOLT:STEP %lf" % step)
        self.ctrl.write(":SOUR:VOLT:MODE SWE")
        self.ctrl.write(":SENS:VOLT:NPLC %lf" % integrationTime)
        self.ctrl.write(":TRAC:FEED SENS")
        self.ctrl.write(":TRAC:POIN %d" % (int(abs((startVoltage-endVoltage)/step)+1)))
        self.ctrl.write(":TRAC:FEED:CONT NEXT")
        self.ctrl.write(":TRIG:COUN %d" % (int(abs((startVoltage-endVoltage)/step)+1)))
        self.ctrl.write(":SOUR:DEL %lf" % delayTime)
        self.ctrl.write(":OUTP ON")
        self.ctrl.write(":INIT")
        
        self.waitForMeasurementDone()
        
        data = self.ctrl.query_ascii_values(":TRACE:DATA?")
        self.ctrl.write(":OUTP OFF")
        self.ctrl.write("*RST")
        data = self.splitData(data)
        self.beep()
        return data
            
    def beep(self):
        self.ctrl.write(":SYST:BEEP 2000, 0.1")
        
    def beep2(self):
        self.ctrl.write(":SYST:BEEP 1800, 0.2")

    def text(self, text):
        self.ctrl.write(":DISP:WIND:TEXT:DATA \'%s\'" % str(text))
        self.ctrl.write(":DISP:WIND:TEXT:STAT ON")
        
    def subtext(self, text):
        self.ctrl.write(":DISP:WIND2:TEXT:DATA \'%s\'" % str(text))
        self.ctrl.write(":DISP:WIND2:TEXT:STAT ON")
        
    def removetext(self):
        self.ctrl.write(":DISP:WIND:TEXT:STAT OFF")
        
    def removesubtext(self):
        self.ctrl.write(":DISP:WIND2:TEXT:STAT OFF")   
        
    def setlocal(self):
        self.ctrl.write(":SYST:LOC")
