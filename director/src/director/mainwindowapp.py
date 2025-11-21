"""MainWindowApp for Director 2.0 - component-based application factory."""

import os
import sys
import signal
import argparse
import runpy

from director.componentgraph import ComponentFactory
from director import consoleapp
from director.frame_properties import FrameProperties
import director.objectmodel as om
import director.visualization as vis
from director.icons import Icons
from director.fieldcontainer import FieldContainer
from director import applogic
from director import appsettings
from director import argutils
from director import script_context
from director.timercallback import TimerCallback

import qtpy.QtCore as QtCore
import qtpy.QtWidgets as QtWidgets
import qtpy.QtGui as QtGui

from director.viewmenumanager import ViewMenuManager


class MainWindowApp(object):

    def __init__(self):

        self.mainWindow = QtWidgets.QMainWindow()
        self.mainWindow.resize(int(768 * (16/9.0)), 768)
        self.settings = QtCore.QSettings()

        self.fileMenu = self.mainWindow.menuBar().addMenu('&File')
        self.editMenu = self.mainWindow.menuBar().addMenu('&Edit')
        self.viewMenu = self.mainWindow.menuBar().addMenu('&View')
        self.toolbarMenu = self.viewMenu.addMenu('&Toolbars')
        self.toolsMenu = self.mainWindow.menuBar().addMenu('&Tools')
        self.helpMenu = self.mainWindow.menuBar().addMenu('&Help')
        
        # Use ViewMenuManager instead of PythonQt.dd.ddViewMenu
        self.viewMenuManager = ViewMenuManager(self.viewMenu)
        self.toolbarMenuManager = ViewMenuManager(self.toolbarMenu)
        
        # Python console dock widget (initialized by component factory)
        self.python_console_dock = None
        self.python_console = None

        self.quitAction = self.fileMenu.addAction('&Quit')
        self.quitAction.setShortcut(QtGui.QKeySequence('Ctrl+Q'))
        self.quitAction.triggered.connect(self.quit)
        self.fileMenu.addSeparator()

        self.pythonConsoleAction = self.toolsMenu.addAction('&Python Console')
        self.pythonConsoleAction.setShortcut(QtGui.QKeySequence('F8'))
        self.pythonConsoleAction.triggered.connect(self.showPythonConsole)
        self.toolsMenu.addSeparator()

        helpAction = self.helpMenu.addAction('Online Documentation')
        helpAction.triggered.connect(self.showOnlineDocumentation)
        self.helpMenu.addSeparator()

        helpKeyboardShortcutsAction = self.helpMenu.addAction('Keyboard Shortcuts')
        helpKeyboardShortcutsAction.triggered.connect(self.showOnlineKeyboardShortcuts)
        self.helpMenu.addSeparator()

    def quit(self):
        MainWindowApp.applicationInstance().quit()

    def exit(self, exitCode=0):
        MainWindowApp.applicationInstance().exit(exitCode)

    def start(self, restoreWindow=True):
        if not consoleapp.ConsoleApp.getTestingEnabled() and restoreWindow:
            self.initWindowSettings()
        self.mainWindow.show()
        self.mainWindow.raise_()
        return consoleapp.ConsoleApp.start()

    @staticmethod
    def applicationInstance():
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        return app

    def showPythonConsole(self):
        """Show Python console as a dock widget."""
        if self.python_console is None:
            self.showErrorMessage("Python console not available. Please install qtconsole.")
            return
        
        if self.python_console_dock is None:
            # This shouldn't happen if component factory initialized it properly
            self.showErrorMessage("Python console dock widget not initialized.")
            return
        
        # Toggle visibility
        if self.python_console_dock.isVisible():
            self.python_console_dock.hide()
        else:
            self.python_console_dock.show()
            self.python_console.console_widget.layout().currentWidget().setFocus()
            self.python_console_dock.raise_()

    def showOnlineDocumentation(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl('https://openhumanoids.github.io/director/'))

    def showOnlineKeyboardShortcuts(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl('https://openhumanoids.github.io/director/user_guide/keyboard_shortcuts.html#director'))

    def showErrorMessage(self, message, title='Error'):
        QtWidgets.QMessageBox.warning(self.mainWindow, title, message)

    def showInfoMessage(self, message, title='Info'):
        QtWidgets.QMessageBox.information(self.mainWindow, title, message)

    def wrapScrollArea(self, widget):
        w = QtWidgets.QScrollArea()
        w.setWidget(widget)
        w.setWidgetResizable(True)
        if hasattr(widget, 'windowTitle'):
            w.setWindowTitle(widget.windowTitle())
        return w

    def addWidgetToViewMenu(self, widget):
        title = None
        if hasattr(widget, 'windowTitle'):
            title = widget.windowTitle()
        self.viewMenuManager.addWidget(widget, title)

    def addViewMenuSeparator(self):
        self.viewMenuManager.addSeparator()

    def addWidgetToDock(self, widget, dockArea, visible=True):
        dock = QtWidgets.QDockWidget()
        dock.setWidget(widget)
        if hasattr(widget, 'windowTitle'):
            dock.setWindowTitle(widget.windowTitle())
        elif hasattr(widget, 'objectName'):
            dock.setWindowTitle(widget.objectName())
        dock.setObjectName(dock.windowTitle() + ' Dock')
        self.mainWindow.addDockWidget(dockArea, dock)
        self.addWidgetToViewMenu(dock)
        dock.setVisible(visible)
        return dock


    def addToolBar(self, title, area=QtCore.Qt.TopToolBarArea):
        toolBar = QtWidgets.QToolBar(title)
        if hasattr(toolBar, 'setObjectName'):
            toolBar.setObjectName(title)
        self.mainWindow.addToolBar(area, toolBar)
        if hasattr(toolBar, 'windowTitle'):
            self.toolbarMenuManager.addWidget(toolBar, toolBar.windowTitle())
        else:
            self.toolbarMenuManager.addWidget(toolBar, title)
        return toolBar

    def addToolBarAction(self, toolBar, text, icon=None, callback=None):
        if isinstance(icon, str):
            icon = Icons.getIcon(icon)
        
        if icon:
            action = toolBar.addAction(icon, text)
        else:
            action = toolBar.addAction(text)

        if callback:
            action.triggered.connect(callback)

        return action

    def registerStartupCallback(self, func, priority=1):
        consoleapp.ConsoleApp.registerStartupCallback(func, priority)

    def _restoreWindowState(self, key):
        appsettings.restoreState(self.settings, self.mainWindow, key)

    def _saveWindowState(self, key):
        appsettings.saveState(self.settings, self.mainWindow, key)
        self.settings.sync()

    def _saveCustomWindowState(self):
        self._saveWindowState('MainWindowCustom')

    def restoreDefaultWindowState(self):
        self._restoreWindowState('MainWindowDefault')

    def initWindowSettings(self):
        self._saveWindowState('MainWindowDefault')
        self._restoreWindowState('MainWindowCustom')
        self.applicationInstance().aboutToQuit.connect(self._saveCustomWindowState)


class MainWindowAppFactory(object):

    def getComponents(self):

        components = {
            'View' : [],
            'Globals' : [],
            'GlobalModules' : ['Globals'],
            'ObjectModel' : [],
            'CommandLineArgs' : [],
            'ViewOptions' : ['View', 'ObjectModel'],
            'MainToolBar' : ['View', 'Grid', 'MainWindow'],
            'ViewBehaviors' : ['View'],
            'Grid': ['View', 'ObjectModel'],
            'PythonConsole' : ['Globals', 'GlobalModules'],
            'OpenMeshDataHandler' : ['MainWindow', 'CommandLineArgs'],
            'OutputConsole' : ['MainWindow'],
            'MainWindow' : ['View', 'ObjectModel', 'PythonConsole'],
            'SignalHandlers' : ['MainWindow'],
            'AdjustedClippingRange' : ['View'],
            'StartupRender' : ['View', 'MainWindow'],
            'RunScriptFunction' : ['Globals', 'PythonConsole', 'CommandLineArgs'],
            'ScriptLoader' : ['CommandLineArgs', 'RunScriptFunction'],
            'ProfilerTool' : ['MainWindow'],
            'ScreenRecorder' : ['MainWindow', 'View', 'MainToolBar'],
            'UndoRedo' : ['MainWindow'],
            'WaitCursor' : ['MainWindow'],
            'ApplicationSettings': ['Grid', 'ViewOptions', 'MainWindow'],
        }

        disabledComponents = []

        return components, disabledComponents

    def initApplicationSettings(self, fields):
        from director.settings_dialog import SettingsDialog

        dialog = SettingsDialog("Application Settings", parent=fields.mainWindow)
        dialog.add_settings("Grid", fields.grid.properties)
        dialog.add_settings("View", fields.viewOptions.properties)
        dialog.restore_all()
        dialog.resize(800, 600)

        settings_action = fields.app.editMenu.addAction("Edit application settings...")

        def show_dialog():
            dialog.show()
            dialog.raise_()

        settings_action.triggered.connect(show_dialog)

        return FieldContainer(settingsDialog=dialog, settingsAction=settings_action)

    def initView(self, fields):
        from director.vtk_widget import VTKWidget
        view = VTKWidget()
        applogic.setCurrentRenderView(view)
        applogic.resetCamera(viewDirection=[-1, -1, -0.3], view=view)
        return FieldContainer(view=view)

    def initObjectModel(self, fields):
        from director.propertiespanel import PropertiesPanel
        
        # Create tree widget and properties panel
        treeWidget = QtWidgets.QTreeWidget()
        propertiesPanel = PropertiesPanel()
        
        # Initialize object model with both widgets
        om.init(treeWidget, propertiesPanel)
        
        objectModel = om.getDefaultObjectModel()
        objectModel.getTreeWidget().setWindowTitle('Scene Browser')
        objectModel.getPropertiesPanel().setWindowTitle('Properties Panel')
        return FieldContainer(objectModel=objectModel)

    def initGrid(self, fields):
        grid = vis.showGrid(fields.view, parent='scene')
        grid.setProperty('Surface Mode', 'Wireframe')
        grid.setProperty('Color', [1,1,1])
        grid.setProperty('Alpha', 0.05)
        grid.setProperty('Show Text', False)
        grid.setProperty('Text Alpha', 0.4)
        vis.addChildFrame(grid)
        FrameProperties(grid.getChildFrame())
        fields.view._grid_obj = grid
        applogic.resetCamera(viewDirection=[-1, -1, -0.3], view=fields.view)
        return FieldContainer(grid=grid)

    def initViewBehaviors(self, fields):
        from director import viewbehaviors
        viewBehaviors = viewbehaviors.ViewBehaviors(fields.view)
        return FieldContainer(viewBehaviors=viewBehaviors)

    def initViewOptions(self, fields):
        viewOptions = vis.ViewOptionsItem(fields.view)
        fields.objectModel.addToObjectModel(viewOptions, parentObj=fields.objectModel.findObjectByName('scene'))
        return FieldContainer(viewOptions=viewOptions)

    def initCommandLineArgs(self, fields):
        # Get command line args from fields if provided, otherwise parse them
        if hasattr(fields, 'command_line_args'):
            commandLineArgs = fields.command_line_args
        else:
            parser = argparse.ArgumentParser()
            argutils.add_standard_args(parser)
            commandLineArgs = parser.parse_known_args()[0]
    
        return FieldContainer(command_line_args=commandLineArgs, commandLineArgs=commandLineArgs)


    def initSignalHandlers(self, fields):
        """Setup signal handlers for graceful shutdown on Ctrl+C."""
        
        app = fields.app
        
        def signal_handler(signum, frame):
            print("Caught interrupt signal, quitting application...")
            app.quit()

        signal.signal(signal.SIGINT, signal_handler)
    
        # The idle timer ensures that the Qt c++ event loop will periodically call into
        # python to allow the python interpretter a chance to run and process signals.
        idle_timer = TimerCallback(targetFps=30)
        idle_timer.start()

        return FieldContainer(idle_timer=idle_timer)
    
    def initAdjustedClippingRange(self, fields):
        '''This setting improves the near plane clipping resolution.
        Drake often draws a very large ground plane which is detrimental to
        the near clipping for up close objects.  The trade-off is Z buffer
        resolution but in practice things look good with this setting.'''
        fields.view.renderer().SetNearClippingPlaneTolerance(0.0005)
        return FieldContainer()

    def initMainWindow(self, fields):

        organizationName = 'Director'
        applicationName = 'Director'
        windowTitle = 'Director'
        windowIcon = None

        if hasattr(fields, 'organizationName'):
            organizationName = fields.organizationName
        if hasattr(fields, 'applicationName'):
            applicationName = fields.applicationName
        if hasattr(fields, 'windowTitle'):
            windowTitle = fields.windowTitle
        if hasattr(fields, 'windowIcon'):
            windowIcon = fields.windowIcon

        app_instance = MainWindowApp.applicationInstance()
        app_instance.setOrganizationName(organizationName)
        app_instance.setApplicationName(applicationName)

        app = MainWindowApp()

        app.mainWindow.setCentralWidget(fields.view)
        app.mainWindow.setWindowTitle(windowTitle)
        if windowIcon:
            app.mainWindow.setWindowIcon(QtGui.QIcon(windowIcon))

        # Create Python console dock if console widget is available
        if fields.pythonConsoleWidget:
            pythonConsoleDock = app.addWidgetToDock(fields.pythonConsoleWidget.get_widget(), QtCore.Qt.BottomDockWidgetArea, visible=False)
            app.python_console_dock = pythonConsoleDock
            app.python_console = fields.pythonConsoleWidget

        sceneBrowserDock = app.addWidgetToDock(fields.objectModel.getTreeWidget(),
                              QtCore.Qt.LeftDockWidgetArea, visible=True)
        propertiesDock = app.addWidgetToDock(fields.objectModel.getPropertiesPanel(),
                              QtCore.Qt.LeftDockWidgetArea, visible=True)

        # Allow the left dock widget to span down to the bottom of the window
        app.mainWindow.setCorner(QtCore.Qt.BottomLeftCorner, QtCore.Qt.LeftDockWidgetArea)

        app.addViewMenuSeparator()

        def toggleObjectModelDock():
            newState = not sceneBrowserDock.isVisible()
            sceneBrowserDock.setVisible(newState)
            propertiesDock.setVisible(newState)

        applogic.addShortcut(app.mainWindow, 'F1', toggleObjectModelDock)

        return FieldContainer(
          app=app,
          mainWindow=app.mainWindow,
          sceneBrowserDock=sceneBrowserDock,
          propertiesDock=propertiesDock,
          pythonConsole=app.python_console,
          pythonConsoleDock=app.python_console_dock,
          toggleObjectModelDock=toggleObjectModelDock,
          )

    def initPythonConsole(self, fields):
        """Initialize the Python console widget (dock is created by MainWindow)."""
        from director.python_console import PythonConsoleWidget
        
        console_widget_manager = None

        # Skip python console construction in test mode
        if not consoleapp.ConsoleApp.getTestingEnabled():
            console_widget_manager = PythonConsoleWidget()

        def register_application_fields(fields):
            script_context.push_variables(fields=fields)
            if console_widget_manager:
                variables = dict(fields.globalsDict)
                variables['fields'] = fields
                variables['view'] = fields.view
                variables['quit'] = fields.app.quit
                variables['exit'] = fields.app.exit
                console_widget_manager.push_variables(variables)
        
        return FieldContainer(pythonConsoleWidget=console_widget_manager, register_application_fields=register_application_fields)

    def initMainToolBar(self, fields):

        # viewcolors.ViewBackgroundLightHandler not yet ported - commented out for now
        # from director import viewcolors

        app = fields.app
        toolBar = app.addToolBar('Main Toolbar')
        
        # Icon resources not yet set up - use text-only for now
        app.addToolBarAction(toolBar, 'Python Console', Icons.Python, callback=app.showPythonConsole)
        toolBar.addSeparator()

        terrainModeAction = app.addToolBarAction(toolBar, 'Camera Free Rotate', Icons.CameraRotate)

        # lightAction = app.addToolBarAction(toolBar, 'Background Light', None)
        # viewBackgroundLightHandler not yet implemented

        app.addToolBarAction(toolBar, 'Reset Camera', Icons.ResetCamera, 
                           callback=lambda: applogic.resetCamera(view=fields.view))

        def getFreeCameraMode():
            # Free camera mode is when terrain interactor is NOT active
            return not fields.view.isTerrainInteractor()

        def setFreeCameraMode(enabled):
            if enabled:
                fields.view.setTrackballInteractor()
            else:
                fields.view.setTerrainInteractor()

        terrainToggle = applogic.ActionToggleHelper(terrainModeAction, getFreeCameraMode, setFreeCameraMode)

        # viewBackgroundLightHandler = viewcolors.ViewBackgroundLightHandler(fields.viewOptions, fields.gridObj,
        #                         lightAction)
        # TODO: Implement ViewBackgroundLightHandler when viewcolors is ported

        return FieldContainer(
            # viewBackgroundLightHandler=viewBackgroundLightHandler,
            terrainToggle=terrainToggle,
            mainToolbar=toolBar
        )

    def initUndoRedo(self, fields):

        undoStack = QtGui.QUndoStack()
        undoView = QtWidgets.QUndoView(undoStack)
        undoView.setEmptyLabel('Start')
        undoView.setWindowTitle('History')
        undoDock = fields.app.addWidgetToDock(undoView, QtCore.Qt.LeftDockWidgetArea, visible=False)
        undoAction = undoStack.createUndoAction(undoStack)
        redoAction = undoStack.createRedoAction(undoStack)
        undoAction.setShortcut(QtGui.QKeySequence('Ctrl+Z'))
        redoAction.setShortcut(QtGui.QKeySequence('Ctrl+Shift+Z'))

        fields.app.editMenu.addAction(undoAction)
        fields.app.editMenu.addAction(redoAction)

        return FieldContainer(
            undoDock=undoDock,
            undoStack=undoStack,
            undoView=undoView,
            undoAction=undoAction,
            redoAction=redoAction
        )

    def initGlobalModules(self, fields):

        import qtpy.QtCore as QtCore
        import qtpy.QtWidgets as QtWidgets
        import qtpy.QtGui as QtGui
        import director.objectmodel as om
        import director.consoleapp as consoleapp
        import director.visualization as vis
        import director.applogic as applogic
        from director import transformUtils
        from director import filterUtils
        from director import ioUtils
        import director.vtkAll as vtk
        from director import vtkNumpy as vnp
        from director.debugVis import DebugData
        from director.timercallback import TimerCallback
        from director.fieldcontainer import FieldContainer
        import numpy as np
        import os
        import sys

        modules = dict(locals())
        del modules['fields']
        del modules['self']
        fields.globalsDict.update(modules)

    def initGlobals(self, fields):
        try:
            globalsDict = fields.globalsDict
        except AttributeError:
            globalsDict = dict()
        if globalsDict is None:
            globalsDict = dict()
        return FieldContainer(globalsDict=globalsDict)

    def initRunScriptFunction(self, fields):

        def runScript(filename, commandLineArgs=None):
            commandLineArgs = commandLineArgs or []
            args = dict(__file__=filename,
                        _argv=[filename] + commandLineArgs,
                        __name__='__main__')
            try:
                with open(filename, 'r') as f:
                    code = compile(f.read(), filename, 'exec')
                exec(code, args)
            finally:
                del args['__name__']
                del args['__file__']
                del args['_argv']
                fields.pythonConsoleWidget.push_variables(args)

        def runModule(moduleName):
            if not moduleName:
                return
            args = {}
            try:
                args = runpy.run_module(moduleName, run_name="__main__", alter_sys=True)
            finally:
                fields.pythonConsoleWidget.push_variables(args)

        return FieldContainer(runScript=runScript, runModule=runModule)

    def initScriptLoader(self, fields):
        def loadScripts():
            args = fields.commandLineArgs

            modules = getattr(args, 'modules', [])
            for moduleName in modules:
                fields.runModule(moduleName)

            scripts = getattr(args, 'scripts', [])
            for scriptArgs in scripts:
                fields.runScript(scriptArgs[0], scriptArgs[1:])

        consoleapp.ConsoleApp.registerStartupCallback(loadScripts)

        return FieldContainer()


    def initOpenMeshDataHandler(self, fields):
        from director import opendatahandler
        openDataHandler = opendatahandler.OpenDataHandler(fields.app)

        def loadData():
            # flatten list of lists
            data_files = fields.commandLineArgs.data_files
            data_files = [item for sublist in data_files for item in sublist]
            for filename in data_files:
                openDataHandler.openGeometry(filename)
            if data_files:
                om.addChildPropertySync(openDataHandler.getRootFolder())
            fields.view.resetCamera()

        fields.app.registerStartupCallback(loadData)

        return FieldContainer(openDataHandler=openDataHandler)

    def initOutputConsole(self, fields):
        from director import outputconsole
        outputConsole = outputconsole.OutputConsole()
        outputConsole.addToAppWindow(fields.app, visible=False)
        applogic.addShortcut(fields.mainWindow, 'F9', outputConsole.toggleDock)

        return FieldContainer(outputConsole=outputConsole)
    
    def initStartupRender(self, fields):
        def startupRender():
            fields.view.forceRender()
            fields.app.applicationInstance().processEvents()
        fields.app.registerStartupCallback(startupRender, priority=0)
        return FieldContainer()

    def initProfilerTool(self, fields):
        """Initialize profiler tool menu action."""
        from director.profiler import Profiler
        
        class ProfilerToolMenu(object):
            """Manages the profiler tool menu action."""
            
            def __init__(self, toolsMenu):
                self.toolsMenu = toolsMenu
                self.profiler = None
                self.action = self.toolsMenu.addAction('Start &Profiler')
                self.action.setCheckable(True)
                self.action.triggered.connect(self._onToggled)
            
            def _onToggled(self, checked):
                """Handle action toggle."""
                if checked:
                    # Start profiling
                    self.profiler = Profiler()
                    self.profiler.start()
                    self.action.setText('Stop &Profiler')
                else:
                    # Stop profiling
                    if self.profiler:
                        self.profiler.stop()
                        self.profiler = None
                    self.action.setText('Start &Profiler')
        
        profilerTool = ProfilerToolMenu(fields.app.toolsMenu)
        return FieldContainer(profilerTool=profilerTool)

    def initScreenRecorder(self, fields):
        """Initialize screen recorder tool."""
        from director.screen_recorder import ScreenRecorder
        
        screen_recorder = ScreenRecorder(
            main_window=fields.app.mainWindow,
            view=fields.view
        )
        
        # Add to toolbar
        toolbar = fields.mainToolbar
        toolbar.addSeparator()
        toolbar.addWidget(screen_recorder.get_widget())
        
        return FieldContainer(screen_recorder=screen_recorder)

    def initWaitCursor(self, fields):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            
        def restore():
            QtWidgets.QApplication.restoreOverrideCursor()
        
        consoleapp.ConsoleApp.registerStartupCallback(restore, priority=100)


def construct(**kwargs):
    """
    Construct a MainWindowApp using the component factory.
    
    Args:
        **kwargs: Additional fields to pass to component factory
    """
    fact = ComponentFactory()
    fact.register(MainWindowAppFactory)

    # Ensure QApplication exists
    MainWindowApp.applicationInstance()

    fields = fact.construct(**kwargs)
    fields.register_application_fields(fields)
    return fields
