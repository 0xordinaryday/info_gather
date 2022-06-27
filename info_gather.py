# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BasicInfoGatherer
                                 A QGIS plugin
 Gathers basic information about sites
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-06-27
        git sha              : $Format:%H$
        copyright            : (C) 2022 by David Gibbons
        email                : david@gibbons.digital
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QTextBrowser
from qgis.core import QgsProject

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .info_gather_dialog import BasicInfoGathererDialog

import sys
import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProject,
                       QgsRasterBandStats,
                       QgsDistanceArea,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       QgsPointXY,
                       QgsProcessingParameterFeatureSink)
from pathlib import Path
from qgis.utils import iface
import processing
import re
import math
import requests
from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

# def resolve_file(name, basepath=None):
#     if not basepath:
#       basepath = os.path.dirname(os.path.realpath(__file__))
#     return os.path.join(basepath)
# 
# filep = resolve_file('address_parser.py')
# sys.path.append(filep)
# import address_parser



class BasicInfoGatherer:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'BasicInfoGatherer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&BasicInfoGatherer')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('BasicInfoGatherer', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/info_gather/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Run Report'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&BasicInfoGatherer'),
                action)
            self.iface.removeToolBarIcon(action)
            
            
    def makeDir(self):
        path = 'C:/Temp/qgis_processing/'
        if not os.path.exists(path):
            os.makedirs(path)
        [f.unlink() for f in Path(path).glob("*") if f.is_file()]
        return None
        
        
    def burnExistingLayers(self):
        namesToBurn = ['slope', 'aspect', 'buffered']
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() in namesToBurn:
                QgsProject.instance().removeMapLayers([layer.id()]) 
        
        
    def getCompassDirection(self, azimuth_result):
        if azimuth_result > 348.75 or azimuth_result <= 11.25 : direction = 'north'
        elif azimuth_result > 11.25 and azimuth_result <= 33.75 : direction = 'north-northeast'
        elif azimuth_result > 33.75 and azimuth_result <= 56.25 : direction = 'northeast'
        elif azimuth_result > 56.25 and azimuth_result <= 78.75 : direction = 'east-northeast'
        elif azimuth_result > 78.75 and azimuth_result <= 101.25 : direction = 'east'
        elif azimuth_result > 101.25 and azimuth_result <= 123.75 : direction = 'east-southeast'
        elif azimuth_result > 123.75 and azimuth_result <= 146.25 : direction = 'southeast'
        elif azimuth_result > 146.25 and azimuth_result <= 168.75 : direction = 'south-southeast'
        elif azimuth_result > 168.75 and azimuth_result <= 191.25 : direction = 'south'
        elif azimuth_result > 191.25 and azimuth_result <= 213.75 : direction = 'south-southwest'
        elif azimuth_result > 213.75 and azimuth_result <= 236.25 : direction = 'southwest'
        elif azimuth_result > 236.25 and azimuth_result <= 258.75 : direction = 'west-southwest'
        elif azimuth_result > 258.75 and azimuth_result <= 281.25 : direction = 'west'
        elif azimuth_result > 281.25 and azimuth_result <= 303.75 : direction = 'west-northwest'
        elif azimuth_result > 303.75 and azimuth_result <= 326.25 : direction = 'northwest'
        else : direction = 'north-northwest'
        return(direction) 
        
            
    def runReport(self):
        """runs report"""
        self.burnExistingLayers()
        self.makeDir()
        self.dlg.textBrowser.setText('')
        
        # use the selected layer, not a hard-coded one
        layer = QgsProject.instance().mapLayersByName(self.dlg.layerSelector.currentText())[0]
        
        # layerName = 'cut_bnd'
        outFn = r'C:/Temp/qgis_processing/buffered.gpkg'
        bufferDist = 5
        # layers = QgsProject.instance().mapLayersByName(layerName)
        # layer = layers[0]
        processing.runAndLoadResults('qgis:buffer', {'INPUT': layer, 'DISTANCE': bufferDist, 'OUTPUT': outFn})  # layer
        
        # cut and warp in one step - note the funky paths!
        os.system('gdalwarp -t_srs EPSG:28355 -of GTiff -cutline C:/Temp/qgis_processing/buffered.gpkg -cl buffered -crop_to_cutline C:\\Temp\\LIDAR\\2m_statewide\\statewide.vrt C:/Temp/qgis_processing/warped.tif')
        
        # calculate aspect grid
        os.system('gdaldem aspect C:/temp/qgis_processing/warped.tif C:/temp/qgis_processing/aspect.tif -of GTiff -b 1')
        # run stats on aspect
        rlayer = iface.addRasterLayer('C:/temp/qgis_processing/aspect.tif', 'aspect')
        aspect_stats = rlayer.dataProvider().bandStatistics(1, QgsRasterBandStats.All)
        # run slope calculation
        os.system('gdaldem slope C:/Temp/qgis_processing/warped.tif C:/Temp/qgis_processing/slope.tif -of GTiff -b 1 -s 1.0')
        # recall layer 
        slope_layer = iface.addRasterLayer('C:/temp/qgis_processing/slope.tif', 'slope')
        slope_stats = slope_layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All)
        Slope_output_string = 'The site has a fall of ' + str(round(slope_stats.mean,1)) + '° towards the ' + self.getCompassDirection(aspect_stats.mean) + '\n'
                
        # get area of CUT_BND
        d = QgsDistanceArea()
        # note here layer was defined earler
        site_area = 0
        for feature in layer.getFeatures():
            geom = feature.geometry()
            site_area += d.measureArea(geom)
            # print("Perimeter (m):", d.measurePerimeter(geom))
        Area_output_string = 'The site has an area of ' + str(round(site_area)) + ' m2\n'
        
        # get map sheet from 1:25k, assumes view is centered
        xmin=iface.mapCanvas().extent().xMinimum()
        xmax=iface.mapCanvas().extent().xMaximum()
        ymin=iface.mapCanvas().extent().yMinimum()
        ymax=iface.mapCanvas().extent().yMaximum()
        bb1= str(xmin) + ","+str(ymin) + "," +str(xmax) + "," +str(ymax)
        
        # Prepare crs source and destination and instanciate a transform function
        sourceCrs = QgsCoordinateReferenceSystem(28355)
        destCrs = QgsCoordinateReferenceSystem(3857)
        tr = QgsCoordinateTransform(sourceCrs, destCrs, QgsProject.instance())
        LowerLeft = tr.transform(QgsPointXY(xmin,ymin))
        UpperRight = tr.transform(QgsPointXY(xmax,ymax))
        
        width=iface.mapCanvas().size().width()
        centreX=str(math.floor(width/2))
        width_string=str(width)
        height=iface.mapCanvas().size().height()
        centreY=str(math.floor(height/2))
        height_string=str(height)
        
        request_url = "https://www.mrt.tas.gov.au/web-services/wms?VERSION=1.1.0&REQUEST=GetFeatureInfo&QUERY_LAYERS=mrtwfs:Geology25kIndex&INFO_FORMAT=text/plain&FEATURE_COUNT=10&X=" + centreX + "&Y=" + centreY + "&LAYERS=mrtwfs:Geology25kIndex&STYLES=&SRS=EPSG:3857&BBOX=" + LowerLeft.toString().replace(' ', '') + ',' + UpperRight.toString().replace(' ', '') + "&WIDTH=" + width_string + "&HEIGHT=" + height_string + "&FORMAT=image/png&TRANSPARENT=true"
        result = requests.get(request_url).text
        
        # seriously, screw regex
        start=result.find("TITLE =") #Index where To starts
        end=result.find("DETAILS =") #Index of a new line
        Map_sheet_name = expected_string=result[start+8:end].strip()
        Map_sheet_string = "The Mineral Resources Tasmania Digital Geology Series 1:25,000 " + Map_sheet_name + " sheet shows that the surface geology of the site is mapped as...\n"
        
        self.dlg.textBrowser.setText(Slope_output_string + Area_output_string + Map_sheet_string)
        


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = BasicInfoGathererDialog()
            self.dlg.runButton.clicked.connect(self.runReport)
            
            
        # Fetch the currently loaded layers
        layers = QgsProject.instance().layerTreeRoot().children()
        # Clear the contents of the comboBox from previous runs
        self.dlg.layerSelector.clear()
        # Populate the layerSelector comboBox with names of all the loaded layers
        self.dlg.layerSelector.addItems([layer.name() for layer in layers])

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass



    
