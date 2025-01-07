# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "Release")
  file(REMOVE_RECURSE
  "CMakeFiles\\DW_SDK_Qt_Example_autogen.dir\\AutogenUsed.txt"
  "CMakeFiles\\DW_SDK_Qt_Example_autogen.dir\\ParseCache.txt"
  "DW_SDK_Qt_Example_autogen"
  )
endif()
