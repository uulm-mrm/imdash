cmake_minimum_required(VERSION 3.5.1)
project(imdash)

find_package(aduulm_cmake_tools REQUIRED)
aduulm_init_ros2_package()

if (AMENT_CMAKE_SYMLINK_INSTALL)
    install(DIRECTORY DESTINATION ${CMAKE_INSTALL_PREFIX}/${PYTHON_INSTALL_DIR})
    install(CODE "execute_process( \
      COMMAND ${CMAKE_COMMAND} -E create_symlink \
      ${PROJECT_SOURCE_DIR}/src/imdash \
      ${CMAKE_INSTALL_PREFIX}/${PYTHON_INSTALL_DIR}/imdash \
      )"
    )
else()
  aduulm_install_ros2_python_code(
    tplros2
    PACKAGE_DIR ${PROJECT_SOURCE_DIR}/src/imdash)
endif()

install(PROGRAMS scripts/imdash DESTINATION lib/${PROJECT_NAME})
install(PROGRAMS scripts/imdash DESTINATION bin/)

aduulm_create_ros2_package()
