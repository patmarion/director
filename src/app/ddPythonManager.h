#ifndef __ddPythonManager_h
#define __ddPythonManager_h

#include <ctkAbstractPythonManager.h>
#include "ddAppConfigure.h"


class ctkPythonConsole;

class DD_APP_EXPORT ddPythonManager : public ctkAbstractPythonManager
{
    Q_OBJECT

public:

  ddPythonManager(QObject* parent=0);
  virtual ~ddPythonManager();

  void setupConsole(QWidget* parent);

  ctkPythonConsole* consoleWidget() const;

  static QString appSitePackagesDir();

  void setSysArgv(const QStringList& args);
  void setPythonPath();

public slots:

  void showConsole();
  void onExecuteFile(const QString& filename);
  void handleCommandLineArgs();
  void loadPlugin(const QString& filename, const QString& functionName);

protected:

  virtual void preInitialization();
  virtual void executeInitializationScripts();

  void setupConsoleShortcuts();

  class ddInternal;
  ddInternal* Internal;

  Q_DISABLE_COPY(ddPythonManager);
};

#endif
