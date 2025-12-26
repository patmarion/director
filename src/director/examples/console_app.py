import director.consoleapp as consoleapp

app = consoleapp.ConsoleApp()
app.showPythonConsole()
view = app.createView()
view.show()

# This starts the Qt event loop and blocks until the application exits
app.start()
