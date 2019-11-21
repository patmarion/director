#ifndef __ddSortFilterProxyModel_h
#define __ddSortFilterProxyModel_h

#include <QSortFilterProxyModel>
#include "ddAppConfigure.h"


class DD_APP_EXPORT ddSortFilterProxyModel : public QSortFilterProxyModel
{
    Q_OBJECT

public:

  ddSortFilterProxyModel(QObject* parent=0) : QSortFilterProxyModel(parent)
  {

  }
protected:

  bool filterAcceptsRow(int sourceRow, const QModelIndex& sourceParent) const override
  {
    // check the current item
    bool result = QSortFilterProxyModel::filterAcceptsRow(sourceRow, sourceParent);
    QAbstractItemModel* model = this->sourceModel();
    QModelIndex currentIndex = model->index(sourceRow, 0, sourceParent);
    if (model->hasChildren(currentIndex)) {
      for (int i = 0; i < model->rowCount(currentIndex) && !result; ++i) {
          result = result || this->filterAcceptsRow(i, currentIndex);
      }
    }
    return result;
  }

private:
  Q_DISABLE_COPY(ddSortFilterProxyModel);
};

#endif
