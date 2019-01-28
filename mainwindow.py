# PyPV
#
# Copyright (C) 2015 Daniel Fernandez Pinto
#               2015-2017 Ilario Gelmetti <iochesonome@gmail.com>
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

from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import matplotlib.pyplot as plt
from numpy import *
import os
import unicodedata
import VICurves
from time import sleep
import datetime
from multiprocessing import Process

import Keithley2400
TEST_MODE = False   # for test mode comment out also "import Keithley2400"


(Ui_MainWindow, QMainWindow) = uic.loadUiType('mainwindow.ui')

NUM_CURRENT_POINTS = 3
CURRENT_POSITIVE = 0
IRRADIANCE_UNIT_MULTIPLIER = 0.001


def plot_graph(
        imageName, voltage, adjCurrent, voltageMaxPower,
        currentMaxPower, Voc, printVoc, Jsc, JscDensity, FF, efficiency,
        saveImage, directory):
    fig = plt.figure(imageName)
    fig.suptitle(imageName, fontsize=14, fontweight='bold')
    ax = fig.add_subplot(111)
    fig.subplots_adjust(top=0.85)
    ax.set_xlabel('Voltage (V)')
    ax.set_ylabel('Current (mA)')
    ax.plot(voltage, adjCurrent)
    ax.plot(voltageMaxPower, currentMaxPower, 'ro')
    if printVoc:
        ax.plot(Voc, 0, 'r+')
    ax.plot(0, Jsc, 'r+')
    ax.axhline(0, color='k')
    ax.axvline(0, color='k')
    ymin, ymax = plt.ylim()
    ax.set_yticks(
            arange(
                    int(min(minimum(adjCurrent, -2)) * 2),
                    int(max(maximum(adjCurrent, 2)) * 2), 0.5),
            minor='True')
    ax.yaxis.grid(True, which='minor')
    ax.set_ylim(ymin, ymax)
    xmin, xmax = plt.xlim()
    ax.set_xticks(arange(-20, 20, 0.2), minor='True')
    ax.xaxis.grid(True, which='minor')
    ax.set_xlim(xmin, xmax)

    legend = (
            "Voc " + Voc + " V\nJsc " + JscDensity + " mA/cm2\nFF " + FF +
            "\nEfficiency " + efficiency + " %")
    ax.text(
            0.05, 0.05, legend, verticalalignment='bottom',
            horizontalalignment='left', transform=ax.transAxes, fontsize=14,
            bbox=dict(facecolor='pink', alpha=0.9, pad=10))

    if saveImage:
        imageNameWithDirectory = os.path.join(directory, imageName)
        plt.savefig(imageNameWithDirectory + ".png")
        plt.close()
    else:
        plt.show()


class MainWindow (QMainWindow):
    """MainWindow inherits QMainWindow"""

    def __init__(self, parent=None):

        if not TEST_MODE:
            print("Checking if Keithley is connected...")

        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        if os.path.isfile('last_configuration.lnk'):
            with open('last_configuration.lnk') as f:
                conf = f.read().splitlines()
            extendedConf = 0
            self.applyConf(conf, extendedConf)

        self.connect(
                self.ui.runButton, SIGNAL('clicked()'),
                SLOT('clickMeasure_IV()'))
        self.connect(
                self.ui.vocButton, SIGNAL('clicked()'),
                SLOT('clickMeasure_V()'))
        self.connect(
                self.ui.stopButton, SIGNAL('clicked()'),
                SLOT('clickStop()'))
        self.connect(
                self.ui.saveAsButton, SIGNAL('clicked()'),
                SLOT('clickSaveAs()'))
        self.connect(
                self.ui.autoSaveButton, SIGNAL('clicked()'),
                SLOT('clickAutoSave()'))
        self.connect(
                self.ui.runListButton, SIGNAL('clicked()'),
                SLOT('clickRunList()'))
        self.connect(
                self.ui.runAutoMeasureButton, SIGNAL('clicked()'),
                SLOT('clickAutoMeasure()'))
        self.connect(
                self.ui.autoScale_check, SIGNAL('clicked()'),
                SLOT('clickAutoScale()'))
        self.connect(
                self.ui.stepV_edit, SIGNAL('editingFinished()'),
                SLOT('calcScanSpeed()'))
        self.connect(
                self.ui.integrationTime_edit, SIGNAL('editingFinished()'),
                SLOT('calcScanSpeed()'))
        self.connect(
                self.ui.delayTime_edit, SIGNAL('editingFinished()'),
                SLOT('calcScanSpeed()'))

        self.isTriggerOpen = False
        if not TEST_MODE:
            self.smu = Keithley2400.K2400()
            self.smu.text("Welcome to PyPV")
            self.smu.subtext("")
            self.smu.shutterClose()
            sleep(2)
            self.smu.setlocal()
        self.currentUnitMultiplier = 1000
        self.ui.data_table.setColumnCount(10)
        labels = (
                'Device', 'Diode', 'Reverse?', 'Jsc', 'Voc', 'FF',
                'efficiency', 'int time', 'delay', 'irradiance')
        self.ui.data_table.setHorizontalHeaderLabels(labels)
        self.date = datetime.date.today()
        self.showImage = 1
        self.currentImagePid = 0
        self.terminateCurrentImage = 0

        self.unsavedData = False
        logHeader = self.date, ""
        with open("measurements_log.txt", 'a') as f_handle:
            savetxt(f_handle, logHeader, fmt='%s')

        self.calcScanSpeed()

    def applyConf(self, conf, extendedConf):
        self.ui.user_edit.setText(str(conf[0]))
        self.ui.experiment_edit.setText(str(conf[1]))
        self.ui.startV_edit.setText(str(conf[2]))
        self.ui.endV_edit.setText(str(conf[3]))
        self.ui.stepV_edit.setText(str(conf[4]))
        self.ui.compliance_edit.setText(str(conf[5]))
        self.ui.scale_combo.setCurrentIndex(int(conf[6]))
        self.ui.integrationTime_edit.setText(str(conf[7]))
        self.ui.cellArea_edit.setText(str(conf[8]))

        if extendedConf:
            self.ui.autoScale_check.setCheckState(int(conf[9]))
            self.ui.irradiance_edit.setText(str(conf[10]))
            self.ui.device_edit.setText(str(conf[11]))
            self.ui.diode_spin.setValue(int(conf[12]))
            self.ui.reverse_check.setCheckState(int(conf[13]))
            self.ui.autoSaveImages_check.setCheckState(int(conf[14]))
            self.ui.preDelayOff_edit.setText(int(conf[15]))
            self.ui.preDelayOn_edit.setText(int(conf[16]))

    def __del__(self):
        print("Saving conf...")
        try:
            (user, experiment, device, diode, cellArea,
                irradiance) = self.getDeviceIdentification()
        except:
            user = "guest"
            experiment = "exp1"
        closingConf = (
                user, experiment, self.ui.startV_edit.text(),
                self.ui.endV_edit.text(), self.ui.stepV_edit.text(),
                self.ui.compliance_edit.text(),
                str(self.ui.scale_combo.currentIndex()),
                self.ui.integrationTime_edit.text(),
                self.ui.cellArea_edit.text())

        with open('last_configuration.lnk', 'w') as f_handle:
            savetxt(f_handle, closingConf, fmt='%s')
        sleep(0.5)
        self.ui = None

    @pyqtSlot()
    def clickMeasure_IV(self):
        self.ui.LCD_Jsc.setDigitCount(5)
        self.ui.LCD_Voc.setDigitCount(5)
        self.ui.LCD_PCE.setDigitCount(5)
        self.ui.LCD_FF.setDigitCount(5)

        try:
            self.startV = float(self.ui.startV_edit.text())
            self.endV = float(self.ui.endV_edit.text())
            self.reverse = int(self.ui.reverse_check.isChecked())
            self.stepV = float(self.ui.stepV_edit.text())
            self.compliance = float(self.ui.compliance_edit.text())
            autoScale = int(self.ui.autoScale_check.isChecked())
            if autoScale:
                self.scale = False
            else:
                self.scale = float(self.ui.scale_combo.currentText())
            self.integrationTime = float(self.ui.integrationTime_edit.text())
            self.delayTime = float(self.ui.delayTime_edit.text())
            self.cellArea = float(self.ui.cellArea_edit.text())
            self.preDelayOff = float(self.ui.preDelayOff_edit.text())
            self.preDelayOn = float(self.ui.preDelayOn_edit.text())
        except:
            print "Values must be valid numbers"

        if self.unsavedData:
            unsavedAnswer = QMessageBox.warning(
                    self, "Unsaved Measurement",
                    "There is an unsaved measurement. Do you really want to "
                    "continue with next measurement?",
                    QMessageBox.Yes | QMessageBox.Abort, QMessageBox.Yes)
            if unsavedAnswer == QMessageBox.Yes:
                self.unsavedData = False

        endVstartV = self.startV * self.endV
        if endVstartV <= 0:
            crossingZero = True
        else:
            crossingZero = False
            crossingAnswer = QMessageBox.question(
                    self,
                    "Scan not Crossing Zero Voltage",
                    "The specified voltage scanning range does not cross "
                    "zero, are you sure the range is ok?",
                    QMessageBox.Yes | QMessageBox.Abort, QMessageBox.Yes)
            if crossingAnswer == QMessageBox.Yes:
                crossingZero = True

        if crossingZero and not self.unsavedData:
            if TEST_MODE:
                testFile = "test/good-1-1-reverse.txt"
                # testFile = "test/bad-1-1-forward.txt"
                # testFile = "test/ugly-1-1-forward.txt"
                self.voltage, self.current = loadtxt(
                        testFile, skiprows=25,
                        unpack=True)
                self.current = self.current / self.currentUnitMultiplier
            else:
                self.smu.reset()
                if self.preDelayOff:
                    subtext = "Shutter Delay Off %s s" % str(self.preDelayOff)
                    print subtext
                    self.smu.subtext(subtext)
                    sleep(self.preDelayOff)

                self.smu.shutterOpen()
                if self.preDelayOn:
                    subtext = "Shutter Delay On %s s" % str(self.preDelayOn)
                    print subtext
                    self.smu.subtext(subtext)
                    sleep(self.preDelayOn)
                self.smu.removetext()
                self.smu.removesubtext()

                if self.reverse:
                    data = self.smu.measureIV(
                            self.endV, self.startV,
                            -self.stepV, self.compliance,
                            self.scale, self.integrationTime,
                            self.delayTime)
                else:
                    data = self.smu.measureIV(
                            self.startV, self.endV,
                            self.stepV, self.compliance,
                            self.scale, self.integrationTime,
                            self.delayTime)
                self.smu.shutterClose()
                self.voltage, self.current = (
                        array(data['voltage']),
                        array(data['current']))

            data2 = self.voltage, self.current * self.currentUnitMultiplier
            self.data3 = transpose(data2)

            savetxt('last_measurement_raw.txt', self.data3)

            self.unsavedData = True
            self.setSaved(0)

            (self.maxPower, self.jsc, tempVoc, tempFf, self.voltageMaxPower,
                self.currentMaxPower) = VICurves.extractdata(
                    self.voltage, self.current * (CURRENT_POSITIVE * 2 - 1))
            self.voc = "%.4g" % (tempVoc)
            self.ff = "%.3g" % (tempFf)
            self.jscDensity = "%.4g" % (self.jsc * self.currentUnitMultiplier /
                                        self.cellArea)
            self.currentMaxPowerDensity = "%.4g" % (
                    self.currentMaxPower *
                    self.currentUnitMultiplier /
                    self.cellArea)

            self.calcEfficiencyAndSetLCDs()

            (user, experiment, device, diode, cellArea,
                irradiance) = self.getDeviceIdentification()
            if self.reverse:
                self.reverseText = "reverse"
            else:
                self.reverseText = "forward"

            self.maxVoltage = self.voltage.max()
            self.minVoltage = self.voltage.min()

            self.save(
                    'last_measurement.txt', user, experiment, device, diode,
                    cellArea, irradiance)

            if not float(irradiance):
                self.printVoc = 0
            else:
                self.printVoc = 1
                if (
                        tempVoc < self.minVoltage or
                        tempVoc > self.maxVoltage or
                        self.current[0] /
                        abs(self.current[0]) == self.current[-1] /
                        abs(self.current[-1])):
                    self.printVoc = 0
                    QMessageBox.warning(
                            self, "Voc not reached",
                            "This scan didn't pass by the Voc! You should "
                            "repeat the measurement using a wider voltage "
                            "range.",
                            QMessageBox.Ok, QMessageBox.Ok)

            if self.showImage:
                saveImage = 0
                self.makeImage(saveImage, "")

    @pyqtSlot()
    def clickMeasure_V(self):
        self.isTriggerOpen = True
        self.ui.LCD_Voc.setDigitCount(5)
        while self.isTriggerOpen:
            voltage = self.measure_V()
            self.ui.LCD_Voc.display(voltage)
            print(voltage)
            QApplication.processEvents()

    def measure_V(self):
        self.smu.reset()
        self.smu.removetext()
        self.smu.removesubtext()
        self.smu.shutterOpen()
        measurements = self.smu.measureVoltage(5, 10.0, 0, 5)
        voltage = average(measurements["voltage"])
        self.smu.shutterClose()
        return voltage

    @pyqtSlot()
    def clickStop(self):
        self.isTriggerOpen = False

    @pyqtSlot()
    def clickRunList(self):
        fileName = QFileDialog.getOpenFileName(
                self, 'Open Parameters List File')
        if os.path.isfile(fileName):
            print(fileName)
            self.isTriggerOpen = True
            conf = genfromtxt(str(fileName), skip_header=1, dtype='str')
            extendedConf = 1
            self.showImage = 1
            self.terminateCurrentImage = 1
            for i in range(len(conf)):
                self.applyConf(conf[i], extendedConf)
                if not self.isTriggerOpen:
                    break
                self.displayDiode()
                self.clickMeasure_IV()
                self.clickAutoSave()

                waitBeforeNext = int(conf[i][17])
                if waitBeforeNext:
                    self.saveProblem = False
                    subtext = "Waiting for user interaction"
                    print subtext
                    self.smu.subtext(subtext)
                    continueWithNextAnswer = QMessageBox.question(
                            self, "Next measurements block",
                            "A block of measurements is completed, should "
                            "continue with the next ones?",
                            QMessageBox.Yes | QMessageBox.Abort,
                            QMessageBox.Yes)
                    if continueWithNextAnswer == QMessageBox.Abort:
                        self.terminateCurrentImage = 0
                        self.smu.subtext("Measurements list completed")
                        break
            self.terminateCurrentImage = 0
            self.smu.subtext("Measurements list completed")

    @pyqtSlot()
    def clickAutoMeasure(self):
        self.isTriggerOpen = True
        self.showImage = 1
        self.terminateCurrentImage = 1
        self.ui.LCD_Voc.setDigitCount(5)

        self.ui.reverse_check.setCheckState(0)
        maxVoltages = [0, 0, 0, 0]

        for i in (0, 1, 2, 3):
            self.ui.diode_spin.setValue(int(i) + 1)
            self.displayDiode()
            voltage = self.measure_V()
            self.smu.shutterClose()
            if voltage < float(self.ui.startV_edit.text()):
                lowVocAnswer = QMessageBox.warning(
                        self, "Voc lower than starting V",
                        "The measured Voc is lower than the starting scan "
                        "voltage. Check the cable connections or the lower "
                        "voltage parameter. Do you want to perform anyway "
                        "this measurement?",
                        QMessageBox.Yes | QMessageBox.Cancel,
                        QMessageBox.Cancel)
                if lowVocAnswer == QMessageBox.Cancel:
                    break
            approxVoltage = "%.1f" % (float(voltage))
            maxVoltages[i] = max(0, float(approxVoltage)) + 0.2
            self.ui.endV_edit.setText(str(maxVoltages[i]))

            self.ui.reverse_check.setCheckState(0)
            QApplication.processEvents()
            self.clickMeasure_IV()
            self.clickAutoSave()
            QApplication.processEvents()
            self.ui.reverse_check.setCheckState(1)
            self.clickMeasure_IV()
            self.clickAutoSave()
            QApplication.processEvents()

        self.terminateCurrentImage = 0
        self.smu.subtext("Measure completed")

    def displayDiode(self):
        QApplication.processEvents()
        (user, experiment, device, diode, cellArea,
            irradiance) = self.getDeviceIdentification()

        self.smu.reset()
        self.smu.removetext()
        self.smu.removesubtext()

        text = "Select diode " + diode
        print text
        self.smu.text(text)
        subtext = "Device " + device
        self.smu.subtext(subtext)
        sleep(0.7)
        d = 0
        while(d < int(diode)):
            self.smu.beep2()
            sleep(0.35)
            d += 1
        sleep(0.5)
        self.smu.beep()
        sleep(0.2)
        self.smu.beep()
        sleep(1)

    @pyqtSlot()
    def clickSaveAs(self):
        self.calcEfficiencyAndSetLCDs()
        (user, experiment, device, diode, cellArea,
            irradiance) = self.getDeviceIdentification()

        suggestedFileName = self.makeAutoName(
                experiment, device, diode, irradiance) + ".txt"

        fileName = QFileDialog.getSaveFileName(
                self, 'Save VI Curve', suggestedFileName, 'Text files (*.txt)')
        if fileName:
            fileNameTxt = str(fileName)
            self.save(
                    fileNameTxt, user, experiment, device, diode, cellArea,
                    irradiance)
            self.setSaved(1)

            self.unsavedData = False
            self.pastFileName = fileNameTxt
            print fileNameTxt
            self.fillTable(device, diode)
            self.fillLogFile(user, experiment, device, diode)

        logContent = (
                "SaveAs by " + str(user) + " experiment " +
                str(experiment) + " in file " + str(fileName), "")
        with open("measurements_log.txt", 'a') as f_handle:
            savetxt(f_handle, logContent, fmt='%s')

    @pyqtSlot()
    def clickAutoSave(self):
        # https://hynek.me/articles/hasattr/#fnref:sentinel
        test = getattr(self, "data3", None)
        if test is None:
            QMessageBox.warning(
                    self, "No data", "There is still no data to save.",
                    QMessageBox.Ok, QMessageBox.Ok)
        else:
            self.calcEfficiencyAndSetLCDs()
            (user, experiment, device, diode, cellArea,
                irradiance) = self.getDeviceIdentification()
            directory = os.path.join(user, str(self.date))
            if not os.path.exists(directory):
                os.makedirs(directory)

            fileName = (
                    self.makeAutoName(experiment, device, diode, irradiance) +
                    ".txt")

            fileNameWithDirectory = os.path.join(directory, fileName)
            self.saveProblem = True
            if not self.unsavedData:
                saveAgainAnswer = QMessageBox.question(
                        self, "Data Already Saved",
                        "This data was already saved in file " +
                        self.pastFileName +
                        ". Maybe you should go and check if is better to "
                        "delete that file, anyway do you want to save this "
                        "data again in file " +
                        fileNameWithDirectory +
                        "?", QMessageBox.Yes | QMessageBox.Cancel,
                        QMessageBox.Yes)
                if saveAgainAnswer == QMessageBox.Yes:
                    self.saveProblem = False

            if os.path.exists(fileNameWithDirectory):
                self.saveProblem = True
                overwriteAnswer = QMessageBox.question(
                        self, "File Already Existing",
                        "There is already a file with name " + fileName +
                        ". Do you really want to overwrite this file?",
                        QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Yes)
                if overwriteAnswer == QMessageBox.Yes:
                    self.saveProblem = False
            else:
                self.saveProblem = False

            if not self.saveProblem:
                self.save(
                        str(fileNameWithDirectory), user, experiment, device,
                        diode, cellArea, irradiance)
                self.setSaved(1)

                autoSaveText = (
                        "Measurement saved in " + str(fileNameWithDirectory))
                print(autoSaveText)
                self.unsavedData = False
                self.pastFileName = fileNameWithDirectory
                logContent = (
                        "AutoSave by " + user + " experiment " +
                        experiment + " in file " + str(fileNameWithDirectory) +
                        " including results:", "")
                with open("measurements_log.txt", 'a') as f_handle:
                    savetxt(f_handle, logContent, fmt='%s')
                self.fillTable(device, diode)
                self.fillLogFile(user, experiment, device, diode)
                self.fillMeasurementsFile(directory, experiment, device, diode)
                if self.ui.autoSaveImages_check.isChecked():
                    saveImage = 1
                    self.makeImage(saveImage, directory)

    @pyqtSlot()
    def clickAutoScale(self):
        if self.ui.autoScale_check.isChecked():
            self.ui.scale_combo.setEnabled(False)
        else:
            self.ui.scale_combo.setEnabled(True)

    def checkFileName(self, fileName):
        # https://stackoverflow.com/questions/9532499/check-whether-a-path-is-valid-in-python-without-creating-a-file-at-the-paths-ta
        if not os.access(fileName, os.W_OK):
            fileNameOk = False
            try:
                open(fileName, 'w').close()
                os.unlink(fileName)
                fileNameOk = True
            except IOError:
                QMessageBox.warning(
                        self, "Error while saving file",
                        "Can't save the required file:\n" + fileName +
                        "\nEliminate the special characters in the User, "
                        "Experiment and Device fields.",
                        QMessageBox.Ok, QMessageBox.Ok)
        else:
            fileNameOk = True
        return fileNameOk

    def save(
            self, fileName, user, experiment, device, diode, cellArea,
            irradiance):
        # this handles also saving of last_measurement.txt
        if self.checkFileName(fileName):
            with open(fileName, 'w') as f_handle:
                savetxt(f_handle, self.makeHeader(
                        user, experiment, device, diode, cellArea,
                        irradiance), fmt='%s')
            with open(fileName, 'a') as f_handle:
                savetxt(f_handle, self.data3, fmt='%g \t%g')

    def makeImage(self, saveImage, directory):
        (user, experiment, device, diode, cellArea,
            irradiance) = self.getDeviceIdentification()
        imageName = self.makeAutoName(experiment, device, diode, irradiance)
        if self.currentImagePid:
            if self.terminateCurrentImage:
                if not saveImage:
                    self.currentImage.terminate()

        p = Process(target=plot_graph, args=(
                imageName, self.voltage,
                - self.current * self.currentUnitMultiplier,
                self.voltageMaxPower,
                self.currentMaxPower * self.currentUnitMultiplier, self.voc,
                self.printVoc, self.jsc * self.currentUnitMultiplier,
                self.jscDensity, self.ff, self.efficiency, saveImage,
                directory))
        p.start()
        if not saveImage:
            self.currentImage = p
            self.currentImagePid = int(p.pid)

    def makeAutoName(self, experiment, device, diode, irradiance):
        if float(irradiance) == 0:
            fileName = (
                    experiment + "-" + device + "-" + diode + "-dark-" +
                    self.reverseText)
        else:
            if float(irradiance) == 100:
                fileName = (
                        experiment + "-" + device + "-" + diode + "-" +
                        self.reverseText)
            else:
                fileName = (
                        experiment + "-" + device + "-" + diode + "-" +
                        str(float(irradiance)/100) + "sun-" +
                        self.reverseText)
        return fileName

    def getDeviceIdentification(self):
        try:
            user = unicodedata.normalize(
                    'NFD', unicode(self.ui.user_edit.text())).encode(
                    'ascii', 'ignore')
            experiment = unicodedata.normalize(
                    'NFD', unicode(self.ui.experiment_edit.text())).encode(
                    'ascii', 'ignore')
            device = unicodedata.normalize(
                    'NFD', unicode(self.ui.device_edit.text())).encode(
                    'ascii', 'ignore')
            diode = str(int(self.ui.diode_spin.value()))
            cellArea = str(self.ui.cellArea_edit.text())
            irradiance = str(self.ui.irradiance_edit.text())
        except:
            QMessageBox.warning(
                    self, "Error reading parameters",
                    "Please check the user, experiment, device, diode, "
                    "cellArea and irradiance data fields", QMessageBox.Ok,
                    QMessageBox.Ok)
        return user, experiment, device, diode, cellArea, irradiance

    def getDarkData(self, irradiance, cellArea, compliance):
        parallelResistance = VICurves.calcParallelResistance(
                self.voltage, self.current * (CURRENT_POSITIVE * 2 - 1))

        seriesResistance = VICurves.calcSeriesResistance(
                self.voltage, self.current * (CURRENT_POSITIVE * 2 - 1),
                compliance, self.reverse)

        darkOutput = (
                "Serie Resistance (Ohm):	" + str(seriesResistance) +
                "	Parallel Resistance (Ohm):	" +
                str(parallelResistance))
        return darkOutput

    def setSaved(self, saved):
        if saved:
            self.ui.saved.setText("Saved")
            self.ui.saved.setStyleSheet('color: green')
        else:
            self.ui.saved.setText("Not saved")
            self.ui.saved.setStyleSheet('color: red')

    def calcEfficiencyAndSetLCDs(self):
        self.irradiance = float(self.ui.irradiance_edit.text())
        (user, experiment, device, diode, cellArea,
            irradiance) = self.getDeviceIdentification()
        if self.irradiance:
            self.efficiency = "%.3f" % float("%.4g" % (100 * (
                    (float(self.maxPower) / float(cellArea)) /
                    (float(self.irradiance) * IRRADIANCE_UNIT_MULTIPLIER))))
        else:
            self.efficiency = "0"

        self.ui.LCD_Jsc.display(self.jscDensity[0:5])
        self.ui.LCD_Voc.display(self.voc[0:5])
        self.ui.LCD_FF.display(self.ff[0:4])
        self.ui.LCD_PCE.display(self.efficiency[0:5])

    @pyqtSlot()
    def calcScanSpeed(self):
        if TEST_MODE:
            self.scanSpeed = 0
        else:
            stepV = float(self.ui.stepV_edit.text())
            integrationTime = float(self.ui.integrationTime_edit.text())
            delayTime = float(self.ui.delayTime_edit.text())
            self.scanSpeed = "%.3g" % (
                    self.smu.scanSpeed(stepV, integrationTime, delayTime))
            scanSpeedText = str(self.scanSpeed) + " V/s"
            self.ui.scanSpeed_label.setText(scanSpeedText)

    def fillTable(self, device, diode):
        self.ui.data_table.insertRow(0)
        self.ui.data_table.setItem(0, 0, QTableWidgetItem(str(device)))
        self.ui.data_table.setItem(0, 1, QTableWidgetItem(str(diode)))
        self.ui.data_table.setItem(0, 2, QTableWidgetItem(self.reverseText))
        self.ui.data_table.setItem(
                0, 3, QTableWidgetItem(str(self.jscDensity[0:5])))
        self.ui.data_table.setItem(0, 4, QTableWidgetItem(str(self.voc[0:5])))
        self.ui.data_table.setItem(0, 5, QTableWidgetItem(str(self.ff[0:4])))
        self.ui.data_table.setItem(
                0, 6, QTableWidgetItem(str(self.efficiency[0:5])))
        self.ui.data_table.setItem(
                0, 7, QTableWidgetItem(str(self.integrationTime)))
        self.ui.data_table.setItem(0, 8, QTableWidgetItem(str(self.delayTime)))
        self.ui.data_table.setItem(
                0, 9, QTableWidgetItem(str(self.irradiance)))
        self.ui.data_table.resizeColumnsToContents()

    def fillMeasurementsFile(self, directory, experiment, device, diode):
        measurementsFileName = (
                "iv_measurements-" + str(experiment) + "-" +
                str(self.date) + ".txt")
        measurementsFileNameWithDirectory = os.path.join(
                directory, measurementsFileName)
        if self.checkFileName(measurementsFileNameWithDirectory):
            if not os.path.exists(measurementsFileNameWithDirectory):
                measurementsFileHeader = (
                        "exp	device	diode	rev/fwd	Jsc	Voc	FF	"
                        "efficiency	intTime	delay	irradiance", "")
                with open(measurementsFileNameWithDirectory, 'w') as f_handle:
                    savetxt(f_handle, measurementsFileHeader, fmt='%s')
            if os.path.isfile(measurementsFileNameWithDirectory):
                measurementsFileContent = (
                        str(experiment) + "	" +
                        str(device) +
                        "	" + str(diode) + "	" + str(self.reverseText) +
                        "	" + str(self.jscDensity) + "	" + str(self.voc) +
                        "	" + str(self.ff) + "	" + str(self.efficiency) +
                        "	" + str(self.integrationTime) + "	" +
                        str(self.delayTime) + "	" + str(self.irradiance), "")
                with open(measurementsFileNameWithDirectory, 'a') as f_handle:
                    savetxt(f_handle, measurementsFileContent, fmt='%s')

    def fillLogFile(self, user, experiment, device, diode):
        logContent = (
                str(user) + "	" + str(experiment) + "	" + str(device) +
                "	" + str(diode) + "	" + str(self.reverseText) + "	" +
                str(self.jscDensity) + "	" + str(self.voc) + "	" +
                str(self.ff) + "	" + str(self.efficiency) + "	" +
                str(self.integrationTime) + "	" + str(self.delayTime) + "	" +
                str(self.irradiance), "")
        with open("measurements_log.txt", 'a') as f_handle:
            savetxt(f_handle, logContent, fmt='%s')

    def makeHeader(
            self, user, experiment, device, diode, cellArea,
            irradiance):
        darkOutput = self.getDarkData(
                irradiance, cellArea, float(self.compliance))
        return (
                "PyPV software (Gr. E. Palomares, ICIQ) - Voltage-Current "
                "measurement Report", "User:	" +
                user, "Date:	" + str(self.date) + "    Time: " +
                str(datetime.datetime.now().strftime("%H:%M:%S")),
                "Experiment:	" + experiment, "Device:	" + device,
                "Diode:	" + diode, "Forward or reverse? " + self.reverseText,
                "Lowest Voltage (V):	" + str(self.minVoltage),
                "Highest Voltage (V): " + str(self.maxVoltage),
                "Voltage Step (V):	" + str(self.stepV), "Compliance (A):	" +
                str(self.compliance), "Scale (A):	" + str(self.scale),
                "Voltage of maximum power point (V):	" +
                str(self.voltageMaxPower) +
                "	Current density of MPP (mA/cm2):	" +
                str(self.currentMaxPowerDensity), "Integration Time:	" +
                str(self.integrationTime) + "	Scan Speed (V/s):	" +
                str(self.scanSpeed), "Delay Time (s):	" +
                str(self.delayTime) + "	ShutterDelayOff (s):	" +
                str(self.preDelayOff) + "	ShutterDelayOn (s):	" +
                str(self.preDelayOn), darkOutput, "Cell Area (cm2):	" +
                cellArea, "Irradiance (mW/cm2):	" + irradiance,
                "Jsc (mA/cm2):	" + str(self.jscDensity), "Voc (V):	" +
                str(self.voc), "Fill factor:	" + str(self.ff),
                "Efficiency (%):	" + str(self.efficiency),
                "Voltage_V \tCurrent_mA")
