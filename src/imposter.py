#!/usr/bin/env python
#  Copyright (C) 2012  BMW Car IT GmbH. All rights reserved.
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License version 2 as
#  published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import signal
import sys
import os

from PyQt4 import uic
from PyQt4.QtCore import SIGNAL, SLOT, QObject, QTimer, Qt
from PyQt4.QtGui import *

import distutils.sysconfig

import traceback

import dbus
import dbus.service
import dbus.mainloop.qt
dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)

signal.signal(signal.SIGINT, signal.SIG_DFL)


def get_resource_path(filename):
    if __name__ == '__main__':
        return filename

    return os.path.join(distutils.sysconfig.get_python_lib(),
                'imposter', filename)


class AgentUi(QDialog):
    def __init__(self, parent, path, fields):
        QDialog.__init__(self, parent)
        ui_class, widget_class = uic.loadUiType(
                                    get_resource_path('ui/agent.ui'))
        self.ui = ui_class()
        self.ui.setupUi(self)

        if 'Passphrase' in fields:
            self.ui.label1.setText('Passphrase')
            self.ui.label2.setVisible(False)
            self.ui.lineEdit2.setVisible(False)
        else:
            print 'No method to answer the input request'

    def accept(self):
        self.hide()
        return True

    def reject(self):
        self.hide()
        return True

    def get_response(self):
        response = {}
        response['Passphrase'] = str(self.ui.lineEdit1.text())

        print response

        return response


class Agent(dbus.service.Object):
    def __init__(self, parent):
        dbus.service.Object.__init__(self)
        self.parent = parent

    @dbus.service.method('net.connman.Agent',
                in_signature='', out_signature='')
    def Release(self):
        print 'Release'

    @dbus.service.method('net.connman.Agent',
                in_signature='os', out_signature='')
    def ReportError(self, path, error):
        print 'ReportError'
        print path, error

    @dbus.service.method('net.connman.Agent',
                in_signature='os', out_signature='')
    def RequestBrowser(self, path, url):
        print 'RequestBrowser'

    @dbus.service.method('net.connman.Agent',
                in_signature='oa{sv}', out_signature='a{sv}',
                async_callbacks=('return_cb', 'raise_cb'))
    def RequestInput(self, path, fields, return_cb, raise_cb):
        print 'RequestInput'

        def handleRequest():
            dialog = AgentUi(self.parent, path, fields)
            dialog.exec_()

            return_cb(dialog.get_response())

        QTimer.singleShot(10, handleRequest)

    @dbus.service.method('net.connman.Agent',
                in_signature='', out_signature='')
    def Cancel(self):
        print 'Cancel'


class ServiceEntry(QWidget):
    def __init__(self, parent, path, properties):
        QWidget.__init__(self, parent)

        ui_class, widget_class = uic.loadUiType(
                get_resource_path('ui/service_entry.ui'))
        self.ui = ui_class()
        self.ui.setupUi(self)

        self.bus = dbus.SystemBus()
        self.path = path
        self.properties = properties

        self.service = dbus.Interface(
                self.bus.get_object('net.connman', path),
                'net.connman.Service')

        self.connect(self.ui.pb_Connect, SIGNAL('clicked()'),
                self.cb_clicked)

        self.connect(self.ui.cb_AutoConnect, SIGNAL('clicked()'),
                self.cb_auto_connect)

        self.connect(self.ui.pb_Remove, SIGNAL('clicked()'),
                self.cb_remove)

        self.ui.cb_Favorite.setEnabled(False)

        self.set_name()
        self.set_state()
        self.set_button()
        self.set_favorite()
        self.set_autoconnect()

    def set_name(self):
        if 'Name' not in self.properties:
            self.ui.la_Name.setText('bug?')
            return

        self.ui.la_Name.setText(self.properties['Name'])

    def set_state(self):
        if 'State' not in self.properties:
            self.ui.la_State.setText('bug?')
            return

        self.ui.la_State.setText(self.properties['State'])

    def set_button(self):
        if 'State' not in self.properties:
            self.ui.pb_Connect.setText('bug?')
            return

        if self.properties['State'] in ['ready', 'connected', 'online']:
            self.ui.pb_Connect.setText('Disconnect')
        else:
            self.ui.pb_Connect.setText('Connect')

    def set_favorite(self):
        if 'Favorite' not in self.properties:
            print 'Favorite: bug?'
            return

        favorite = bool(self.properties['Favorite'])
        print 'Favorite: ', favorite
        self.ui.cb_Favorite.setChecked(favorite)

    def set_autoconnect(self):
        if 'AutoConnect' not in self.properties:
            print 'AutoConnect: bug?'
            return

        autoconnect = bool(self.properties['AutoConnect'])
        self.ui.cb_AutoConnect.setChecked(autoconnect)

    def cb_clicked(self):
        if self.properties['State'] in ['ready', 'connected', 'online']:
            self.service.Disconnect()
        else:
            self.service.Connect()

    def cb_auto_connect(self):
        if 'AutoConnect' not in self.properties:
            print 'AutoConnect: bug?'
            return

        autoconnect = not self.properties['AutoConnect']

        self.service.SetProperty('AutoConnect', dbus.Boolean(autoconnect))

    def cb_remove(self):
        self.service.Remove()

    def property_changed(self, name, value):
        print 'Service PropertyChanged: ', name

        self.properties[name] = value

        if name == 'Name':
            self.set_name()
        elif name == 'State':
            self.set_state()
            self.set_button()
        elif name == 'Favorite':
            self.set_favorite()
        elif name == 'AutoConnect':
            self.set_autoconnect()


class ServicePane(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        ui_class, widget_class = uic.loadUiType(
                get_resource_path('ui/service_pane.ui'))
        self.ui = ui_class()
        self.ui.setupUi(self)

        self.services = {}

    def changed_services(self, services):
        for i in range(self.ui.vlayout.count()):
            item = self.ui.vlayout.takeAt(0)
            self.ui.vlayout.removeItem(item)

        for path, properties in services:
            entry = None
            if path in self.services:
                entry = self.services[path]
            else:
                entry = ServiceEntry(self, path, properties)
                self.services[path] = entry

            self.ui.vlayout.addWidget(entry)

    def remove_services(self, services):
        for path in services:
            print 'Service removed: ', path
            self.services[path].deleteLater()
            del self.services[path]

    def property_changed(self, name, value, path, interface):
        if path in self.services:
            self.services[path].property_changed(name, value)

    def clear(self):
        for path, _ in self.services.items():
            print 'Remove Service: ', path
            self.remove_service(path)


class TechnologyEntry(QWidget):
    def __init__(self, parent, path, properties):
        QWidget.__init__(self, parent)

        ui_class, widget_class = uic.loadUiType(
                get_resource_path('ui/technology_entry.ui'))
        self.ui = ui_class()
        self.ui.setupUi(self)

        self.bus = dbus.SystemBus()
        self.path = path
        self.properties = properties

        self.visible = True
        self.toggle_visible()

        for name, value in properties.items():
            self.property_changed(name, value)

        self.connect(self.ui.pb_ToggleVisible, SIGNAL('clicked()'),
                 self.toggle_visible)
        self.connect(self.ui.pb_Scan, SIGNAL('clicked()'),
                self.pb_scan_clicked)
        self.connect(self.ui.pb_Powered, SIGNAL('clicked()'),
                self.pb_powered_clicked)
        self.connect(self.ui.pb_Tethering, SIGNAL('clicked()'),
                self.pb_tethering_clicked)
        self.connect(self.ui.le_TetheringIdentifier,
                SIGNAL('editingFinished()'),
                self.le_tethering_identifier_changed)
        self.connect(self.ui.le_TetheringPassphrase,
                SIGNAL('editingFinished()'),
                self.le_tethering_passphrase_changed)

        self.technology = dbus.Interface(
                self.bus.get_object('net.connman', path),
                'net.connman.Technology')

    def toggle_visible(self):
        self.visible = not self.visible

        self.ui.label1.setVisible(self.visible)
        self.ui.label2.setVisible(self.visible)
        self.ui.label3.setVisible(self.visible)
        self.ui.label4.setVisible(self.visible)
        self.ui.label5.setVisible(self.visible)
        self.ui.label6.setVisible(self.visible)
        self.ui.pb_Scan.setVisible(self.visible)
        self.ui.la_Connected.setVisible(self.visible)
        self.ui.la_Type.setVisible(self.visible)
        self.ui.pb_Tethering.setVisible(self.visible)
        self.ui.le_TetheringIdentifier.setVisible(self.visible)
        self.ui.le_TetheringPassphrase.setVisible(self.visible)

    def pb_scan_clicked(self):
        self.technology.Scan()

    def pb_powered_clicked(self):
        enable = not self.properties['Powered']
        self.technology.SetProperty('Powered', enable)

    def pb_tethering_clicked(self):
        enable = not self.properties['Tethering']
        self.technology.SetProperty('Tethering', enable)

    def le_tethering_identifier_changed(self):
        identifier = str(self.ui.le_TetheringIdentifier.text())
        if ('TetheringIdentifier' in self.properties and
                identifier == self.properties['TetheringIdentifier']):
            return

        self.technology.SetProperty('TetheringIdentifier', identifier)

    def le_tethering_passphrase_changed(self):
        passphrase = str(self.ui.le_TetheringPassphrase.text())
        if ('TetheringPassphrase' in self.properties and
                passphrase == self.properties['TetheringPassphrase']):
            return

        self.technology.SetProperty('TetheringPassphrase', passphrase)

    def property_changed(self, name, value):
        print 'Technology PropertyChanged: ', name

        self.properties[name] = value

        if name == 'Powered':
            val = 'disabled'
            if value:
                val = 'enabled'
            self.ui.pb_Powered.setText(val)
        elif name == 'Connected':
            val = 'true'
            if value:
                val = 'false'
            self.ui.la_Connected.setText(val)
        elif name == 'Name':
            self.ui.la_Name.setText(value)
        elif name == 'Type':
            self.ui.la_Type.setText(value)
        elif name == 'Tethering':
            val = 'disabled'
            if value:
                val = 'enabled'
            self.ui.pb_Tethering.setText(val)
        elif name == 'TetheringIdentifier':
            self.ui.le_TetheringIdentifier.setText(value)
        elif name == 'TetheringPassphrase':
            self.ui.le_TetheringPassphrase.setText(value)


class TechnologyPane(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        self.layout = QVBoxLayout(self)
        self.techs = {}

    def add_technology(self, path, properties):
        if path in self.techs:
            return

        print 'Add Technology ', path
        entry = TechnologyEntry(self, path, properties)
        self.layout.addWidget(entry)
        self.techs[path] = entry

    def remove_technology(self, path):
        print 'Remove Technology ', path
        self.techs[path].deleteLater()
        del self.techs[path]

    def property_changed(self, name, value, path, interface):
        if not path in self.techs:
            return
        self.techs[path].property_changed(name, value)

    def clear(self):
        for path, properties in self.techs.items():
            self.remove_technology(path)


class ManagerPane(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        ui_class, widget_class = uic.loadUiType(
                get_resource_path('ui/manager.ui'))
        self.ui = ui_class()
        self.ui.setupUi(self)

        self.properties = {}
        self.manager = None

        self.connect(self.ui.pb_OfflineMode, SIGNAL('clicked()'),
                self.pb_offline_mode_clicked)
        self.connect(self.ui.pb_SessionMode, SIGNAL('clicked()'),
                self.pb_session_mode_clicked)

    def set_manager(self, manager):
        self.manager = manager

    def pb_offline_mode_clicked(self):
        if not self.manager:
            return

        enable = not self.properties['OfflineMode']
        self.manager.SetProperty('OfflineMode', enable)

    def pb_session_mode_clicked(self):
        if not self.manager:
            return

        enable = not self.properties['SessionMode']
        self.manager.SetProperty('SessionMode', enable)

    def property_changed(self, name, value):
        print 'Manager PropertyChanged: ', name

        self.properties[name] = value

        if name == 'State':
            self.ui.la_State.setText(value)
        elif name == 'OfflineMode':
            str = 'disabled'
            if value:
                str = 'enabled'
            self.ui.pb_OfflineMode.setText(str)
        elif name == 'SessionMode':
            str = 'disabled'
            if value:
                str = 'enabled'
            self.ui.pb_SessionMode.setText(str)

    def clear(self):
        self.manager = None
        self.ui.la_State.setText('ConnMan is not running')
        self.ui.pb_OfflineMode.setText('')
        self.ui.pb_SessionMode.setText('')


class MainWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setFocusPolicy(Qt.StrongFocus)
        self.shutdown_system = False

        self.bus = dbus.SystemBus()
        self.manager = None
        self.agent = None
        self.agent_path = '/imposter_agent'

        self.setup_ui()
        self.create_system_tray()

        try:
            self.bus.watch_name_owner('net.connman',
                    self.connman_name_owner_changed)
        except dbus.DBusException:
            traceback.print_exc()
            exit(1)

    def setup_ui(self):
        self.resize(500, 300)
        self.mainLayout = QHBoxLayout(self)
        self.setLayout(self.mainLayout)

        self.tech_pane = TechnologyPane()
        self.manager_pane = ManagerPane()
        self.service_pane = ServicePane()

        # Add technology and manager pane
        layout = QVBoxLayout()
        layout.addWidget(self.tech_pane)
        spacer = QSpacerItem(20, 40,
                QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)
        layout.addWidget(self.manager_pane)
        self.mainLayout.addLayout(layout)

        # Add services pane
        self.mainLayout.addWidget(self.service_pane)

        self.setLayout(self.mainLayout)

    def create_system_tray(self):
        self.quitAction = QAction(self.tr('&Quit'), self)
        QObject.connect(self.quitAction,
                       SIGNAL('triggered()'), qApp,
                       SLOT('quit()'))

        self.trayIconMenu = QMenu(self)
        self.trayIconMenu.addAction(self.quitAction)
        self.trayIcon = QSystemTrayIcon(self)
        self.trayIcon.setContextMenu(self.trayIconMenu)
        self.trayIcon.setIcon(
                QIcon(get_resource_path('icons/network-active.png')))

        self.trayIcon.show()

        traySignal = 'activated(QSystemTrayIcon::ActivationReason)'
        QObject.connect(self.trayIcon, SIGNAL(traySignal),
                self.__icon_activated)

    def closeEvent(self, event):
        self.hide()
        self.trayIcon.show()
        if self.shutdown_system == False:
            event.ignore()

    def set_shutdown(self, value):
        self.shutdown_system = value

    def __icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
                self.trayIcon.show()
            else:
                self.show()

    def connman_name_owner_changed(self, proxy):
        try:
            if proxy:
                print 'ConnMan appeared on D-Bus ', str(proxy)
                self.connman_down() # make sure we really clear it
                                    # stuff, e.g. this is needed when
                                    # connman crashes. The python
                                    # D-Bus binding seems not to call
                                    # the down all the time.
                self.connman_up()
            else:
                print 'ConnMan disappeared on D-Bus'
                self.connman_down()

        except dbus.DBusException:
            traceback.print_exc()
            exit(1)

    def property_changed(self, name, value, path, interface):
        if interface == 'net.connman.Service':
            self.service_pane.property_changed(name, value,
                               path, interface)
        elif interface == 'net.connman.Technology':
            self.tech_pane.property_changed(name, value,
                            path, interface)
        elif interface == 'net.connman.Manager':
            self.manager_pane.property_changed(name, value)

    def technology_added(self, path, properties):
        self.tech_pane.add_technology(path, properties)

    def technology_removed(self, path):
        self.tech_pane.remove_technology(path)

    def services_changed(self, changed_services, removed_services):
        self.service_pane.remove_services(removed_services)
        self.service_pane.changed_services(changed_services)

    def services_removed(self, services):
        for path in services:
            self.service_pane.remove_service(path)

    def connman_up(self):
        self.manager = dbus.Interface(self.bus.get_object('net.connman', '/'),
                          'net.connman.Manager')

        self.agent = Agent(self)
        self.agent.add_to_connection(self.bus, self.agent_path)
        self.manager.RegisterAgent(self.agent_path)

        self.bus.add_signal_receiver(self.property_changed,
                    bus_name='net.connman',
                    signal_name='PropertyChanged',
                    path_keyword='path',
                    interface_keyword='interface')

        self.bus.add_signal_receiver(self.technology_added,
                    bus_name='net.connman',
                    signal_name='TechnologyAdded')
        self.bus.add_signal_receiver(self.technology_removed,
                    bus_name='net.connman',
                    signal_name='TechnologyRemoved')
        self.bus.add_signal_receiver(self.services_changed,
                    bus_name='net.connman',
                    signal_name='ServicesChanged')

        for path, properties in self.manager.GetTechnologies():
            self.technology_added(path, properties)

        self.services_changed(self.manager.GetServices(), [])

        self.manager_pane.set_manager(self.manager)
        for name, value in self.manager.GetProperties().items():
            self.manager_pane.property_changed(name, value)

    def connman_down(self):
        if self.agent:
            self.agent.remove_from_connection(self.bus, self.agent_path)
            self.agent = None

        if self.manager:
            self.manager = None

        self.tech_pane.clear()
        self.manager_pane.clear()
        self.service_pane.clear()


class MyApplication(QApplication):
    def set_widget(self, widget):
        self.main_windget = widget

    def commitData(self, sm):
        self.main_windget.set_shutdown(True)

def main():
    app = MyApplication(sys.argv)
    mainwidget = MainWidget()
    mainwidget.show()
    app.set_widget(mainwidget)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
