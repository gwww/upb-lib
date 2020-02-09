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

Simplest thing right now is when in the root of the git repo that you have cloned is to enter the command `bin/simple`. This program requires that the environment variable `UPBPIM_URL` set to indicate how to connect to the PIM. For example, `serial:///dev/cu.KeySerial1` connects to the PIM on a serial port (`serial://`) `/dev/cu/KeySerial1`. On Windows something like `serial://COM1` might work.

Also required is a `UPStart` export file. The `bin/simple` program looks for it
in the same directory as where the program is (i.e.: `bin`) and assumes that it is named `upb.upe`.

## Configuration

Initialization of the library takes the following parameters:

`url`: This is the PIM to connect to. It is formatted as a URL. Two formats
are supported: `serial://<device>` where `<device>` is the serial/USB port on which the PIM is connected; `tcp://<IP or domain>[:<port]` where IP or domain is where the device is connected on the network (perhaps using `ser2tcp` or a PIM-U) and an optional `port` number with a default of 2101.
Note: no testing has been completed on the `tcp://` connection as of yet.

`UPStartExportFile`: the path of where to read the export file generated through File->Export on the UPStart utility. This is optional but recommended.

`flags`: A string that contains a set of comma separated flags. Each flag can take the form of <flag_name> or <flag_name>=<value>. Parse is simple with no escapes so values cannot contain commas or equals. Flags supported are:

- `unlimited_blink_rate`: By default the minimum value that can be pass to blink a light or link is 30 (which is about 1/2 a second). When this flag is specified the minimum is 1.
- `use_raw_rate`: By default the API takes the number of seconds as the rate in which to transition lights to their new level. The number of seconds is coverted to the closest rate value that UPB understands (see rate table below). For example, if a request is to transition a light to its new state in 8 seconds, the closest value that UPB supports is 10 seconds and that is the transition time that will be used. If the use raw rate flag is given on initializing this library then the rate value is assumed to be the UPB rate value. i.e.: not in seconds but is a value that UPB "understands".

## First use of the API

Read the code in `bin/simple`. That is the short use of the API around. Beyond that look at the file `lights.py` and `links.py`. Any method in those files that has a description that starts with `(Helper)` are generally UPB actions.

## Usage

Many of the UPB commands take a `rate`. The values of the rate is as follows (at least for Simply Automated devices):

```
0 = Snap
1 = 0.8 seconds
2 = 1.6 seconds
3 = 3.3 seconds
4 = 5.0 seconds
5 = 6.6 seconds
6 = 10 seconds
7 = 20 seconds
8 = 30 seconds
9 = 1 minute
10 = 2 minutes
11 = 5 minutes
12 = 10 minutes
13 = 15 minutes
14 = 30 minutes
15 = 1 hour
```

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
