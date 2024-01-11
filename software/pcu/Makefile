##############################################################################
# Build global options
# NOTE: Can be overridden externally.
#

# Compiler options here.
ifeq ($(USE_OPT),)
  USE_OPT = -O0 -ggdb -fomit-frame-pointer -falign-functions=16
endif

# C specific options here (added to USE_OPT).
ifeq ($(USE_COPT),)
  USE_COPT = 
endif

# C++ specific options here (added to USE_OPT).
ifeq ($(USE_CPPOPT),)
  USE_CPPOPT = -fno-rtti
endif

# Enable this if you want the linker to remove unused code and data.
ifeq ($(USE_LINK_GC),)
  USE_LINK_GC = yes
endif

# Linker extra options here.
ifeq ($(USE_LDOPT),)
  USE_LDOPT = 
endif

# Enable this if you want link time optimizations (LTO).
ifeq ($(USE_LTO),)
  USE_LTO = yes
endif

# Enable this if you want to see the full log while compiling.
ifeq ($(USE_VERBOSE_COMPILE),)
  USE_VERBOSE_COMPILE = no
endif

# If enabled, this option makes the build process faster by not compiling
# modules not used in the current configuration.
ifeq ($(USE_SMART_BUILD),)
  USE_SMART_BUILD = yes
endif

#
# Build global options
##############################################################################

##############################################################################
# Architecture or project specific options
#

# Stack size to be allocated to the Cortex-M process stack. This stack is
# the stack used by the main() thread.
ifeq ($(USE_PROCESS_STACKSIZE),)
  USE_PROCESS_STACKSIZE = 0x200
endif

# Stack size to the allocated to the Cortex-M main/exceptions stack. This
# stack is used for processing interrupts and exceptions.
ifeq ($(USE_EXCEPTIONS_STACKSIZE),)
  USE_EXCEPTIONS_STACKSIZE = 0x200
endif

# Enables the use of FPU (no, softfp, hard).
ifeq ($(USE_FPU),)
  USE_FPU = no
endif

# FPU-related options.
ifeq ($(USE_FPU_OPT),)
  USE_FPU_OPT = -mfloat-abi=$(USE_FPU) -mfpu=fpv4-sp-d16
endif

#
# Architecture or project specific options
##############################################################################

##############################################################################
# Project, target, sources and paths
#

# Define project name here
PROJECT = ch

# Target settings.
MCU  = cortex-m0

# Imported source files and paths.
CHIBIOS  := ./ChibiOS
CHIBIOS_CONTRIB := ./ChibiOS-Contrib
CONFDIR  := ./cfg
BUILDDIR := ./build
DEPDIR   := ./.dep

# Licensing files.
include $(CHIBIOS)/os/license/license.mk
# Startup files.
include $(CHIBIOS)/os/common/startup/ARMCMx/compilers/GCC/mk/startup_stm32f0xx.mk
# HAL-OSAL files (optional).
include $(CHIBIOS)/os/hal/hal.mk
include $(CHIBIOS)/os/hal/ports/STM32/STM32F0xx/platform.mk
# include $(CHIBIOS)/os/hal/boards/ST_NUCLEO64_F070RB/board.mk
include ./board/board.mk
include $(CHIBIOS)/os/hal/osal/rt-nil/osal.mk
# RTOS files (optional).
include $(CHIBIOS)/os/rt/rt.mk
include $(CHIBIOS)/os/common/ports/ARMv6-M/compilers/GCC/mk/port.mk
# Auto-build files in ./source recursively.
include $(CHIBIOS)/tools/mk/autobuild.mk
# Other files (optional).
include $(CHIBIOS)/os/test/test.mk
include $(CHIBIOS)/test/rt/rt_test.mk
include $(CHIBIOS)/test/oslib/oslib_test.mk
include $(CHIBIOS)/os/various/shell/shell.mk
include $(CHIBIOS)/os/hal/lib/streams/streams.mk
include $(CHIBIOS_CONTRIB)/os/hal/ports/STM32/LLD/USBHv1/driver.mk


# Define linker script file here
LDSCRIPT= $(STARTUPLD)/STM32F070xB.ld

# C sources that can be compiled in ARM or THUMB mode depending on the global
# setting.
CSRC = $(ALLCSRC) \
       $(TESTSRC) \
       bcuCommunication/bcuCommunication.c \
       bcuCommunication/usb.c \
       bcuCommunication/threads.c \
       alarmClock/alarmClock.c \
       measurement/measurement.c \
       docking/docking.c \
       power/power.c \
       statemachine/statemachine.c \
       hmi/display.c \
       hmi/hmi.c \
       tools/debug.c \
       version/pcu_version.c \
       main.c \

# C++ sources that can be compiled in ARM or THUMB mode depending on the global
# setting.
CPPSRC = $(ALLCPPSRC)

# List ASM source files here.
ASMSRC = $(ALLASMSRC)

# List ASM with preprocessor source files here.
ASMXSRC = $(ALLXASMSRC)

BASE_INCDIR = ./core_defines \
			  ./version \
			  ./bcuCommunication \
			  ./alarmClock \
			  ./measurement \
			  ./docking \
			  ./power \
			  ./statemachine \
			  ./tools \
			  ./hmi

# Inclusion directories.
INCDIR = $(CONFDIR) $(ALLINC) $(TESTINC) $(BASE_INCDIR)

# Define C warning options here.
CWARN = -Wall -Wextra -Wundef -Wstrict-prototypes

# Define C++ warning options here.
CPPWARN = -Wall -Wextra -Wundef

#
# Project, target, sources and paths
##############################################################################

##############################################################################
# Start of user section
#

# List all user C define here, like -D_DEBUG=1
UDEFS =

# Define ASM defines here
UADEFS =

# List all user directories here
UINCDIR =

# List the user directory to look for the libraries here
ULIBDIR =

# List all user libraries here
ULIBS =

#
# End of user section
##############################################################################

##############################################################################
# Common rules
#

RULESPATH = $(CHIBIOS)/os/common/startup/ARMCMx/compilers/GCC/mk
include $(RULESPATH)/arm-none-eabi.mk
include $(RULESPATH)/rules.mk

#
# Common rules
##############################################################################

##############################################################################
# Versioning rules
GIT_BRANCH_NAME := $(shell git rev-parse --abbrev-ref HEAD)
GIT_BRANCH_STATUS := $(shell if [ -z "$$(git status --porcelain )" ]; \
											then echo "clean";	else	echo "dirty"; fi )
GIT_LAST_COMMIT := $(shell git describe --contains --always)
GIT_LAST_COMMIT_DATE := $(firstword $(shell git --no-pager show --date=short \
												--format="%ad" --name-only))
BUILD_DATE := $(shell date '+%YY-%mM-%dD-%Hh:%Mm:%Ss' )

.PHONY: force
version/pcu_version.c: force
	@echo $(GIT_BRANCH_NAME) | awk ' BEGIN {print "/* This file is autogenerated */"} \
		{print "#include \"pcu_version.h\""} \
		{print "const char * pcu_build_git_branch_name = \"" $$0"\";"} \
		{print "const char * pcu_build_git_branch_status = \"$(GIT_BRANCH_STATUS)\";"} \
		{print "const char * pcu_build_git_last_commit = \"$(GIT_LAST_COMMIT)\";"} \
		{print "const char * pcu_build_git_commit_time = \"$(GIT_LAST_COMMIT_DATE)\";"} \
		{print "const char * pcu_build_date = \"$(BUILD_DATE)\";"} \
		END {}' > version/pcu_version.c

##############################################################################
