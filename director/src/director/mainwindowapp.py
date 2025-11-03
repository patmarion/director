"""MainWindowApp for Director 2.0 - component-based application factory."""

import os
import sys
from director.componentgraph import ComponentFactory
from director import consoleapp
import director.objectmodel as om
import director.visualization as vis
from director.fieldcontainer import FieldContainer
from director import applogic
from director import appsettings
from director import argutils

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
        self._python_console_dock = None
        self._python_console_widget_manager = None

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

    def start(self, enableAutomaticQuit=True, restoreWindow=True):
        if not consoleapp.ConsoleApp.getTestingEnabled() and restoreWindow:
            self.initWindowSettings()
        self.mainWindow.show()
        self.mainWindow.raise_()
        return consoleapp.ConsoleApp.start(enableAutomaticQuit)

    @staticmethod
    def applicationInstance():
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        return app

    def showPythonConsole(self):
        """Show Python console as a dock widget."""
        if self._python_console_widget_manager is None:
            self.showErrorMessage("Python console not available. Please install qtconsole.")
            return
        
        if self._python_console_dock is None:
            # This shouldn't happen if component factory initialized it properly
            self.showErrorMessage("Python console dock widget not initialized.")
            return
        
        # Toggle visibility
        if self._python_console_dock.isVisible():
            self._python_console_dock.hide()
        else:
            self._python_console_dock.show()
            self._python_console_dock.raise_()

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
        dock.setVisible(visible)
        self.addWidgetToViewMenu(dock)
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
            # Try to load icon, but handle gracefully if resource doesn't exist
            try:
                icon = QtGui.QIcon(icon)
            except:
                icon = None  # Use no icon if resource unavailable
        
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
            # 'ViewOptions' : ['View', 'ObjectModel'],  # ViewOptionsItem not yet implemented
            'MainToolBar' : ['View', 'Grid', 'MainWindow'],  # Removed ViewOptions dependency
            'ViewBehaviors' : ['View'],
            'Grid': ['View', 'ObjectModel'],
            'PythonConsole' : [],  # Create console widget
            'MainWindow' : ['View', 'ObjectModel', 'PythonConsole'],  # Needs PythonConsole to create dock
            'AdjustedClippingRange' : ['View'],
            'RunScriptFunction' : ['Globals'],
            'ScriptLoader' : ['MainWindow', 'RunScriptFunction']}

        disabledComponents = []

        return components, disabledComponents

    def initView(self, fields):
        from director.vtk_widget import VTKWidget
        view = VTKWidget()
        applogic.setCurrentRenderView(view)
        #applogic.setCameraTerrainModeEnabled(view, True)
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
        grid.setProperty('Surface Mode', 'Surface with edges')
        grid.setProperty('Color', [1,1,1])
        grid.setProperty('Alpha', 0.05)
        fields.view._grid_obj = grid
        applogic.resetCamera(viewDirection=[-1, -1, -0.3], view=fields.view)
        return FieldContainer(grid=grid)

    def initViewBehaviors(self, fields):
        from director import viewbehaviors
        viewBehaviors = viewbehaviors.ViewBehaviors(fields.view)
        return FieldContainer(viewBehaviors=viewBehaviors)

    def initViewOptions(self, fields):
        # ViewOptionsItem is not yet implemented in Director 2.0
        # TODO: Implement ViewOptionsItem when needed
        # viewOptions = vis.ViewOptionsItem(fields.view)
        # fields.objectModel.addToObjectModel(viewOptions, parentObj=fields.objectModel.findObjectByName('scene'))
        # viewOptions.setProperty('Background color', [0.3, 0.3, 0.35])
        # viewOptions.setProperty('Background color 2', [0.95,0.95,1])
        # return FieldContainer(viewOptions=viewOptions)
        return FieldContainer(viewOptions=None)

    def initAdjustedClippingRange(self, fields):
        '''This setting improves the near plane clipping resolution.
        Drake often draws a very large ground plane which is detrimental to
        the near clipping for up close objects.  The trade-off is Z buffer
        resolution but in practice things look good with this setting.'''
        renderer = fields.view.renderer()
        if renderer:
            renderer.SetNearClippingPlaneTolerance(0.0005)
        return FieldContainer()

    def initMainWindow(self, fields):

        organizationName = 'RobotLocomotion'
        applicationName = 'DirectorMainWindow'
        windowTitle = 'Director App'
        windowIcon = None  # Icon resources not yet set up

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
            try:
                app.mainWindow.setWindowIcon(QtGui.QIcon(windowIcon))
            except:
                pass  # Ignore if icon resource unavailable

        # Create Python console dock if console widget is available
        if fields.pythonConsoleWidget:
            pythonConsoleDock = app.addWidgetToDock(fields.pythonConsoleWidget.get_widget(), QtCore.Qt.BottomDockWidgetArea, visible=False)
            app._python_console_dock = pythonConsoleDock
            app._python_console_widget_manager = fields.pythonConsoleWidget

        sceneBrowserDock = app.addWidgetToDock(fields.objectModel.getTreeWidget(),
                              QtCore.Qt.LeftDockWidgetArea, visible=True)
        propertiesDock = app.addWidgetToDock(fields.objectModel.getPropertiesPanel(),
                              QtCore.Qt.LeftDockWidgetArea, visible=True)

        app.addViewMenuSeparator()

        def toggleObjectModelDock():
            newState = not sceneBrowserDock.isVisible()
            sceneBrowserDock.setVisible(newState)
            propertiesDock.setVisible(newState)

        applogic.addShortcut(app.mainWindow, 'F1', toggleObjectModelDock)

        # Get command line args from fields if provided, otherwise parse them
        commandLineArgs = None
        if hasattr(fields, 'command_line_args'):
            commandLineArgs = fields.command_line_args
        else:
            import argparse
            parser = argparse.ArgumentParser()
            argutils.add_standard_args(parser)
            commandLineArgs = parser.parse_known_args()[0]

        return FieldContainer(
          app=app,
          mainWindow=app.mainWindow,
          sceneBrowserDock=sceneBrowserDock,
          propertiesDock=propertiesDock,
          pythonConsoleDock=app._python_console_dock,
          toggleObjectModelDock=toggleObjectModelDock,
          commandLineArgs=commandLineArgs
          )

    def initPythonConsole(self, fields):
        """Initialize the Python console widget (dock is created by MainWindow)."""
        from director.python_console import PythonConsoleWidget, QTCONSOLE_AVAILABLE
        
        if not QTCONSOLE_AVAILABLE:
            return FieldContainer(pythonConsoleWidget=None)
        
        # Set up minimal namespace - will be updated later with more variables
        namespace = {}
        
        try:
            console_widget_manager = PythonConsoleWidget(namespace=namespace)
        except RuntimeError:
            # Console widget creation failed
            return FieldContainer(pythonConsoleWidget=None)
        
        return FieldContainer(pythonConsoleWidget=console_widget_manager)


    def initMainToolBar(self, fields):

        # viewcolors.ViewBackgroundLightHandler not yet ported - commented out for now
        # from director import viewcolors

        app = fields.app
        toolBar = app.addToolBar('Main Toolbar')
        
        # Icon resources not yet set up - use text-only for now
        app.addToolBarAction(toolBar, 'Python Console', None, callback=app.showPythonConsole)
        toolBar.addSeparator()

        terrainModeAction = app.addToolBarAction(toolBar, 'Camera Free Rotate', None)

        # lightAction = app.addToolBarAction(toolBar, 'Background Light', None)
        # viewBackgroundLightHandler not yet implemented

        app.addToolBarAction(toolBar, 'Reset Camera', None, 
                           callback=lambda: applogic.resetCamera(view=fields.view))

        def getFreeCameraMode():
            return not applogic.getCameraTerrainModeEnabled(fields.view)

        def setFreeCameraMode(enabled):
            applogic.setCameraTerrainModeEnabled(fields.view, not enabled)

        terrainToggle = applogic.ActionToggleHelper(terrainModeAction, getFreeCameraMode, setFreeCameraMode)

        # viewBackgroundLightHandler = viewcolors.ViewBackgroundLightHandler(fields.viewOptions, fields.gridObj,
        #                         lightAction)
        # TODO: Implement ViewBackgroundLightHandler when viewcolors is ported

        return FieldContainer(
            # viewBackgroundLightHandler=viewBackgroundLightHandler,
            terrainToggle=terrainToggle
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

        globalsDict = fields.globalsDict

        def runScript(filename, commandLineArgs=None):
            commandLineArgs = commandLineArgs or []
            args = dict(__file__=filename,
                        _argv=[filename] + commandLineArgs,
                        __name__='__main__',
                        _fields=fields)
            prev_args = {}
            for k, v in args.items():
                if k in globalsDict:
                    prev_args[k] = globalsDict[k]
                globalsDict[k] = v
            try:
                with open(filename, 'r') as f:
                    code = compile(f.read(), filename, 'exec')
                exec(code, globalsDict)
            finally:
                for k in args.keys():
                    del globalsDict[k]
                for k, v in prev_args.items():
                    globalsDict[k] = v

        return FieldContainer(runScript=runScript)


    def initScriptLoader(self, fields):
        def loadScripts():
            if hasattr(fields.commandLineArgs, 'scripts') and fields.commandLineArgs.scripts:
                for scriptArgs in fields.commandLineArgs.scripts:
                    print("loading script")
                    print(scriptArgs)
                    fields.runScript(scriptArgs[0], scriptArgs[1:])
        fields.app.registerStartupCallback(loadScripts)
        return FieldContainer()


# MainWindowPanelFactory removed - optional panels not yet ported
# These included:
# - OpenDataHandler
# - ScreenGrabberPanel
# - CameraBookmarksPanel
# - CameraControlPanel
# - MeasurementPanel
# - OutputConsole
# - UndoRedo
# - DrakeVisualizer
# - TreeViewer
# - LCMGLRenderer
# These can be ported later as needed


def construct(command_line_args=None, **kwargs):
    """
    Construct a MainWindowApp using the component factory.
    
    Args:
        command_line_args: Parsed command-line arguments (from argutils)
        **kwargs: Additional fields to pass to component factory
    """
    fact = ComponentFactory()
    fact.register(MainWindowAppFactory)
    
    # Pass command_line_args through kwargs if provided
    if command_line_args is not None:
        kwargs['command_line_args'] = command_line_args
    
    fields = fact.construct(**kwargs)

    # Push variables to Python console if it exists
    if hasattr(fields, 'pythonConsoleWidget') and fields.pythonConsoleWidget is not None:
        fields.pythonConsoleWidget.push_variables({'fields': fields})
    
    return fields

def main(command_line_args=None, **kwargs):
    """
    Main entry point for MainWindowApp.
    
    Args:
        command_line_args: Parsed command-line arguments (optional, will parse if None)
        **kwargs: Additional arguments to pass to construct()
    """
    # Ensure QApplication exists
    MainWindowApp.applicationInstance()
    
    # Parse command line args if not provided
    if command_line_args is None:
        import argparse
        parser = argparse.ArgumentParser()
        argutils.add_standard_args(parser)
        command_line_args = parser.parse_known_args()[0]
    
    fields = construct(command_line_args=command_line_args, **kwargs)
    


    fields.app.start()


if __name__ == '__main__':
    main()

