import pyqtgraph as pg


win = pg.GraphicsLayoutWidget(show=True)
win.setWindowTitle("pyqtgraph example")
label = pg.LabelItem(justify="right")
win.addItem(label)

p1 = win.addPlot(row=1, col=0)
# customize the averaged curve that can be activated from the context menu:
p1.avgPen = pg.mkPen("#FFFFFF")
p1.avgShadowPen = pg.mkPen("#8080DD", width=10)

p2 = win.addPlot(row=2, col=0)


w = fields.mainWindow.centralWidget()

splitter = QtWidgets.QSplitter()

splitter.addWidget(win)
splitter.addWidget(fields.view)

fields.mainWindow.setCentralWidget(splitter)

win.show()


# create numpy arrays
# make the numbers large to show that the range shows data from 10000 to all the way 0
data1 = 10000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)
data2 = 15000 + 15000 * pg.gaussianFilter(np.random.random(size=10000), 10) + 3000 * np.random.random(size=10000)

p1.plot(data1, pen="r")
p1.plot(data2, pen="g")
p2.plot(data2, pen="b")
