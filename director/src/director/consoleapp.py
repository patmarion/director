import os
import sys
import traceback
import argparse

from director import applogic
from director import argutils
from director import objectmodel as om
from director import viewbehaviors
from director import visualization as vis
from director.timercallback import TimerCallback

import qtpy.QtCore as QtCore
import qtpy.QtWidgets as QtWidgets
import qtpy.QtGui as QtGui


def _consoleAppExceptionHook(exc_type, exc_value, exc_traceback):
    msg =  ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    sys.stderr.write(msg)
    ConsoleApp.exit(1)


class ConsoleApp(object):

    _startupCallbacks = {}
    _exitCode = 0
    _quitTimer = None
    _testingArgs = None

    def __init__(self):
        om.init()
        self.objectModelWidget = None
        self.pythonConsoleWidget = None
        self.pythonConsoleWindow = None

    @staticmethod
    def start(enableAutomaticQuit=True):
        '''
        In testing mode, the application will quit automatically after starting
        unless enableAutomaticQuit is set to False.  Tests that need to perform
        work after the QApplication has started can set this flag to False and
        call quit or exit themselves.

        In testing mode, this function will register an exception hook so that
        tests will return on error code if an unhandled exception is raised.
        '''
        if enableAutomaticQuit:
            ConsoleApp.startTestingModeQuitTimer()

        if ConsoleApp.getTestingEnabled() and not ConsoleApp.getTestingInteractiveEnabled():
            sys.excepthook = _consoleAppExceptionHook

        def onStartup():
            callbacks = []
            for priority in sorted(ConsoleApp._startupCallbacks.keys()):
                callbacks.extend(ConsoleApp._startupCallbacks[priority])
            for func in callbacks:
                try:
                    func()
                except:
                    if ConsoleApp.getTestingEnabled():
                        raise
                    else:
                        print(traceback.format_exc())

        startTimer = TimerCallback(callback=onStartup)
        startTimer.singleShot(0)

        result = ConsoleApp.applicationInstance().exec_()

        if ConsoleApp.getTestingEnabled() and not ConsoleApp.getTestingInteractiveEnabled():
            print('TESTING PROGRAM RETURNING EXIT CODE:', result)
            sys.exit(result)

        return result


    @staticmethod
    def startTestingModeQuitTimer(timeoutInSeconds=0.1):
        if ConsoleApp.getTestingEnabled() and not ConsoleApp.getTestingInteractiveEnabled():
            ConsoleApp.startQuitTimer(timeoutInSeconds)

    @staticmethod
    def startQuitTimer(timeoutInSeconds):
        quitTimer = TimerCallback()
        quitTimer.callback = ConsoleApp.quit
        quitTimer.singleShot(timeoutInSeconds)
        ConsoleApp._quitTimer = quitTimer

    @staticmethod
    def getQuitTimer():
        return ConsoleApp._quitTimer

    @staticmethod
    def quit():
        ConsoleApp.exit(ConsoleApp._exitCode)

    @staticmethod
    def exit(exitCode=0):
        ConsoleApp._exitCode = exitCode
        ConsoleApp.applicationInstance().exit(exitCode)

    @staticmethod
    def applicationInstance():
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        return app

    @staticmethod
    def processEvents():
        ConsoleApp.applicationInstance().processEvents()

    @staticmethod
    def registerStartupCallback(func, priority=1):
        ConsoleApp._startupCallbacks.setdefault(priority, []).append(func)

    def showObjectModel(self):

        if not self.objectModelWidget:
            w = QtWidgets.QSplitter(QtCore.Qt.Vertical)
            model = om.getDefaultObjectModel()
            w.addWidget(model.getTreeWidget())
            sw = QtWidgets.QScrollArea()
            sw.setWidget(model.getPropertiesPanel())
            sw.setWidgetResizable(True)
            w.addWidget(sw)
            applogic.addShortcut(w, 'Ctrl+Q', self.quit)
            self.objectModelWidget = w
            self.objectModelWidget.resize(350, 700)
            w.setSizes([350, 350])

        self.objectModelWidget.show()
        self.objectModelWidget.raise_()
        self.objectModelWidget.activateWindow()
        return self.objectModelWidget

    def createView(self, useGrid=True):
        # Note: This creates a VTKWidget view - simplified from original PythonQt version
        from director.vtk_widget import VTKWidget
        
        view = VTKWidget()
        self.view = view  # Store reference for Python console namespace
        applogic.setCurrentRenderView(view)
        view.resize(600, 400)

        if useGrid:
            view.initializeGrid()
            self.gridObj = om.findObjectByName('grid')

        # ViewOptionsItem is not yet implemented - skip for now
        self.viewOptions = vis.ViewOptionsItem(view)
        om.addToObjectModel(self.viewOptions, parentObj=om.findObjectByName('scene'))

        applogic.resetCamera(viewDirection=[-1,-1,-0.3], view=view)
        self.viewBehaviors = viewbehaviors.ViewBehaviors(view)

        applogic.addShortcut(view, 'Ctrl+Q', self.quit)
        applogic.addShortcut(view, 'F8', self.showPythonConsole)
        applogic.addShortcut(view, 'F1', self.showObjectModel)

        view.setWindowIcon(om.Icons.getIcon(om.Icons.Robot))
        view.setWindowTitle('View')

        return view

    def showPythonConsole(self):
        """Show Python console in a standalone window."""
        from director.python_console import PythonConsoleWidget, QTCONSOLE_AVAILABLE
        
        if not QTCONSOLE_AVAILABLE:
            print("Python console not available. Please install qtconsole.")
            return
        
        # Create console widget if it doesn't exist
        if self.pythonConsoleWidget is None:
            # Set up minimal initial namespace
            namespace = {
                'om': om,
                'vis': vis,
            }
            
            # Add gridObj if it exists
            if hasattr(self, 'gridObj') and self.gridObj:
                namespace['gridObj'] = self.gridObj
            
            try:
                self.pythonConsoleWidget = PythonConsoleWidget(namespace=namespace)
            except RuntimeError as e:
                print(str(e))
                return
        
        # Create window if it doesn't exist
        if self.pythonConsoleWindow is None:
            window = QtWidgets.QMainWindow()
            window.setWindowTitle('Python Console')
            window.setCentralWidget(self.pythonConsoleWidget.get_widget())
            window.resize(800, 400)
            self.pythonConsoleWindow = window
        
        # Show the window
        self.pythonConsoleWindow.show()
        self.pythonConsoleWindow.raise_()
        self.pythonConsoleWindow.activateWindow()
        return self.pythonConsoleWindow

    @staticmethod
    def getTestingArgs(dataDirRequired=False, outputDirRequired=False):

      parser = argparse.ArgumentParser()
      argutils.add_standard_args(parser)
      
      # Note: --data-dir and --output-dir are already added by add_standard_args
      # Just update the required status if needed
      # We need to get the existing actions and update them
      for action in parser._actions:
          if '--data-dir' in action.option_strings:
              action.required = dataDirRequired
          if '--output-dir' in action.option_strings:
              action.required = outputDirRequired

      args = parser.parse_known_args()[0]
      
      # Cache the result
      ConsoleApp._testingArgs = args
      return args

    @staticmethod
    def getTestingDataDirectory():
        path = ConsoleApp.getTestingArgs(dataDirRequired=True).data_dir
        if not os.path.isdir(path):
            raise Exception('Testing data directory does not exist: %s' % path)
        return path

    @staticmethod
    def getTestingOutputDirectory(outputDirRequired=True):
        args = ConsoleApp.getTestingArgs()
        path = args.output_dir
        if outputDirRequired and not path:
            raise Exception('Testing output directory is required but not provided')
        if path and not os.path.isdir(path):
            raise Exception('Testing output directory does not exist: %s' % path)
        return path

    @staticmethod
    def getTestingInteractiveEnabled():
        return ConsoleApp.getTestingArgs().interactive

    @staticmethod
    def getTestingEnabled():
        return ConsoleApp.getTestingArgs().testing



def main():

    # Ensure QApplication exists
    ConsoleApp.applicationInstance()
    
    app = ConsoleApp()
    app.showPythonConsole()
    view = app.createView()
    view.show()
    view.raise_()
    view.activateWindow()

    # Push variables to Python console namespace
    if app.pythonConsoleWidget is not None:
        app.pythonConsoleWidget.push_variables({
            'app': app,
            'view': view,
            'quit': ConsoleApp.quit,
            'exit': ConsoleApp.exit,
        })

    app.start()


if __name__ == '__main__':
    main()

