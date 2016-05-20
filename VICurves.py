# PyPV
#
# Copyright (C) 2015-2016 Ilario Gelmetti <iochesonome@gmail.com>
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

from numpy import *

def extractdata( voltage, current ):
    maxPower, voltageMaxPower, currentMaxPower= calcPower( voltage, current )
    jsc = calcJsc( voltage, current )
    voc = calcVoc( voltage, current )
    ff = maxPower / (jsc * voc)
    return maxPower, jsc, voc, ff, voltageMaxPower, currentMaxPower
    
def calcPower( voltage, current ):
    power = voltage * current
    maxPower = power.max()
    indexMaxPower = power.argmax()
    voltageMaxPower = voltage[indexMaxPower]
    currentMaxPower = current[indexMaxPower]
    return maxPower, voltageMaxPower, currentMaxPower

def calcJsc( voltage, current ):
    posJsc = abs(voltage).argmin()
    length = len(voltage)
    rangeJscStart, rangeJscStop = max(posJsc-3,0), min(posJsc+3,length)
    voltageJsc = voltage[rangeJscStart:rangeJscStop]
    currentJsc = current[rangeJscStart:rangeJscStop]
    fitJsc = polyfit(voltageJsc, currentJsc, 2)
    jsc = fitJsc[2]
    return jsc

def calcVoc( voltage, current ):
    posVoc = abs(current).argmin()
    length = len(voltage)
    rangeVocStart, rangeVocStop = max((posVoc-3),0), min(posVoc+3,length)
    voltageVoc = voltage[rangeVocStart:rangeVocStop]
    currentVoc = current[rangeVocStart:rangeVocStop]
    fitVoc = polyfit(currentVoc, voltageVoc, 2)
    voc = fitVoc[2]
    return voc
    
def calcSeriesResistance( voltage, current, compliance ):
    seriesResistance = "NotFound"
    while len(voltage) > 6: 
        print("voltage")
        print(len(voltage))  
        length = len(voltage)
        if current[length-6] > 0:
            break
        if (current[length-5] > current[length-4]) & (current[length-4] > current[length-3]) & (current[length-3] > current[length-2]) & (current[length-2] > current[length-1]) & (current[length-1] > -compliance):
            voltageSR = voltage[length-5:length]
            print(voltageSR)
            currentSR = current[length-5:length]
            print(currentSR)
            fitSR = polyfit(voltageSR, currentSR, 1)
            print(fitSR[0])
            seriesResistance = -1/fitSR[0]
            print seriesResistance
            break
        else:
            current = current[0:length-2]
            voltage = voltage[0:length-2]
    return seriesResistance
    
def calcParallelResistance( voltage, current ):
    posJsc = abs(voltage).argmin()
    length = len(voltage)
    rangePRStart, rangePRStop = max(posJsc-5,0), min(posJsc+6,length)
    voltagePR = voltage[rangePRStart:rangePRStop]
    currentPR = current[rangePRStart:rangePRStop]
    fitPR = polyfit(voltagePR, currentPR, 1)
    parallelResistance = -1/fitPR[0]
    print(parallelResistance)
    return parallelResistance
    
