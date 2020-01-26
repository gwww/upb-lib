# Python UPB Powerline Interface library

Library for interacting with UPB PIM/CIM

https://github.com/gwww/upb-lib

## Requirements

- Python 3.7 (or higher)

## Description

This package is created as a library to interact with an UPB PIM.
The motivation to write this was to use with the Home Assistant
automation platform. The library can be used for writing other UPB
applications. The IO with the PIM is asynchronous over TCP or over the
serial port.

## Installation

```bash
    $ pip install upb_lib
```

## Overview

Details TBD
  
Simplest thing right now is when in the root of the git repo that you have cloned is to enter the command `bin/simple`. You need the environment variable `UPBPIM_URL` set. Mine is set to `serial:///dev/cu.KeySerial1` on a MacBook. What is constant is `serial://` followed by the USB port that the PIM is on, which in my case is `/dev/cu.KeySerial1`. On Windows is might be something like `COM1`.

Also required is a `UPStart` export file. Mine is in the `bin` directory and named `upb.upe`. The `simple` program looks for it there.

This is all under very active development and will change. But if you really want to get up and running... Go for it!

## Development

This project uses [poetry](https://poetry.eustace.io/) for development dependencies. Installation instructions are on their website.

To get started developing:

```
git clone https://github.com/gwww/upb-lib.git
cd upb
poetry install
poetry shell # Or activate the created virtual environment
make test # to ensure everything installed properly
```

There is a `Makefile` in the root directory as well. The `make` command
followed by one of the targets in the `Makefile` can be used. If you don't
have or wish to use `make` the `Makefile` serves as examples of common
commands that can be run.
