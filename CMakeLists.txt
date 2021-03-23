cmake_minimum_required(VERSION 3.13.4)

project(fiducialPlane2slice)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/fiducialPlane2slice")
set(EXTENSION_CATEGORY "Visualization")
set(EXTENSION_CONTRIBUTORS "Adam Csoka (Medicopus Nonprofit Ltd.)")
set(EXTENSION_DESCRIPTION "Module for auto cropping Volume")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/fiducialPlane2slice.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/fiducialPlane2slice/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(fiducialPlane2sliceVolume)
add_subdirectory(fiducialPlane2slicer)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
