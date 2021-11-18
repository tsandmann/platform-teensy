# Teensy: development platform for [PlatformIO](http://platformio.org)

### Notice
This is a customized version of the [teensy platform config](https://github.com/platformio/platform-teensy) for PlatformIO that uses a more recent cross-compiler toolchain (gcc 11.x) supporting [Linux x86_64](https://github.com/tsandmann/arm-cortexm-toolchain-linux), [macOS x86_64](https://github.com/tsandmann/arm-cortexm-toolchain-mac), [macOS arm64](https://github.com/tsandmann/arm-cortexm-toolchain-macos-arm64) and [Windows x86_64](https://github.com/tsandmann/arm-cortexm-toolchain-win64) hosts.

## Introduction
Teensy is a complete USB-based microcontroller development system, in a very small footprint, capable of implementing many types of projects. All programming is done via the USB port. No special programmer is needed, only a standard USB cable and a PC or Macintosh with a USB port.

* [Home](http://platformio.org/platforms/teensy) (home page in PlatformIO Platform Registry)
* [Documentation](http://docs.platformio.org/page/platforms/teensy.html) (advanced usage, packages, boards, frameworks, etc.)

## Usage

1. [Install PlatformIO](http://platformio.org)
2. Create PlatformIO project and configure a platform option in [platformio.ini](http://docs.platformio.org/page/projectconf.html) file:

```ini
[env:teensy41]
platform = https://github.com/tsandmann/platform-teensy.git
board = ...
...
```

## Configuration

Please navigate to [documentation](http://docs.platformio.org/page/platforms/teensy.html).
