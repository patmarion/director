"""Application settings utilities for saving/restoring window state."""



def saveState(settings, widget, key):
    """Save widget state to settings."""
    settings.beginGroup(key)
    settings.setValue('position', widget.pos())
    settings.setValue('size', widget.size())
    if hasattr(widget, 'saveState'):
        settings.setValue('state', widget.saveState())
    settings.endGroup()


def restoreState(settings, widget, key):
    """Restore widget state from settings."""
    settings.beginGroup(key)
    
    if settings.contains('size'):
        widget.resize(settings.value('size'))
    
    if settings.contains('position'):
        widget.move(settings.value('position'))
    
    if settings.contains('state') and hasattr(widget, 'restoreState'):
        widget.restoreState(settings.value('state'))
    
    settings.endGroup()

