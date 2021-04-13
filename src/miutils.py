# -*- coding: utf-8 -*-
# 

import aqt
from aqt.qt import *
from os.path import dirname, join

addon_path = dirname(__file__)

def miInfo(text, parent=False, level = 'msg'):
    if level == 'wrn':
        title = "Migaku Flexible Grading Warning"
    elif level == 'not':
        title = "Migaku Flexible Grading Notice"
    elif level == 'err':
        title = "Migaku Flexible Grading Error"
    else:
        title = "Migaku Flexible Grading Editor"
    if parent is False:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    icon = QIcon(join(addon_path, 'icons', 'Migaku.png'))
    mb = QMessageBox(parent)
    mb.setText(text)
    mb.setWindowIcon(icon)
    mb.setWindowTitle(title)
    b = mb.addButton(QMessageBox.Ok)
    b.setFixedSize(100, 30)
    b.setDefault(True)

    return mb.exec_()


def miAsk(text, parent=None):

    msg = QMessageBox(parent)
    msg.setWindowTitle("Migaku Flexible Grading")
    msg.setText(text)
    icon = QIcon(join(addon_path, 'icons', 'Migaku.png'))
    b = msg.addButton(QMessageBox.Yes)
    b.setFixedSize(100, 30)
    b.setDefault(True)
    c = msg.addButton(QMessageBox.No)
    c.setFixedSize(100, 30)
    msg.setWindowIcon(icon)
    msg.exec_()
    if msg.clickedButton() == b:
        return True
    else:
        return False
