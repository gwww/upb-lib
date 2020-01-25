"""
Constants used across package
"""

from enum import Enum

PIM_ID = 0xFF


class UpbCommand(Enum):
    """UPB commands and responses"""

    ACTIVATE = 0x20
    DEACTIVATE = 0x21
    GOTO = 0x22
    REPORT_STATE = 0x30
    DEVICE_STATE_REPORT = 0x86
    REGISTER_VALUES_REPORT = 0x90


class PimCommand(Enum):
    """Lead character when sending to PIM"""

    TX_UPB_MSG = "\x14"
    READ_PIM_REGISTERS = "\x12"
    WRITE_PIM_REGISTERS = "\x17"


# UPB Product list from export document
# Note: some of the manufacturer numbers are not known
# Note: some products may be missing, this is the only list around
PRODUCTS = {
    "1/1": ("(WS1) Wall Switch - 1 Channel", "Switch"),
    "1/2": ("(WS1R) Wall switch Ð Relay", "Switch"),
    "1/3": ("(WMC6) Wall Mount Controller - 6 Button", "Keypad"),
    "1/4": ("(WMC8) Wall Mount Controller - 8 Button", "Keypad"),
    "1/6": ("(OCM2) Output Control Module - 2 Channel", "Module"),
    "1/7": ("(LCM1) Load Control Module 1", "Module"),
    "1/9": ("(LM1) Lamp Module - 1 Channel", "Module"),
    "1/10": ("(LM2) Lamp Module Ð 2 Channel", "Module"),
    "1/11": ("(ICM2) Input Control Module - 2 Channel", "Input"),
    "1/13": ("(DTC6) Desktop Controller - 6 Button", "Keypad"),
    "1/14": ("(DTC8) Desktop Controller - 8 Button", "Keypad"),
    "1/15": ("(AM1) Appliance Module - 1 Channel", "Module"),
    "1/25": ("(LSM) Load Shedding Module", "Module"),
    "1/24": ("(WS1E) Wall Switch - Electronic Low Voltage", "Switch"),
    "1/36": ("(DCM) Doorbell Control Module", "Input"),
    "1/37": ("(TCM) Telephone Control Module", "Input"),
    "1/58": ("(RM1) Receptacle Module", "Module"),
    "1/60": ("(FMD2) Fixture Module Ð Dimmer", "Module"),
    "1/61": ("(FMR) Fixture Module - Relay", "Module"),
    "1/62": ("(WS2D) LED Wall Switch", "Switch"),
    "1/63": ("(KPLD6) Keypad Light Dimmer", "Keypad"),
    "1/65": ("(KPC6) Controller Ð 6 Button", "Keypad"),
    "1/66": ("(KPC8) Controller Ð 8 Button", "Keypad"),
    "1/69": ("(KPLD8) Keypad Load Dimmer Ð 8 Button", "Keypad"),
    "1/70": ("(KPLR6) Keypad Load Relay Ð 6 Button", "Keypad"),
    "1/71": ("(KPLR8) Keypad Load Relay Ð 8 Button", "Keypad"),
    "1/72": ("(WS1L) Wall Switch Ð LED", "CFL Dimmer"),
    "1/73": ("(KPC7) Controller Ð 7 Button", "Keypad"),
    "1/74": ("(KPLR7) Keypad Load Relay Ð 7 Button", "Keypad"),
    "1/75": ("(KPLD7) Keypad Load Dimmer Ð 7 Button", "Keypad"),
    "HAI/1": ("35A00-1 600W Dimming Switch", "Switch"),
    "HAI/2": ("35A00-2 1000W Dimming Switch", "Switch"),
    "HAI/16": ("35A00-3 600W Non-Dimming Switch", "Switch"),
    "HAI/17": ("35A00-4 1000W Non-Dimming Switch", "Switch"),
    "HAI/18": ("40A00-1 15A Relay Switch", "Switch"),
    "HAI/3": ("55A00-1 1000W Dimming Switch", "Switch"),
    "HAI/4": ("55A00-2 1500W Dimming Switch", "Switch"),
    "HAI/5": ("55A00-3 2400W Dimming Switch", "Switch"),
    "HAI/32": ("59A00-1 300W Lamp Module", "Module"),
    "HAI/48": ("60A00-1 15A Appliance Module", "Module"),
    "HAI/80": ("38A00-1 6-Button Room Controller", "Keypad"),
    "HAI/96": ('38A00-2 8-Button House Controller"', "Keypad"),
    "4/1": ("UML Lamp Module", "Module"),
    "4/5": ("UMA Appliance Module", "Module"),
    "4/7": ("UFR Fixture Relay ", "URD Receptacle"),
    "4/9": ("UMA Appliance Module Ð Timer", "Module"),
    "4/10": ("UFD Fixture Dimmer", "Switch or Module *"),
    "4/12": ("UML Lamp Module Ð Timer", "Module"),
    "4/13": ("UFR Fixture ", "URD Receptacle Ð Timer"),
    "4/14": ("UFD Fixture Dimmer Ð Timer", "Switch or Module *"),
    "4/15": ("UCT Tabletop Controller", "Keypad"),
    "4/20": ("USM1 Switch Motorized", "Switch"),
    "4/22": ("US1 ", "US2 Series Dimming Switch"),
    "4/26": ("UCQ ", "UCQT Quad Output Module"),
    "4/27": ("US4 Series Quad Dimming Switch", "Switch"),
    "4/28": ("US1-40 Series Dimming Switch", "Switch"),
    "4/29": ("US2-40 Series Dimming Switch", "Switch"),
    "4/36": ("UCQTX Quad Output Module", "Module"),
    "4/62": ("US22-40T Series Dimming Switch", "Switch"),
    "4/34": ("US1-40 Series Dimming Switch Ð Timer", "Switch"),
    "4/44": ("USM1R", "Switch"),
    "4/45": ("USM2R", "Switch"),
    "4/40": ("UMI-32 3-Input ", "2-Output Module"),
    "WMT/88": ("CLSW-01 Classic series single dimmer wall switch", "Switch"),
    "WMT/89": ("CL6-01 Classic series wall mount 6 button", "Keypad controller"),
    "4/201": ("Lamp Module (UML-E)", "Module"),
    "4/205": ("Appliance Module (UMA-E)", "Module"),
    "4/222": ("Retail Dimming Switch (RS101)", "Switch"),
    "4/240": ("Retail I", "O 32 Module"),
    "MD/32": ("(VHC) Vacuum Handle Controller", "VHC"),
    "MD/33": ("(VPM) Vacuum Power Module", "VPM"),
    "MD/35": ("(VIM) Vacuum Input Module", "Input"),
    "MD/36": ("(DSM) Doorbell Sense Module", "Input"),
    "MD/37": ("(TSM) Telephone Sense Module", "Input"),
}
