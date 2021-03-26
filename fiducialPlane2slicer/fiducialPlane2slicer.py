import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import numpy as np
import vtkSlicerMarkupsModuleMRMLPython
import math

#
# fiducialPlane2slicer
#

class fiducialPlane2slicer(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "fiducialPlane2slicer"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["John Doe (AnyWare Corp.)"]  # TODO: replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
"""  # TODO: update with short description of the module
    self.parent.helpText += self.getDefaultModuleDocumentationLink()  # TODO: verify that the default URL is correct or change it to the actual documentation
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""  # TODO: replace with organization, grant and thanks.

#
# fiducialPlane2slicerWidget
#

class fiducialPlane2slicerWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self.slicesDict = {"Red Slice": "vtkMRMLSliceNodeRed", "Yellow Slice": "vtkMRMLSliceNodeYellow", "Green Slice": "vtkMRMLSliceNodeGreen"}

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/fiducialPlane2slicer.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    #points
    self.p1 = np.array([0.0, 0.0, 0.0])
    self.p2 = np.array([0.0, 0.0, 0.0])
    self.p3 = np.array([0.0, 0.0, 0.0])
    self.p4 = np.array([0.0, 0.0, 0.0])
    self.p5 = np.array([0.0, 0.0, 0.0])
    self.p6 = np.array([0.0, 0.0, 0.0])
    self.p7 = np.array([0.0, 0.0, 0.0])

    #normal vectors
    self.n1 = np.array([0.0, 0.0, 0.0])
    self.n2 = np.array([0.0, 0.0, 0.0])
    self.n3 = np.array([0.0, 0.0, 0.0])

    self.markupsNode = None
    self.fpoints = {}
    self.pointsComboBoxies = [self.ui.point1ComboBox, self.ui.point2ComboBox, self.ui.point3ComboBox, self.ui.point4ComboBox,
                         self.ui.point5ComboBox]
    for pcb in self.pointsComboBoxies:
      pcb.addItem("")
    self.sliceSelectorSetup()
    self.fiducials = []
    self.fiducialPoints = {}
    self.fiducialSelectorSetup()
    self.fillpointComboBoxies()

    # Connections
    self.sliceNameCollector = ["red", "yellow"]
    self.buttonPlane2Pushed = False
    self.ui.pushButtonPlane1.connect('clicked(bool)', self.onPushButtonPlane1)
    self.ui.pushButtonPlane2.connect('clicked(bool)', self.onPushButtonPlane2)
    self.ui.pushButtonPlane3.connect('clicked(bool)', self.onPushButtonPlane3)
    self.ui.point1ComboBox.connect('currentIndexChanged(QString)', self.onPoints123Changed)
    self.ui.point2ComboBox.connect('currentIndexChanged(QString)', self.onPoints123Changed)
    self.ui.point3ComboBox.connect('currentIndexChanged(QString)', self.onPoints123Changed)
    self.ui.point4ComboBox.connect('currentIndexChanged(QString)', self.onPoints123Changed)
    self.ui.point5ComboBox.connect('currentIndexChanged(QString)', self.onPoints123Changed)

    slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self.modifyfiducialSelector)
    slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeRemovedEvent, self.modifyfiducialSelector)


  def onMarkupPointPositionDefined(caller, event, p):
    markupsNode = caller
    movingMarkupIndex = markupsNode.GetDisplayNode().GetActiveControlPoint()
    logging.info(f"Markup point added: point ID = {movingMarkupIndex}")

  def onMarkupPointPositionUndefined(caller, event, p):
    markupsNode = caller
    logging.info(f"Markup point removed.")


  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()


  def onPushButtonPlane1(self):
    """
    Run processing when user clicks "Apply" button.
    """
    try:
      name = self.ui.sliceSelectorComboBox.currentText
      self.sliceNameCollector[0] = name
      # print("name: ", name)
      sliceNodeName = self.slicesDict[name]
      # print("sliceNode: ", sliceNodeName)
      sliceNode = slicer.mrmlScene.GetNodeByID(sliceNodeName)
      fvalues = list(self.fpoints.values())
      fkeys = list(self.fpoints.keys())

      box = self.pointsComboBoxies[0].currentText
      if not box:
        slicer.util.errorDisplay("Point 1 has not been set!")
        return 0
      index = fkeys[fvalues.index(box)]
      self.markupsNode.GetNthFiducialPosition(index, self.p1)

      box = self.pointsComboBoxies[1].currentText
      if not box:
        slicer.util.errorDisplay("Point 1 has not been set!")
        return 0
      index = fkeys[fvalues.index(box)]
      self.markupsNode.GetNthFiducialPosition(index, self.p2)

      box = self.pointsComboBoxies[2].currentText
      if not box:
        slicer.util.errorDisplay("Point 1 has not been set!")
        return 0
      index = fkeys[fvalues.index(box)]
      self.markupsNode.GetNthFiducialPosition(index, self.p3)

      dist = np.linalg.norm(self.p1 - self.p2)
      if np.isclose(dist, 0):
        slicer.util.errorDisplay("The Point1 and Point2 is too close to each other (Two point may be same)!")
        return 0
      dist = np.linalg.norm(self.p2 - self.p3)
      if np.isclose(dist, 0):
        slicer.util.errorDisplay("The Point2 and Point3 is too close to each other (Two point may be same)!")
        return 0

      # Get plane axis directions
      self.n1 = np.cross(self.p2 - self.p1, self.p2 - self.p3)  # plane normal direction
      print("Plane1 equation: {n0}(x - {x}) + {n1}(y - {y}) + {n2}(z - {z}) = 0".format(n0=self.n1[0], n1=self.n1[1], n2=self.n1[2], x=self.p2[0], y=self.p2[1], z=self.p2[2]))
      self.n1 = self.n1 / np.linalg.norm(self.n1)
      print("normal vector of plane1: ", self.n1)
      t = np.cross([0, 1, 0], self.n1)  # plane transverse direction
      t = t / np.linalg.norm(t)
      # Set slice plane orientation and position
      sliceNode.SetSliceToRASByNTP(self.n1[0], self.n1[1], self.n1[2], t[0], t[1], t[2], self.p1[0], self.p1[1], self.p1[2], 0)
      self.ui.pushButtonPlane2.enabled = True
      self.buttonPlane2Pushed = True
    except Exception as e:
      slicer.util.errorDisplay("Please set 3 fiducal on object!")
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()



  def onPushButtonPlane2(self):
    """
    Run processing when user clicks "Apply" button.
    """
    try:
      name = self.ui.sliceSelector2ComboBox.currentText
      sliceNodeName = self.slicesDict[name]
      self.sliceNameCollector[1] = name
      sliceNode = slicer.mrmlScene.GetNodeByID(sliceNodeName)

      fvalues = list(self.fpoints.values())
      fkeys = list(self.fpoints.keys())
      box = self.pointsComboBoxies[3].currentText
      if not box:
        slicer.util.errorDisplay("Point 1 has not been set!")
        return 0
      index = fkeys[fvalues.index(box)]
      self.markupsNode.GetNthFiducialPosition(index, self.p4)

      box = self.pointsComboBoxies[4].currentText
      if not box:
        slicer.util.errorDisplay("Point 1 has not been set!")
        return 0
      index = fkeys[fvalues.index(box)]
      self.markupsNode.GetNthFiducialPosition(index, self.p5)

      dist = np.linalg.norm(self.p4 - self.p5)
      if np.isclose(dist, 0):
        slicer.util.errorDisplay("The Point4 and Point5 is too close to each other (Two point may be same)!")
        return 0

      #Calculate p5 projection on plane
      v = self.p5 - self.p2
      d = np.dot(v, self.n1)
      print("The distance of the fifth point from the plane: ", d)
      if np.isclose(d, 0):
        slicer.util.errorDisplay("The fifth point is too close to plane (The point may be on the plane)!")
        return 0

      #Calculate p4 projection on plane
      v = self.p4 - self.p2
      d = np.dot(v, self.n1)
      print("The distance of the fourth point from the plane: ", d)
      if np.isclose(d, 0):
        slicer.util.errorDisplay("The fourth point is too close to plane (The point may be on the plane)!")
        return 0
      self.p6 = self.p4 - d*self.n1
      self.n2 = np.cross(self.p4 - self.p5, self.p4 - self.p6)  # plane normal direction
      print("Plane2 equation: {n0}(x - {x}) + {n1}(y - {y}) + {n2}(z - {z}) = 0".format(n0=self.n2[0], n1=self.n2[1], n2=self.n2[2], x=self.p4[0], y=self.p4[1], z=self.p4[2]))
      self.n2 = self.n2 / np.linalg.norm(self.n2)
      print("normal vector of plane2: ", self.n2)
      t2 = np.cross(-self.n1, self.n2)  # plane transverse direction
      t2 = t2 / np.linalg.norm(t2)
      # Set slice plane orientation and position
      sliceNode.SetSliceToRASByNTP(self.n2[0], self.n2[1], self.n2[2], t2[0], t2[1], t2[2], self.p1[0], self.p1[1], self.p1[2], 0)
      self.ui.pushButtonPlane3.enabled = True
    except Exception as e:
      slicer.util.errorDisplay("Please set 4 fiducal on object!")
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()


  def onPushButtonPlane3(self):
    """
    Run processing when user clicks "Apply" button.
    """
    try:
      for i in self.slicesDict.keys():
        if i not in self.sliceNameCollector:
          sliceNodeName = self.slicesDict[i]
          break

      sliceNode = slicer.mrmlScene.GetNodeByID(sliceNodeName)

      self.p7 = 10 * self.n1 + self.p6
      self.p8 = 10 * self.n2 + self.p6
      self.n3 = np.cross(self.p6 - self.p7, self.p6 - self.p8)  # plane normal direction
      print("Plane3 equation: {n0}(x - {x}) + {n1}(y - {y}) + {n2}(z - {z}) = 0".format(n0=self.n3[0], n1=self.n3[1], n2=self.n3[2], x=self.p5[0], y=self.p5[1], z=self.p5[2]))
      self.n3 = self.n3 / np.linalg.norm(self.n3)
      print("normal vector of plane3: ", self.n3)
      t3 = np.cross(-self.n1, self.n3)  # plane transverse direction
      t3 = t3 / np.linalg.norm(t3)
      # Set slice plane orientation and position
      sliceNode.SetSliceToRASByNTP(self.n3[0], self.n3[1], self.n3[2], t3[0], t3[1], t3[2], self.p6[0], self.p6[1], self.p6[2], 0)

    except Exception as e:
      slicer.util.errorDisplay("Please set 3 fiducal on object!")
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()


  def sliceSelectorSetup(self):
    keys = ["Red Slice", "Yellow Slice", "Green Slice"]
    # print(keys)
    for key in self.slicesDict.keys():
      self.ui.sliceSelectorComboBox.addItem(key)
      self.ui.sliceSelector2ComboBox.addItem(key)
    self.ui.sliceSelectorComboBox.setCurrentText(keys[0])
    self.ui.sliceSelector2ComboBox.setCurrentText(keys[1])


  def fiducialSelectorSetup(self):
    for node in list(slicer.mrmlScene.GetNodes()):
      if isinstance(node, vtkSlicerMarkupsModuleMRMLPython.vtkMRMLMarkupsFiducialNode):
        name = node.GetName()
        if name not in self.fiducials:
          self.ui.fiducialSelectorComboBox.addItem(name)
          self.fiducials.append(name)
    self.pushButtonPlaneActivator()
    self.setMarkupsNode()


  def fillpointComboBoxies(self):
    values = list(self.fpoints.values())
    # print("values:", values)
    n = min(len(values),5)
    for i in range(n):
      # print(values[i])
      self.pointsComboBoxies[i].setCurrentText(values[i])

  def modifyfiducialSelector(self, caller, event):
    fiducials = []
    for node in list(slicer.mrmlScene.GetNodes()):
      if isinstance(node, vtkSlicerMarkupsModuleMRMLPython.vtkMRMLMarkupsFiducialNode):
        name = node.GetName()
        fiducials.append(name)
    diff = list(set(fiducials) - set(self.fiducials))
    # print(diff)
    for fiducial in diff:
      self.ui.fiducialSelectorComboBox.addItem(fiducial)
      self.fiducials.append(fiducial)
    diff = list(set(self.fiducials) - set(fiducials))
    # print(diff)
    for fiducial in diff:
      index = self.ui.fiducialSelectorComboBox.findText(fiducial)
      self.ui.fiducialSelectorComboBox.removeItem(index)
      self.fiducials.remove(fiducial)
    self.pushButtonPlaneActivator()
    self.setMarkupsNode()


  def pushButtonPlaneActivator(self):
    if len(self.fiducials):
      self.ui.pushButtonPlane1.enabled = True
    else:
      self.ui.pushButtonPlane1.enabled = False
      self.ui.pushButtonPlane2.enabled = False
      self.ui.pushButtonPlane3.enabled = False


  def setMarkupsNode(self):
    fiducialname = self.ui.fiducialSelectorComboBox.currentText
    if fiducialname:
      self.markupsNode = slicer.util.getNode(fiducialname)
      self.markupsNode.AddObserver(self.markupsNode.PointPositionDefinedEvent, self.modifiedFiducialPoints)
      self.markupsNode.AddObserver(self.markupsNode.PointPositionUndefinedEvent, self.modifiedFiducialPoints)
      self.modifiedFiducialPoints()


  def modifiedFiducialPoints(self, caller=None, event=None):
    if self.markupsNode:
      n = self.markupsNode.GetNumberOfMarkups()
      fpoints = {}
      # print(n)
      for i in range(n):
        label = self.markupsNode.GetNthControlPointLabel(i)
        fpoints[i] = self.markupsNode.GetNthControlPointLabel(i)

      values = list(fpoints.values())
      svalues = list(self.fpoints.values())
      diff = list(set(svalues) - set(values))
      # print(diff)

      for value in diff:
        for i in range(len(self.pointsComboBoxies)):
          current = self.pointsComboBoxies[i].currentText
          index = self.pointsComboBoxies[i].findText(value)
          self.pointsComboBoxies[i].removeItem(index)
          if current == value:
            self.pointsComboBoxies[i].setCurrentText('')
            if i < 3:
              self.ui.pushButtonPlane1.enabled = False
              self.ui.pushButtonPlane2.enabled = False
              self.ui.pushButtonPlane3.enabled = False
            elif i < 5:
              self.ui.pushButtonPlane2.enabled = False
              self.ui.pushButtonPlane3.enabled = False
        self.fpoints.pop(list(self.fpoints.keys())[list(self.fpoints.values()).index(value)])
      diff = list(set(values) - set(svalues))
      # print(diff)
      for value in diff:
        for pcb in self.pointsComboBoxies:
          pcb.addItem(value)
      self.fpoints = fpoints

  def onPoints123Changed(self):
    if self.pointsComboBoxies[0].currentText and self.pointsComboBoxies[1].currentText and self.pointsComboBoxies[2].currentText:
      self.ui.pushButtonPlane1.enabled = True
      if self.pointsComboBoxies[3].currentText and self.pointsComboBoxies[4].currentText and self.buttonPlane2Pushed:
        self.ui.pushButtonPlane2.enabled = True
      else:
        self.ui.pushButtonPlane2.enabled = False
    else:
      self.ui.pushButtonPlane1.enabled = False
      self.ui.pushButtonPlane2.enabled = False
      self.buttonPlane2Pushed = False


# fiducialPlane2slicerLogic
#
class fiducialPlane2slicerLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "50.0")
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")

  def run(self, inputVolume, outputVolume, imageThreshold, invert=False, showResult=True):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param inputVolume: volume to be thresholded
    :param outputVolume: thresholding result
    :param imageThreshold: values above/below this threshold will be set to 0
    :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
    :param showResult: show output volume in slice viewers
    """

    if not inputVolume or not outputVolume:
      raise ValueError("Input or output volume is invalid")

    logging.info('Processing started')

    # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
    cliParams = {
      'InputVolume': inputVolume.GetID(),
      'OutputVolume': outputVolume.GetID(),
      'ThresholdValue' : imageThreshold,
      'ThresholdType' : 'Above' if invert else 'Below'
      }
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)

    logging.info('Processing completed')

#
# fiducialPlane2slicerTest
#

class fiducialPlane2slicerTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_fiducialPlane2slicer1()

  def test_fiducialPlane2slicer1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    inputVolume = SampleData.downloadFromURL(
      nodeNames='MRHead',
      fileNames='MR-Head.nrrd',
      uris='https://github.com/Slicer/SlicerTestingData/releases/download/MD5/39b01631b7b38232a220007230624c8e',
      checksums='MD5:39b01631b7b38232a220007230624c8e')[0]
    self.delayDisplay('Finished with download and loading')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 279)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 50

    # Test the module logic

    logic = fiducialPlane2slicerLogic()

    # Test algorithm with non-inverted threshold
    logic.run(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.run(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
