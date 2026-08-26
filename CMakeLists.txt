cmake_minimum_required(VERSION 4.0)
project(overlay-reader)
set(CMAKE_CXX_STANDARD 14)

set(CMAKE_AUTOMOC ON)
set(CMAKE_INCLUDE_CURRENT_DIR ON)

include(FindPkgConfig)
include(GNUInstallDirs)

pkg_check_modules(ZIP REQUIRED libzip)
find_package(Boost COMPONENTS filesystem REQUIRED)

SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pthread -fPIC")
SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fPIC")

include_directories(
    src
    ${Boost_INCLUDE_DIRS}
)

add_subdirectory(src)
add_subdirectory(data)
