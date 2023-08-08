from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import finplot as fplt

import sys
import zmq
import zmq.asyncio
import json
import time
import datetime
import pandas as pd
from typing import Dict, Any

fplt.display_timezone = datetime.timezone.utc


class Publisher:
    
    def __init__(self, port: int):
        self.port = port
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind(f'tcp://*:{port}')

    async def send(self, data: Dict[str, Any]):
        await self.socket.send_string(json.dumps(data))
        
        
class Subscriber:
    
    def __init__(self, port: int):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(f'tcp://localhost:{port}')
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        
    def recv(self):
        return json.loads(self.socket.recv_string())


class Worker(QThread):
    timeout = pyqtSignal(pd.DataFrame)

    def __init__(self, port: int):
        super().__init__()
        
        self.data = []
        self.subscriber = Subscriber(port)

    def run(self):
        i = 0
        
        while True:
            data = self.subscriber.recv()
            self.data.append([i, data['spread']])
            i += 1

            df = pd.DataFrame(self.data, columns=['Date', 'Spread'])
            self.timeout.emit(df)
            time.sleep(0.1)


class ChartWindow(QMainWindow):
    
    def __init__(self, port: int):
        super().__init__()

        self.df = None
        self.plot = None

        # thread
        self.w = Worker(port)
        self.w.timeout.connect(self.update_data)
        self.w.start()

        # timer: update chart every 0.5 second
        self.timer = QTimer(self)
        self.timer.start(500)
        self.timer.timeout.connect(self.update)

        view = QGraphicsView()
        grid_layout = QGridLayout(view)
        self.setCentralWidget(view)
        self.resize(1200, 600)

        self.ax = fplt.create_plot(init_zoom_periods=100)
        self.axs = [self.ax]
        grid_layout.addWidget(self.ax.vb.win, 0, 0)

    def update(self):
        now = datetime.datetime.now()
        self.statusBar().showMessage(str(now))

        if self.df is not None:
            if self.plot is None:
                self.plot = fplt.plot(self.df[['Date', 'Spread']])
                fplt.show(qt_exec=False)
            else:
                self.plot.update_data(self.df[['Date', 'Spread']])

    @pyqtSlot(pd.DataFrame)
    def update_data(self, df):
        self.df = df
        
        
# Sample publisher function for test
def send_data(port: int):
    import asyncio
    
    async def _send():
        pub = Publisher(port)
        i = 0
        while True:
            await pub.send({'spread': i})
            i += 1
            time.sleep(0.5)
            
    asyncio.run(_send())


if __name__ == "__main__":
    from multiprocessing import Process
    
    port = 9999
    
    # p = Process(target=send_data, args=(port,))
    # p.start()
    
    app = QApplication(sys.argv)
    window = ChartWindow(port)
    window.show()
    app.exec()