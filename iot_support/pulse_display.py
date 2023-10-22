#!/usr/bin/env python3

import argparse
from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
import numpy as np
import math
import zmq


## Support program for the iotpcf8591pulses and powermeter devices for debugging. Receive the ZMQ debug output of such a device
## (currently with up to 2 channels) and display them in real time. In addition display the delta t from the
## included time stamps


class TimeLine(QtCore.QObject):
    frameChanged = QtCore.pyqtSignal(int)

    def __init__(self, interval=60, loopCount=1, parent=None):
        super(TimeLine, self).__init__(parent)
        self._startFrame = 0
        self._endFrame = 0
        self._loopCount = loopCount
        self._timer = QtCore.QTimer(self, timeout=self.on_timeout)
        self._counter = 0
        self._loop_counter = 0
        self.setInterval(interval)

    def on_timeout(self):
        if self._startFrame <= self._counter < self._endFrame:
            self.frameChanged.emit(self._counter)
            self._counter += 1
        else:
            self._counter = 0
            self._loop_counter += 1

        if self._loopCount > 0:
            if self._loop_counter >= self.loopCount():
                self._timer.stop()

    def setLoopCount(self, loopCount):
        self._loopCount = loopCount

    def loopCount(self):
        return self._loopCount

    interval = QtCore.pyqtProperty(int, fget=loopCount, fset=setLoopCount)

    def setInterval(self, interval):
        self._timer.setInterval(interval)

    def interval(self):
        return self._timer.interval()

    interval = QtCore.pyqtProperty(int, fget=interval, fset=setInterval)

    def setFrameRange(self, startFrame, endFrame):
        self._startFrame = startFrame
        self._endFrame = endFrame

    @QtCore.pyqtSlot()
    def start(self):
        self._counter = 0
        self._loop_counter = 0
        self._timer.start()


class Gui(QtWidgets.QWidget):
    def __init__(self,host,port):
        super().__init__()
        self.setupData()
        self.setupZMQ(host,port)
        self.setupUI()

    def setupData(self):
        self.SIZE= 500
        self.t= 0.0
        self.told= 0.0
        self.y= np.zeros((5,self.SIZE))

    def setupZMQ(self,host,port):

        self.counter= 0 ## counting the packages received
        self.printsome= 0

        self.context = zmq.Context()
        self.recvsocket = self.context.socket(zmq.SUB)
        self.recvsocket.connect('tcp://%s:%s' % (host,port) )
        self.recvsocket.setsockopt_string( zmq.SUBSCRIBE, '' )
        self.recvsocket.setsockopt( zmq.LINGER, 0 )
        self.recvsocket.setsockopt( zmq.SNDHWM, 1 )
        self.recvsocket.setsockopt( zmq.RCVHWM, 1 )

        self.poller = zmq.Poller()
        self.poller.register( self.recvsocket, zmq.POLLIN )

    def setupUI(self):
        pg.setConfigOption('background', 0.95)
        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget()
        #self.plot.setAspectLocked(lock=True, ratio=0.01)
        self.plot.setYRange(0,260)
        widget_layout = QtWidgets.QVBoxLayout(self)
        widget_layout.addWidget(self.plot)

        self._plots = [self.plot.plot([], [], pen=pg.mkPen(color=color, width=2)) for
                       color in ("g", "r", "darkgreen", "orange", "b")]
        self._timeline = TimeLine(loopCount=0, interval=100)
        self._timeline.setFrameRange(0, self.SIZE*5)
        self._timeline.frameChanged.connect(self.receive_data)
        self._timeline.start()

    def plot_data(self, data):
        for plt, val in zip(self._plots, data):
            plt.setData(range(len(val)), val)

    # receiving data from ZMQ
    @QtCore.pyqtSlot(int)
    def receive_data(self, i):

        #old= self.counter

        # receive all pending packets

        socks = dict(self.poller.poll(1))
        while self.recvsocket in socks:

            i= self.counter % self.SIZE

            packet = self.recvsocket.recv_json()
            #print( i, "received: ", packet )
            self.t= packet["time"]


            j= 0
            for c in packet["adc"]:
                if packet["adc"][c] < 200:
                    self.printsome= 10
                    print("")
                self.y[ j, i ]= packet["adc"][c]
                j+=1

            for c in packet["sig"]:
                self.y[ j, i ]= packet["sig"][c]
                j+=1

            #print(1000.0*(self.t-self.told))
            # one addl. value is time difference in ms between samples
            self.y[j,i]= min( 255.0, 1000.0*(self.t-self.told) )
            self.told= self.t

            if self.printsome > 0:
                print( i, packet )
                self.printsome -= 1


            self.counter += 1
            socks = dict(self.poller.poll(1))

        # do one plot operation

        self.plot_data( [ self.y[0], self.y[1], self.y[2], self.y[3], self.y[4] ] )

        #new=self.counter
        #print(new-old)

    # new version with an overwriting diagram mod pos
    @QtCore.pyqtSlot(int)
    def update_data(self, i):

        for ii in range(4*i,4*i+4):
            for j in range(3):
                self.y[j,ii%self.SIZE]= (j+1) * math.sin(j+(j+1)*i*0.02)
        self.plot_data( [ self.y[0], self.y[1], self.y[2] ] )

    # original version of a moving diagram
    @QtCore.pyqtSlot(int)
    def generate_data(self, i):
        ang = np.arange(i, i + 720)
        cos_func = np.cos(np.radians(ang))
        sin_func = np.sin(np.radians(ang))
        tan_func = sin_func/cos_func
        tan_func[(tan_func < -3) | (tan_func > 3)] = np.NaN
        self.plot_data([sin_func, cos_func, tan_func])

    def finalizeZMQ(self):
        self.recvsocket.close()
        self.context.term()
        #print("finalized ZMQ")

    def finalize(self):
        self.finalizeZMQ()

if __name__ == '__main__':

    ap= argparse.ArgumentParser()
    ap.add_argument("-c", "--connect", required=False, default="localhost", help="IP or hostname to connect to, default is 'localhost'")
    ap.add_argument("-p", "--port", required=False, default="5557", help="port to connect to, default is 5557")
    #ap.add_argument('-v', '--verbose', action='store_true', help="Print the values" )
    args= vars(ap.parse_args())

    print("connect to", args["connect"], args["port"])

    import sys
    app = QtWidgets.QApplication(sys.argv)
    gui = Gui(args["connect"], args["port"])
    gui.show()
    #print("A")
    #sys.exit(app.exec_())
    app.exec_()
    #print("B")
    gui.finalize()
