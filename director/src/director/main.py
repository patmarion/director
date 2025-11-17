from director import mainwindowapp


def main():
    fields = mainwindowapp.construct()
    return fields.app.start()


if __name__ == '__main__':
    main()