# Copyright 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Arduino

Arduino Wiring-based Framework allows writing cross-platform software to
control devices attached to a wide range of Arduino boards to create all
kinds of creative coding, interactive objects, spaces or physical experiences.

http://arduino.cc/en/Reference/HomePage
"""

from io import open
from os import listdir, environ
from os.path import isdir, isfile, join
from platformio.util import get_systype
from platformio.proc import exec_command
import re

from SCons.Script import DefaultEnvironment

import multiprocessing


def append_lto_options():
    if "windows" in get_systype():
        env.Append(
            CCFLAGS=["-flto", "-fipa-pta"],
            LINKFLAGS=["-flto"]
        )
    else:
        env.Append(
            CCFLAGS=["-flto", "-fipa-pta"],
            LINKFLAGS=["-flto=" + str(multiprocessing.cpu_count())]
        )

def get_size_output(source):
    cmd = env.get("SIZECHECKCMD")
    if not cmd:
        return None
    if not isinstance(cmd, list):
        cmd = cmd.split()
    cmd = [arg.replace("$SOURCES", str(source[0])) for arg in cmd if arg]
    sysenv = environ.copy()
    sysenv["PATH"] = str(env["ENV"]["PATH"])
    result = exec_command(env.subst(cmd), env=sysenv)
    if result["returncode"] != 0:
        return None
    return result["out"].strip()

def calculate_size(output, pattern):
    if not output or not pattern:
        return -1
    size = 0
    regexp = re.compile(pattern)
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = regexp.search(line)
        if not match:
            continue
        size += sum(int(value) for value in match.groups())
    return size

def format_availale_bytes(value, total):
    percent_raw = float(value) / float(total)
    blocks_per_progress = 10
    used_blocks = min(int(round(blocks_per_progress * percent_raw)), blocks_per_progress)
    return "[{:{}}] {: 6.1%} (used {:d} bytes from {:d} bytes)".format("=" * used_blocks, blocks_per_progress, percent_raw, value, total)

def print_size_teensy4(target, source, env):
    env.Replace(SIZECHECKCMD = env.get("SIZETOOL_SAVED") + " -A -d $SOURCES")

    program_max_size = int(env.BoardConfig().get("upload.maximum_size", 0))
    ram1_max_size = int(env.BoardConfig().get("upload.maximum_ram_size", 0))
    ram2_max_size = int(env.BoardConfig().get("upload.maximum_ram_size", 0))

    output = get_size_output(source)
    program_size = calculate_size(output, env.get("SIZEPROGREGEXP"))
    ram1_usage = calculate_size(output, env.get("SIZEDATAREGEXP"))
    ram2_usage = calculate_size(output, env.get("SIZERAM2REGEXP"))
    itcm = calculate_size(output, env.get("SIZEITCMREGEXP"))
    itcm_blocks = (itcm + 0x7FFF) >> 15
    itcm_total = itcm_blocks * 32768
    itcm_padding = itcm_total - itcm

    if ram1_max_size and ram1_usage > -1:
        print("RAM 1:  %s" % format_availale_bytes(ram1_usage + itcm_padding, ram1_max_size))
    if ram2_max_size and ram2_usage > -1:
        print("RAM 2:  %s" % format_availale_bytes(ram2_usage, ram2_max_size))
    if program_max_size and program_size > -1:
        print("Flash:  %s" % format_availale_bytes(program_size, program_max_size))
    if int(ARGUMENTS.get("PIOVERBOSE", 0)):
        print("ITCM P: %s" % format_availale_bytes(itcm_padding, 32767))
        print("")
        print(output)

env = DefaultEnvironment()
platform = env.PioPlatform()

FRAMEWORK_DIR = platform.get_package_dir("framework-arduinoteensy-ts")
FRAMEWORK_DIR_LIBS = platform.get_package_dir("framework-arduinoteensy")
FRAMEWORK_VERSION = platform.get_package_version("framework-arduinoteensy-ts")
BUILD_CORE = env.BoardConfig().get("build.core")

assert isdir(FRAMEWORK_DIR)

BUILTIN_USB_FLAGS = (
    "USB_SERIAL",
    "USB_DUAL_SERIAL",
    "USB_TRIPLE_SERIAL",
    "USB_KEYBOARDONLY",
    "USB_TOUCHSCREEN",
    "USB_HID_TOUCHSCREEN",
    "USB_HID",
    "USB_SERIAL_HID",
    "USB_MIDI",
    "USB_MIDI4",
    "USB_MIDI16",
    "USB_MIDI_SERIAL",
    "USB_MIDI4_SERIAL",
    "USB_MIDI16_SERIAL",
    "USB_AUDIO",
    "USB_MIDI_AUDIO_SERIAL",
    "USB_MIDI16_AUDIO_SERIAL",
    "USB_MTPDISK",
    "USB_RAWHID",
    "USB_FLIGHTSIM",
    "USB_FLIGHTSIM_JOYSTICK",
    "USB_EVERYTHING",
    "USB_DISABLED",
    "USB_MTPDISK_SERIAL"
)
if not set(env.get("CPPDEFINES", [])) & set(BUILTIN_USB_FLAGS):
    env.Append(CPPDEFINES=["USB_SERIAL"])

env.Replace(
    SIZEPROGREGEXP=r"^(?:\.text|\.text\.headers|\.text\.itcm|\.text\.code|\.text\.progmem|\.data|\.data\.func|\.ARM\.exidx|\.ARM\.extab|\.text\.csf)\s+([0-9]+).*",
    SIZEDATAREGEXP=r"^(?:\.usbdescriptortable|\.dmabuffers|\.usbbuffers|\.data|\.bss|\.noinit|\.text\.itcm|\.text\.itcm\.padding)\s+([0-9]+).*",
    SIZEITCMREGEXP=r"^(?:\.text\.itcm)\s+([0-9]+).*",
    SIZERAM2REGEXP=r"^(?:\.ARM\.exidx|\.ARM\.extab|\.bss\.dma)\s+([0-9]+).*"
)

env.Append(
    CPPDEFINES=[
        ("ARDUINO", 10819),
        ("TEENSYDUINO", int(FRAMEWORK_VERSION.split(".")[1])),
        "CORE_TEENSY"
    ],

    CPPPATH=[
        join(FRAMEWORK_DIR, ".", BUILD_CORE)
    ],

    LIBSOURCE_DIRS=[
        join(FRAMEWORK_DIR_LIBS, "libraries")
    ]
)

if "BOARD" in env and BUILD_CORE == "teensy":
    env.Append(
        ASFLAGS=[
            "-mmcu=$BOARD_MCU"
        ],
        ASPPFLAGS=[
            "-x", "assembler-with-cpp",
        ],

        CCFLAGS=[
            "-Os",  # optimize for size
            "-Wall",  # show warnings
            "-ffunction-sections",  # place each function in its own section
            "-fdata-sections",
            "-mmcu=$BOARD_MCU"
        ],

        CXXFLAGS=[
            "-fno-exceptions",
            "-felide-constructors",
            "-std=gnu++11",
            "-fpermissive"
        ],

        CPPDEFINES=[
            ("F_CPU", "$BOARD_F_CPU"),
            "LAYOUT_US_ENGLISH"
        ],

        LINKFLAGS=[
            "-Os",
            "-Wl,--gc-sections,--relax",
            "-mmcu=$BOARD_MCU"
        ],

        LIBS=["m"]
    )
elif "BOARD" in env and BUILD_CORE in ("teensy3", "teensy4"):
    env.Append(
        ASFLAGS=[
            "-mthumb",
            "-mcpu=%s" % env.BoardConfig().get("build.cpu"),
        ],

        ASPPFLAGS=[
            "-x", "assembler-with-cpp",
        ],

        CFLAGS=[
            "-Wno-old-style-declaration",
            "-std=gnu17"
        ],

        CCFLAGS=[
            "-Wall",  # show warnings
            "-Wextra",
            "-ffunction-sections",  # place each function in its own section
            "-fdata-sections",
            "-mthumb",
            "-mcpu=%s" % env.BoardConfig().get("build.cpu"),
            "-nostdlib",
            "--specs=nano.specs"
        ],

        CXXFLAGS=[
            "-fno-exceptions",
            "-fno-non-call-exceptions",
            "-fno-unwind-tables",
            "-fno-asynchronous-unwind-tables",
            "-felide-constructors",
            "-fno-rtti",
            "-std=gnu++20",
            "-Wno-error=narrowing",
            "-Wno-volatile",
            "-fpermissive"
        ],

        CPPDEFINES=[
            ("F_CPU", "$BOARD_F_CPU"),
            "LAYOUT_US_ENGLISH"
        ],

        RANLIBFLAGS=["-s"],

        LINKFLAGS=[
            "-ffunction-sections",
            "-fdata-sections",
            "-Wl,--gc-sections,--relax",
            "-nostartfiles",
            "-mthumb",
            "-mcpu=%s" % env.BoardConfig().get("build.cpu"),
            "--specs=nano.specs"
        ],

        LIBS=["m", "stdc++"]
    )
    
    if BUILD_CORE == "teensy4":
        env.Replace(
            SIZETOOL_SAVED = env.get("SIZETOOL"),
            SIZETOOL = None,
            SIZECHECKCMD = None,
            SIZEPRINTCMD = print_size_teensy4
        )

    if "SET_CURRENT_TIME" in env['CPPDEFINES']:
        env.Append(
            LINKFLAGS=["-Wl,--defsym=__rtc_localtime=$UNIX_TIME"]
        )
    else:
        env.Append(
            LINKFLAGS=["-Wl,--defsym=__rtc_localtime=0"]
        )
        
    if not "DISABLE_PRINTF_FLOAT" in env['CPPDEFINES']:
        env.Append(
            LINKFLAGS=["-Wl,-u,_printf_float"]
        )

    if not env.BoardConfig().get("build.ldscript", ""):
        env.Replace(LDSCRIPT_PATH=env.BoardConfig().get("build.arduino.ldscript", ""))

    if env.BoardConfig().id_ in (
        "teensy35",
        "teensy36",
        "teensy40",
        "teensy41",
        "teensymm",
    ):
        fpv_version = "4-sp"
        if env.BoardConfig().id_.startswith(("teensy4", "teensymm")):
            fpv_version = "5"

        env.Append(
            ASFLAGS=[
                "-mfloat-abi=hard",
                "-mfpu=fpv%s-d16" % fpv_version
            ],
            CCFLAGS=[
                "-mfloat-abi=hard",
                "-mfpu=fpv%s-d16" % fpv_version
            ],
            LINKFLAGS=[
                "-mfloat-abi=hard",
                "-mfpu=fpv%s-d16" % fpv_version
            ]
        )

    # Optimization
    if "TEENSY_OPT_FASTER_LTO" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-O2"],
            LINKFLAGS=["-O2"]
        )
        append_lto_options()
    elif "TEENSY_OPT_FAST" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-O1"],
            LINKFLAGS=["-O1"]
        )
    elif "TEENSY_OPT_FAST_LTO" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-O1"],
            LINKFLAGS=["-O1"]
        )
        append_lto_options()
    elif "TEENSY_OPT_FASTEST" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-O3"],
            LINKFLAGS=["-O3"]
        )
    elif "TEENSY_OPT_FASTEST_LTO" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-O3"],
            LINKFLAGS=["-O3"]
        )
        append_lto_options()
    elif "TEENSY_OPT_FASTEST_PURE_CODE" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-O3", "-mpure-code"],
            CPPDEFINES=["__PURE_CODE__"],
            LINKFLAGS=["-O3", "-mpure-code"]
        )
    elif "TEENSY_OPT_FASTEST_PURE_CODE_LTO" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-O3", "-mpure-code"],
            CPPDEFINES=["__PURE_CODE__"],
            LINKFLAGS=["-O3", "-mpure-code"]
        )
        append_lto_options()
    elif "TEENSY_OPT_DEBUG" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-g", "-Og"],
            LINKFLAGS=["-g", "-Og"]
        )
    elif "TEENSY_OPT_DEBUG_LTO" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-g", "-Og"],
            LINKFLAGS=["-g", "-Og"]
        )
        append_lto_options()
    elif "TEENSY_OPT_SMALLEST_CODE_LTO" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-Os"],
            LINKFLAGS=["-Os"]
        )
        append_lto_options()
    elif "TEENSY_OPT_FASTER" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-O2"],
            LINKFLAGS=["-O2"]
        )
    elif "TEENSY_OPT_SMALLEST_CODE" in env['CPPDEFINES']:
        env.Append(
            CCFLAGS=["-Os"],
            LINKFLAGS=["-Os"]
        )
    # default profiles
    else:
        # for Teensy LC => TEENSY_OPT_SMALLEST_CODE
        if env.BoardConfig().id_ == "teensylc":
            env.Append(
                CCFLAGS=["-Os", "--specs=nano.specs"],
                LINKFLAGS=["-Os", "--specs=nano.specs"]
            )
        # for others => TEENSY_OPT_FASTER
        else:
            env.Append(
                CCFLAGS=["-O2"],
                LINKFLAGS=["-O2"]
            )


cpu = env.BoardConfig().get("build.cpu", "")
if "cortex-m" in cpu:
    board = env.subst("$BOARD")
    math_lib = "arm_cortex%s_math"
    if board in ("teensy35", "teensy36"):
        math_lib = math_lib % "M4lf"
    elif board in ("teensy30", "teensy31"):
        math_lib = math_lib % "M4l"
    elif board.startswith(("teensy4", "teensymm")):
        math_lib = math_lib % "M7lfsp"
    else:
        math_lib = math_lib % "M0l"

    #env.Prepend(LIBS=[math_lib])

    if cpu.startswith(("cortex-m4", "cortex-m0")):
        env.Append(
            ASFLAGS=[
                "-mno-unaligned-access",
            ],
            CCFLAGS=[
                "-mno-unaligned-access",
                "-fsingle-precision-constant"
            ],
            LINKFLAGS=[
                "-fsingle-precision-constant"
            ]
        )

# Teensy 2.x Core
if BUILD_CORE == "teensy":
    env.Append(CPPPATH=[join(FRAMEWORK_DIR, ".")])

    # search relative includes in teensy directories
    core_dir = join(FRAMEWORK_DIR, ".", "teensy")
    for item in sorted(listdir(core_dir)):
        file_path = join(core_dir, item)
        if not isfile(file_path):
            continue
        content = None
        content_changed = False
        with open(file_path, encoding="latin-1") as fp:
            content = fp.read()
            if '#include "../' in content:
                content_changed = True
                content = content.replace('#include "../', '#include "')
        if not content_changed:
            continue
        with open(file_path, "w", encoding="latin-1") as fp:
            fp.write(content)
else:
    env.Prepend(LIBPATH=[join(FRAMEWORK_DIR, ".", BUILD_CORE)])

#
# Target: Build Core Library
#

libs = []

if "build.variant" in env.BoardConfig():
    env.Append(
        CPPPATH=[
            join(FRAMEWORK_DIR, "variants",
                 env.BoardConfig().get("build.variant"))
        ]
    )
    libs.append(env.BuildLibrary(
        join("$BUILD_DIR", "FrameworkArduinoVariant"),
        join(FRAMEWORK_DIR, "variants", env.BoardConfig().get("build.variant"))
    ))

libs.append(env.BuildLibrary(
    join("$BUILD_DIR", "FrameworkArduino"),
    join(FRAMEWORK_DIR, ".", BUILD_CORE),
    src_filter="+<*> -<Blink.cc>"
))

env.Prepend(LIBS=libs)
