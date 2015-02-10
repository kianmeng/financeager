#!/usr/bin/python

""" Defines the main Financeager class. """

# authorship information
__authors__     = ['Philipp Metzner']
__author__      = ','.join(__authors__)
__credits__     = []
__copyright__   = 'Copyright (c) 2014'
__license__     = 'GPL'

# maintanence information
__maintainer__  = 'Philipp Metzner'
__email__       = 'beth.aleph@yahoo.de'


from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QMessageBox, QCheckBox 
from PyQt4.QtCore import pyqtSlot 
from . import loadUi, _CURRENTMONTH_ 
from .. import settings 
from monthtab import MonthTab 
from newentrydialog import NewEntryDialog 
from statisticswindow import StatisticsWindow 
from settingsdialog import SettingsDialog 
from items import EntryItem, ExpenseItem, DateItem, CategoryItem

class FinanceagerWindow(QtGui.QMainWindow):
    """ MainWindow class for the Financeager application. """
    #TODO implement search function that list all entries corresp. to one name?
    
    def __init__(self, parent=None):
        super(FinanceagerWindow, self).__init__(parent)

        # load the ui
        loadUi(__file__, self)

        # define custom properties
        self.__year = None 
        # required in removeEntry() for index tracking
        self.__removeableIndex = None 
        # StatisticsWindow singleton
        self.__statWindow = None 
        # holds boolean value whether file is automatically saved at exit
        self.__autoSave = False 
        self.__fileName = None 

        # adjust layout
        self.monthsTabWidget.clear()
        
        # if specified, load xml file from command line argument
        if QtCore.QCoreApplication.instance().argc() > 1:
            import os.path 
            inputFile = QtCore.QCoreApplication.instance().argv()[1]
            if os.path.isfile(inputFile):
                self.loadYear(inputFile)
            else:
                print 'File does not exist!'

        # create connections
        self.action_New_Year.triggered.connect(self.newYear)
        self.action_New_Entry.triggered.connect(self.newEntry)
        self.action_Remove_Entry.triggered.connect(self.removeEntry)
        self.action_Load_Year.triggered.connect(self.loadYearFromUser)
        self.action_Statistics.toggled.connect(self.showStatistics)
        self.action_Settings.triggered.connect(self.showSettings)
        self.action_About.triggered.connect(self.showAbout)
        self.action_Quit.triggered.connect(self.close)
        
    
    def autoSave(self):
        return self.__autoSave 

    @pyqtSlot(bool)
    def setAutoSave(self, value):
        self.__autoSave = value 

    def closeEvent(self, event):
        """ 
        Reimplementation. 
        Asks the user whether to save the current year, then exits. 
        Also registers if the autoSave checkBox is checked.

        :param      event | QEvent emitted from close() signal
        """
        if self.__year is not None:
            if not self.__autoSave:
                question = QMessageBox(QMessageBox.Question, 
                        'Save file?', 'Do you want to save the current file to disk?')
                question.addButton(QMessageBox.Yes)
                question.addButton(QMessageBox.No)
                question.addButton(QMessageBox.Cancel)
                checkBox = QCheckBox('Always save at exit')
                checkBox.blockSignals(True)
                question.addButton(checkBox, QMessageBox.ActionRole)
                question.setDefaultButton(QMessageBox.Yes)
                question.exec_()
                buttonRole = question.buttonRole(question.clickedButton())
                if buttonRole == QMessageBox.YesRole or buttonRole == QMessageBox.NoRole:
                    self.__autoSave = checkBox.isChecked()
                    if buttonRole == QMessageBox.YesRole:
                        self.saveToXML()
                    event.accept()
                else: 
                    event.ignore()
            else:
                self.saveToXML()
                event.accept()
        else:
            event.accept()

    def currentMonthTab(self):
        """ 
        For simplicity. 
        :return     MonthTreeView 
        """
        return self.monthsTabWidget.currentWidget()

    def enableRemoveEntry(self, index):
        """
        Is called from the current month widget when an item is clicked. 
        Enables the remove entry action if item is of type entry or expense.

        :param      index | QModelIndex
        """
        item = index.model().itemFromIndex(index)
        self.action_Remove_Entry.setEnabled(isinstance(item.parent(), CategoryItem))
        self.__removeableIndex = index 

    @property 
    def fileName(self):
        return self.__fileName 

    @fileName.setter 
    def fileName(self, fileName):
        self.__fileName = fileName 

    def loadYear(self, inputFile):
        """
        Parses the inputFile and loads the content recursively.

        :param      inputFile | str 
        """
        import xml.etree.ElementTree as et 
        try:
            tree = et.parse(inputFile)
            root = tree.getroot()
        except IOError, err:
            QtGui.QMessageBox.warning(self, 'Error!', 
                    'An unexpected error occured during parsing the xml file: \n%s' % err)
            return 
        for child in root:
            month = str(child.get('value'))
            monthTab = MonthTab(self, month, False)
            monthTab.parseXMLtoModel([child.getchildren()[0]], monthTab.expendituresModel())
            monthTab.parseXMLtoModel([child.getchildren()[1]], monthTab.receiptsModel())
            monthTab.expendituresView.expandAll()
            monthTab.receiptsView.expandAll()
            self.monthsTabWidget.addTab(monthTab, month)
        self.setYear(int(root.get('value')), inputFile)
        self.setAutoSave(root.get('autoSave') == 'True')
    
    def loadYearFromUser(self):
        """
        Asks the user to choose an appropriate xml file. 
        Calls loadYear() if inputFile is valid.
        """
        inputFile = str(QtGui.QFileDialog.getOpenFileName(self, 'Load Year', 
            QtCore.QDir.currentPath(), 'xml file (*.xml)'))
        if inputFile:
            self.loadYear(inputFile)


    def newEntry(self):
        """ 
        Prompts the user with a dialog to input a new entry. 
        Writes the entry to the appropriate category in the current month tab. 
        """
        dialog = NewEntryDialog(self)
        if dialog.exec_():
            category = unicode(dialog.categoryCombo.currentText())
            if category in self.currentMonthTab().receiptsModel().categoriesStringList():
                model = self.currentMonthTab().receiptsModel()
            else:
                model = self.currentMonthTab().expendituresModel()
            catItem = model.findItems(category)
            if catItem:
                catItem = catItem[0]
                entryItem = EntryItem(unicode(dialog.nameEdit.text()))
                expenseItem = ExpenseItem(str(dialog.expenseEdit.text()))
                dateItem = DateItem(unicode(dialog.dateCombo.currentText()))
                catItem.appendRow([entryItem, expenseItem, dateItem])
                model.setSumItem(expenseItem)
            
    def newYear(self):
        """
        Creates a new table with twelve empty MonthTabs. 
        Asks the user to give a year and if he wants to save the current year. 
        Kinda stupid. 
        """
        if self.__year is None:
            dialog = QtGui.QInputDialog(self)
            dialog.setWindowTitle('New Year')
            dialog.setLabelText('Enter a year: ')
            dialog.setInputMode(QtGui.QInputDialog.IntInput)
            from datetime import date 
            # necessary to set a dateList in a newEntryDialog
            dialog.setIntMinimum(date.min.year) # 1
            dialog.setIntMaximum(date.max.year) # 9999
            if dialog.exec_():
                self.monthsTabWidget.clear()
                for month in settings._MONTHS_:
                    self.monthsTabWidget.addTab(MonthTab(self, month), month)
                self.setYear(dialog.intValue(), 
                    settings._XMLFILE_ + str(self.__year) + '.xml')
        # override if another year has already been loaded?
        else:
            answer = QtGui.QMessageBox.information(
                    self, 'New Year', 'Do you want to open a new year?',
                    QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if answer == QtGui.QMessageBox.Yes:
                self.saveToXML()
                self.__year = None 
                self.newYear()
            return 

    def removeEntry(self):
        """ 
        Removes the selected entry from the model.
        Makes sure that item points to an ExpenseItem.
        Disables action_Remove_Entry if item at currentIndex does not suit.
        """
        index = self.__removeableIndex 
        model = index.model()
        item = model.itemFromIndex(index.parent().child(index.row(), 1))
        model.setSumItem(item, 2*item.value())
        model.removeRow(index.row(), index.parent())
        self.enableRemoveEntry(model.parent().currentIndex())
        
    def saveToXML(self):
        """ Saves all the month tabs to an XML file. """
        xmlWriter = QtCore.QXmlStreamWriter()
        xmlWriter.setAutoFormatting(True)
        xmlFile = QtCore.QFile(self.fileName)

        if xmlFile.open(QtCore.QIODevice.WriteOnly) == False:
            QtGui.QMessageBox.warning(self, 'Error', 'Error opening file!')
        else:
            xmlWriter.setDevice(xmlFile)
            xmlWriter.writeStartDocument()
            xmlWriter.writeStartElement('root')
            xmlWriter.writeAttribute('name', 'year')
            xmlWriter.writeAttribute('value', str(self.__year))
            xmlWriter.writeAttribute('autoSave', str(self.__autoSave))
            for i in range(self.monthsTabWidget.count()):
                widget = self.monthsTabWidget.widget(i)
                widget.writeToXML(xmlWriter, 'month', widget.month(), widget)
            xmlWriter.writeEndElement()
            xmlWriter.writeEndDocument()
    
    def setYear(self, year, fileName):
        """ 
        Helper function. 
        Wraps some layout and action adjustments when new year is set. 
        """
        self.__year = year 
        self.fileName = fileName 
        self.action_New_Entry.setEnabled(True)
        self.action_Statistics.setEnabled(True)
        self.setWindowTitle('Financeager - ' + str(self.__year))
        self.__statWindow = StatisticsWindow(self)
        # put the current month's tab to the front
        self.monthsTabWidget.setCurrentIndex(_CURRENTMONTH_)

    def showAbout(self):
        """ Information window about the author, credits, etc. """
        import os.path 
        pmpath = QtCore.QDir.currentPath() + \
                os.path.sep.join(['', 'src', 'resources', 'img', 'money.png'])
        messageBox = QtGui.QMessageBox(self)
        messageBox.setWindowTitle('About Financeager')
        messageBox.setText('Thank you for choosing Financeager.')
        messageBox.setInformativeText('Author: %s \nEmail: %s \nCredits: %s \n%s \n' % 
                (__author__, __email__, __credits__, __copyright__))
        messageBox.setIconPixmap(QtGui.QPixmap(pmpath))
        messageBox.exec_()

    def showSettings(self):
        """
        TODO comment this
        """
        dialog = SettingsDialog(self)
        dialog.autoSaveSet[bool].connect(self.setAutoSave)
        if dialog.exec_():
            dialog.applyChanges()

    def showStatistics(self, checked):
        """
        TODO
        """
        if self.__statWindow is not None:
            if checked:
                self.__statWindow.show()
            else:
                self.__statWindow.hide()

    def year(self):
        return self.__year 