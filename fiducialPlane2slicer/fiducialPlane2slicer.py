import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import numpy as np
import vtkSlicerMarkupsModuleMRMLPython

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

    self.sliceSelectorSetup()
    self.fiducialSelectorSetup()
    # Connections
    self.sliceNameCollector = ["red", "yellow"]

    self.ui.pushButtonPlane1.connect('clicked(bool)', self.onPushButtonPlane1)
    self.ui.pushButtonPlane2.connect('clicked(bool)', self.onPushButtonPlane2)
    self.ui.pushButtonPlane3.connect('clicked(bool)', self.onPushButtonPlane3)

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

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def setParameterNode(self, inputParameterNode):
    """
    Adds observers to the selected parameter node. Observation is needed because when the
    parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Set parameter node in the parameter node selector widget
    wasBlocked = self.ui.parameterNodeSelector.blockSignals(True)
    self.ui.parameterNodeSelector.setCurrentNode(inputParameterNode)
    self.ui.parameterNodeSelector.blockSignals(wasBlocked)

    if inputParameterNode == self._parameterNode:
      # No change
      return

    # Unobserve previusly selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    if inputParameterNode is not None:
      self.addObserver(inputParameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    # Disable all sections if no parameter node is selected
    self.ui.basicCollapsibleButton.enabled = self._parameterNode is not None
    self.ui.advancedCollapsibleButton.enabled = self._parameterNode is not None
    if self._parameterNode is None:
      return

    # Update each widget from parameter node
    # Need to temporarily block signals to prevent infinite recursion (MRML node update triggers
    # GUI update, which triggers MRML node update, which triggers GUI update, ...)

    wasBlocked = self.ui.inputSelector.blockSignals(True)
    self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
    self.ui.inputSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.outputSelector.blockSignals(True)
    self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))
    self.ui.outputSelector.blockSignals(wasBlocked)

    wasBlocked = self.invertedOutputSelector.blockSignals(True)
    self.invertedOutputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolumeInverse"))
    self.invertedOutputSelector.blockSignals(wasBlocked)

    wasBlocked = self.ui.imageThresholdSliderWidget.blockSignals(True)
    self.ui.imageThresholdSliderWidget.value = float(self._parameterNode.GetParameter("Threshold"))
    self.ui.imageThresholdSliderWidget.blockSignals(wasBlocked)

    wasBlocked = self.ui.invertOutputCheckBox.blockSignals(True)
    self.ui.invertOutputCheckBox.checked = (self._parameterNode.GetParameter("Invert") == "true")
    self.ui.invertOutputCheckBox.blockSignals(wasBlocked)

    # Update buttons states and tooltips
    if self._parameterNode.GetNodeReference("InputVolume") and self._parameterNode.GetNodeReference("OutputVolume"):
      self.ui.applyButton.toolTip = "Compute output volume"
      self.ui.applyButton.enabled = True
    else:
      self.ui.applyButton.toolTip = "Select input and output volume nodes"
      self.ui.applyButton.enabled = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None:
      return

    self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)
    self._parameterNode.SetParameter("Threshold", str(self.ui.imageThresholdSliderWidget.value))
    self._parameterNode.SetParameter("Invert", "true" if self.ui.invertOutputCheckBox.checked else "false")
    self._parameterNode.SetNodeReferenceID("OutputVolumeInverse", self.invertedOutputSelector.currentNodeID)

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
      fiducialname = self.ui.fiducialSelectorComboBox.currentText
      # markupsNode = slicer.mrmlScene.GetFirstNodeByName(fiducialname)
      # print(fiducialname)
      markupsNode = slicer.util.getNode(fiducialname)
      # print(markupsNode)
      # Get markup point positions as numpy arrays
      markupsNode.GetNthFiducialPosition(0, self.p1)
      markupsNode.GetNthFiducialPosition(1, self.p2)
      markupsNode.GetNthFiducialPosition(2, self.p3)
      # Get plane axis directions
      self.n1 = np.cross(self.p2 - self.p1, self.p2 - self.p3)  # plane normal direction
      print("Plane1 equation: ")
      print("{n0}(x - {x}) + {n1}(y - {y}) + {n2}(z - {z}) = 0".format(n0=self.n1[0], n1=self.n1[1], n2=self.n1[2], x=self.p2[0], y=self.p2[1], z=self.p2[2]))
      self.n1 = self.n1 / np.linalg.norm(self.n1)
      t = np.cross([0, 0, 1], self.n1)  # plane transverse direction
      t = t / np.linalg.norm(t)
      # Set slice plane orientation and position
      sliceNode.SetSliceToRASByNTP(self.n1[0], self.n1[1], self.n1[2], t[0], t[1], t[2], self.p1[0], self.p1[1], self.p1[2], 0)
      self.ui.pushButtonPlane2.enabled = True
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
      fiducialname = self.ui.fiducialSelectorComboBox.currentText
      markupsNode = slicer.util.getNode(fiducialname)
      markupsNode.GetNthFiducialPosition(3, self.p4)

      #Calculate p4 projection on plane
      v = self.p4 - self.p2
      d = np.dot(v, self.n1)
      self.p5 = self.p4 - d*self.n1
      self.n2 = np.cross(self.p4 - self.p1, self.p4 - self.p5)  # plane normal direction
      print("Plane2 equation: ")
      print("{n0}(x - {x}) + {n1}(y - {y}) + {n2}(z - {z}) = 0".format(n0=self.n2[0], n1=self.n2[1], n2=self.n2[2], x=self.p4[0], y=self.p4[1], z=self.p4[2]))
      self.n2 = self.n2 / np.linalg.norm(self.n2)
      print("normal vector: ", self.n2)
      t2 = np.cross(self.n1, self.n2)  # plane transverse direction
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

      self.p6 = 10 * self.n1 + self.p5
      self.p7 = 10 * self.n2 + self.p5
      self.n3 = np.cross(self.p5 - self.p6, self.p5 - self.p7)  # plane normal direction
      print("Plane3 equation: ")
      print("{n0}(x - {x}) + {n1}(y - {y}) + {n2}(z - {z}) = 0".format(n0=self.n3[0], n1=self.n3[1], n2=self.n3[2], x=self.p5[0], y=self.p5[1], z=self.p5[2]))
      self.n3 = self.n3 / np.linalg.norm(self.n3)
      print("normal vector: ", self.n3)
      t3 = np.cross(self.n1, self.n3)  # plane transverse direction
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
        self.ui.fiducialSelectorComboBox.addItem(node.GetName())



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
