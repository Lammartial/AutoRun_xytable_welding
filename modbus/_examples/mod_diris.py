"""
Modbus client module.
Socomec - DIRIS ModBus standard protocols.
--------------------------------------------------------------------------
"""

import time

#--------------------------------------------------------------------------------------------------
# other Package modules
#
from .mod_meter import ModbusMeter
from ..modbus_base import Endian, BinaryPayloadDecoder, ReadHoldingRegistersResponse

#--------------------------------------------------------------------------------------------------
class DirisMeter(ModbusMeter):
    """
    The paremeter for scaler is a list which has to match the number of channels that are read
    with this meter object.
    """
    def __init__(self, connection, unit_address=None, channel=0, scale_PI=1, scale_U=1):
        self.scale_PI = scale_PI
        self.scale_U = scale_U
        self.channel_count = 4
        assert (channel < self.channel_count)
        super().__init__(connection, unit_address=unit_address, channel=channel)

    def to_json(self):
        d = super().to_json()
        d.update({
            "scale_PI": self.scale_PI,
            "scale_U": self.scale_U
        })
        return d

    def getDecoder(self, registers): # setup the endianess for DIRIS meters
        return BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.Big, wordorder=Endian.Big)

    # common functions
    def readConstData(self, channel=None):
        # channel is unused
        return self.readProductId_Diris()

    def readAcPowerData(self, channel=None):
        d = self.readLoadMeasurement_Diris(channel=channel)
        if d["std"]["Status"] <= 0:
            return None
        # clean it up a bit
        del d["std"]["Channel"]
        return d["std"]

    def readAcEnergyData(self, channel=None):
        d = self.readEnergyMeter_Diris(channel=channel)
        if d["std"]["Status"] <= 0:
            return None
        # clean it up a bit
        del d["std"]["Channel"]
        return d["std"]

    def readDcPowerData(self, channel=None):
        log.warning(type(self).__qualname__ + "readDcPowerData Need implementation")
        return

    def readDcEnergyData(self, channel=None):
        log.warning(type(self).__qualname__ + "readDcEnergyData Need implementation")
        return

    def readTemperatureData(self, channel=None):
        log.warning(type(self).__qualname__ + "readTemperatureData Need implementation")
        return


    #----------------------------------------------------------------------------------------------
    #  DIRIS FAMILY METER
    #----------------------------------------------------------------------------------------------
    def readProductId_Diris(self):
        """
        DIRIS PRODUCT IDENTIFICATION
        """
        d = {}
        holdingRegs = self.readHoldingRegisters(0xc350, 66)
        decoder = self.getDecoder(holdingRegs)
        cc = "ascii"
        d["Timestamp"] = self.createTimestamp()
        # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
        #decoded = OrderedDict([('Timestamp', self.createTimestamp()), ...
        d["IdString"] =                    self.filterString(decoder.decode_string(8)) # string_16[4]
        d["ProdOrderId"] =                 decoder.decode_16bit_uint()          # U16
        d["ProductId"] =                   decoder.decode_16bit_uint()          # U16
        d["ModbusTableVersion"] =          decoder.decode_16bit_uint()          # U16
        d["ProductSoftwareVersion"] =      decoder.decode_16bit_uint()          # U16
        d["Serial_AA_SS"] =                decoder.decode_16bit_uint()          # U16_HEX
        d["Serial_SST_L"] =                decoder.decode_16bit_uint()          # U16_HEX
        d["Serial_Order"] =                decoder.decode_16bit_uint()          # U16
        d["Serial_Reserve"] =              decoder.decode_32bit_uint()          # U32
        d["CodeTable"] =                   decoder.decode_64bit_uint()          # U64_HEX
        d["CustomizationDataLoaded"] =     decoder.decode_16bit_uint()          # U8
        d["ProductVersionMajor"] =         decoder.decode_16bit_uint()          # U16
        d["ProductVersionMinor"] =         decoder.decode_16bit_uint()          # U16
        d["ProductVersionRevision"] =      decoder.decode_16bit_uint()          # U16
        d["ProductVersionBuild"] =         decoder.decode_16bit_uint()          # U16
        #d["ProductBuildDate"] =            binascii.hexlify(decoder.decode_string(6)).decode(cc) # DATETIME_3
        d["ProductBuildDate"] =            decoder.decode_16bit_uint() * 0x100000000 + \
                                           decoder.decode_16bit_uint() * 0x10000 + \
                                           decoder.decode_16bit_uint()          # DATETIME_3
        d["SoftwareTechBaseVerMajor"] =    decoder.decode_16bit_uint()          # U16
        d["SoftwareTechBaseVerMinor"] =    decoder.decode_16bit_uint()          # U16
        d["SoftwareTechBaseVerRevision"] = decoder.decode_16bit_uint()          # U16
        d["CustomVersionMajor"] =          decoder.decode_16bit_uint()          # U16
        d["CustomVersionMinor"] =          decoder.decode_16bit_uint()          # U16
        d["ProductVLO"] =                  self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["CustomVLO"] =                   self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["SoftwareTechBaseVLO"] =         self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["VendorName"] =                  self.filterString(decoder.decode_string(8*2))  # String[8*2]
        d["ProductName"] =                 self.filterString(decoder.decode_string(8*2))  # String[8*2]
        d["ExtendedName"] =                self.filterString(decoder.decode_string(8*2))  # String[8*2]
        #d["ResourceVersion"] =             decoder.decode_16bit_uint())           # U16

        # DECODER FUNCTIONS:
        # 'bits', decoder.decode_bits()),
        # '8int', decoder.decode_8bit_int()),
        # '8uint', decoder.decode_8bit_uint()),
        # '16int', decoder.decode_16bit_int()),
        # '16uint', decoder.decode_16bit_uint()),
        # '32int', decoder.decode_32bit_int()),
        # '32uint', decoder.decode_32bit_uint()),
        # '16float', decoder.decode_16bit_float()),
        # '16float2', decoder.decode_16bit_float()),
        # '32float', decoder.decode_32bit_float()),
        # '32float2', decoder.decode_32bit_float()),
        # '64int', decoder.decode_64bit_int()),
        # '64uint', decoder.decode_64bit_uint()),
        # 'ignore', decoder.skip_bytes(8)),
        # '64float', decoder.decode_64bit_float()),
        # '64float2', decoder.decode_64bit_float()),
        return d

    #----------------------------------------------------------------------------------------------
    def readLoadMeasurement_Diris(self, channel=None):
        """
        Reads the instant measurement data of a Load (1..4) depending on the base address (0x4800, 0x5000, 0x5800, 0x6000).
        channel=0..3 (Load 1..4) if None, the predefined channel is used.
        scale_xx= scalers for U and P and I measurements.
        Returns dataset d which is valid and filled, if d[Status]>0.
        """
        baseAddress = [0x4800, 0x5000, 0x5800, 0x6000]

        # setup dictionary for read
        obj = {
            "std": {},  # standard datensatz
            "soco": {}, # manufacturer specific data
        }
        d = obj["std"]

        if channel is None:
            channel = self.channel
        assert (channel < self.channel_count)
        d["Channel"] = channel

        _ba = baseAddress[channel]
        holdingRegs = self.readHoldingRegisters(_ba, 1)
        decoder = self.getDecoder(holdingRegs)
        status = decoder.decode_16bit_uint()
        d["Status"] = status # for channel
        time.sleep(0.025)
        if (status > 0):
            #d = _readLoadLine(d, d["socoData"], baseAddress[c], scalePI, scaleU)
            sPI = self.scale_PI
            sU = self.scale_U
            # skip status register as it was read in calling func already
            holdingRegs = self.readHoldingRegisters(_ba + 1, 91)
            decoder = self.getDecoder(holdingRegs)
            _n = obj["soco"]
            d["Timestamp"] = self.createTimestamp()
            _n["Timestamp"] = d["Timestamp"]
            # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
            _n["DateOfLastInstance"] = decoder.decode_32bit_uint() * 1e+0 # DATETIME s
            _n["IntegrationTime"] = decoder.decode_16bit_uint() * 1e+0    # U16      s/5
            d["U_LN"] = decoder.decode_32bit_uint() * sU * 1e-2           # U32      V/100
            d["U_LL"] = decoder.decode_32bit_uint() * sU * 1e-2           # U32      V/100
            d["I"] = decoder.decode_32bit_uint() * sPI * 1e-3             # U32      A/1000
            d["Frequency"] = decoder.decode_32bit_uint() * 1e-3           # U32      Hz/1000
            d["U_L1N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
            d["U_L2N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
            d["U_L3N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
            d["U_N"] = decoder.decode_32bit_uint() * sU * 1e-2            # U32      V/100
            d["U_L1L2"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
            d["U_L2L3"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
            d["U_L3L1"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
            d["I_L1"] = decoder.decode_32bit_uint() * sPI *  1e-3         # U32      A/1000
            d["I_L2"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
            d["I_L3"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
            d["I_N"] = decoder.decode_32bit_uint() * sPI * 1e-3           # U32      A/1000
            _n["Inba"] = decoder.decode_16bit_uint() * sPI * 1e-2         # U16      %/100
            _n["Idir"] = decoder.decode_32bit_uint() * sPI * 1e-3         # U32      A/1000
            _n["Iinv"] = decoder.decode_32bit_uint() * sPI * 1e-3         # U32      A/1000
            _n["Ihom"] = decoder.decode_32bit_uint() * sPI * 1e-3         # U32      A/1000
            _n["Inb"] = decoder.decode_16bit_uint() * sPI * 1e-2          # U16      %/100
            _n["Snom"] = decoder.decode_32bit_uint() * sPI * 1e+0         # VA
            d["P"] = decoder.decode_32bit_int() * sPI * 1e+0              # W
            d["Q"] = decoder.decode_32bit_int() * sPI * 1e+0              # var
            _n["Q_lagg"] = decoder.decode_32bit_int() * sPI * 1e+0        # var (+/induktiv)
            _n["Q_lead"] = decoder.decode_32bit_int() * sPI * 1e+0        # var (-/kapazitiv)
            d["S"] = decoder.decode_32bit_uint() * sPI * 1e+0             # VA
            d["PF"] = decoder.decode_16bit_int() * 1e-3                   # S16      -/1000 PowerFactor
            d["PF_Type"] =  decoder.decode_16bit_uint() * 1e+0            # U8       0=undefined,1=leading,2=lagging
            d["P_L1"] = decoder.decode_32bit_int() * sPI * 1e+0           # W
            d["P_L2"] = decoder.decode_32bit_int() * sPI * 1e+0           # W
            d["P_L3"] = decoder.decode_32bit_int() * sPI * 1e+0           # W
            d["Q_L1"] = decoder.decode_32bit_int() * sPI * 1e+0           # var
            d["Q_L2"] = decoder.decode_32bit_int() * sPI * 1e+0           # var
            d["Q_L3"] = decoder.decode_32bit_int() * sPI * 1e+0           # var
            _n["Q_L1_lagg"] = decoder.decode_32bit_int() * sPI * 1e+0     # var (+/induktiv)
            _n["Q_L2_lagg"] = decoder.decode_32bit_int() * sPI * 1e+0     # var (+/induktiv)
            _n["Q_L3_lagg"] = decoder.decode_32bit_int() * sPI * 1e+0     # var (+/induktiv)
            _n["Q_L1_lead"] = decoder.decode_32bit_int() * sPI * 1e+0     # var (-/kapazitiv)
            _n["Q_L2_lead"] = decoder.decode_32bit_int() * sPI * 1e+0     # var (-/kapazitiv)
            _n["Q_L3_lead"] = decoder.decode_32bit_int() * sPI * 1e+0     # var (-/kapazitiv)
            d["S_L1"] = decoder.decode_32bit_uint() * sPI * 1e+0          # VA
            d["S_L2"] = decoder.decode_32bit_uint() * sPI * 1e+0          # VA
            d["S_L3"] = decoder.decode_32bit_uint() * sPI * 1e+0          # VA
            d["PF_L1"] = decoder.decode_16bit_int() * 1e-3                # S16      -/1000 PowerFactor
            d["PF_L2"] = decoder.decode_16bit_int() * 1e-3                # S16      -/1000 PowerFactor
            d["PF_L3"] = decoder.decode_16bit_int() * 1e-3                # S16      -/1000 PowerFactor
            d["PF_L1_Type"] = decoder.decode_16bit_uint() * 1e+0          # U8       0=undefined,1=leading,2=lagging
            d["PF_L2_Type"] = decoder.decode_16bit_uint() * 1e+0          # U8       0=undefined,1=leading,2=lagging
            d["PF_L3_Type"] = decoder.decode_16bit_uint() * 1e+0          # U8       0=undefined,1=leading,2=lagging
        return obj

    #----------------------------------------------------------------------------------------------
    def readEnergyMeter_Diris(self, channel=None):
        """
        Reads the accumulated energy data of a Load (1..4) depending on the base address (0x4D80, 0x5580, 0x5D80, 0x6580).
        channel=0..3 (Load 1..4) if None, the predefined channel is used.
        scale_xx= scalers for E, P and I measurements.
        Returns dataset d which is valid and filled, if d[Status]>0.
        """
        baseAddress = [0x4D80, 0x5580, 0x5D80, 0x6580];
        # setup dictionary for read results
        obj = {
            "std" : {},  # standard datensatz
            "soco": {}, # manufacturer specific data
        }
        d = obj["std"]

        if channel is None:
            channel = self.channel
        assert (channel < self.channel_count)
        d["Channel"] = channel

        _ba = baseAddress[channel]
        holdingRegs = self.readHoldingRegisters(_ba, 1)
        decoder = self.getDecoder(holdingRegs)
        status = decoder.decode_16bit_uint()
        d["Status"] = status # for channel
        time.sleep(0.025)
        if (status > 0):
            sPI = self.scale_PI
            # skip status register as it was read in calling func already
            holdingRegs = self.readHoldingRegisters(_ba + 1, 65)
            decoder = self.getDecoder(holdingRegs)
            _n = obj["soco"]
            d["Timestamp"] = self.createTimestamp()
            _n["Timestamp"] = d["Timestamp"]
            # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
            d["HourMeter"] = decoder.decode_32bit_uint() * 1e+0                 # U32      s
            d["Ea_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3              # U32      (Ea+)  Wh / 0.001
            _n["rEa_pos"] = decoder.decode_16bit_uint() * sPI * 1e-1            # U16      (rEa+) Wh / 10
            d["Ea_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3              # U32      (Ea-)  Wh / 0.001
            _n["rEa_neg"] = decoder.decode_16bit_uint() * sPI * 1e-1            # U16      (rEa-) Wh / 10
            d["Er_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3              # U32      (Er+)  varh / 0.001
            _n["rEr_pos"] = decoder.decode_16bit_uint() * sPI * 1e-1            # U16      (rEr+) varh / 10
            d["Er_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3              # U32      (Er-)  varh / 0.001
            _n["rEr_neg"] = decoder.decode_16bit_uint() * sPI * 1e-1            # U16      (rEr-) varh / 10
            d["Eap"] = decoder.decode_32bit_uint() * sPI * 1e+3                 # U32      (Eap) VAh / 0.001  Apparent Energy
            _n["rEap"] = decoder.decode_16bit_uint() * sPI * 1e-1               # U16      (rEap) VAh / 10    Residual Apparent Energy
            _n["Er_pos_lagg"] = decoder.decode_32bit_uint() * sPI * 1e+3        # U32      (Er+ lagg)  varh / 0.001
            _n["rEr_pos_lagg"] = decoder.decode_16bit_uint() * sPI * 1e-1       # U16      (rEr+ lagg) varh / 10
            _n["Er_neg_lagg"] = decoder.decode_32bit_uint() * sPI * 1e+3        # U32      (Er- lagg)  varh / 0.001
            _n["rER_neg_lagg"] = decoder.decode_16bit_uint() * sPI * 1e-1       # U16      (rEr- lagg) varh / 10
            _n["Er_pos_lead"] = decoder.decode_32bit_uint() * sPI * 1e+3        # U32      (Er+ lead)  varh / 0.001
            _n["rEr_pos_lead"] = decoder.decode_16bit_uint() * sPI * 1e-1       # U16      (rEr+ lead) varh / 10
            _n["Er_neg_lead"] = decoder.decode_32bit_uint() * sPI * 1e+3        # U32      (Er- lead)  varh / 0.001
            _n["rEr_neg_lead"] = decoder.decode_16bit_uint() * sPI * 1e-1       # U16      (rEr- lead) varh / 10
            _n["Partial_HourMeter"] = decoder.decode_32bit_uint() * 1e+0,       # U32      s
            _n["Partial_Ea_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3     # U32      (Ea+)  Wh / 0.001
            _n["Partial_rEa_pos"] = decoder.decode_16bit_uint() * sPI * 1e-1    # U16      (rEa+) Wh / 10
            _n["Partial_Ea_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3     # U32      (Ea-)  Wh / 0.001
            _n["Partial_rEa_neg"] = decoder.decode_16bit_uint() * sPI * 1e-1    # U16      (rEa-) Wh / 10
            _n["Partial_Er_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3     # U32      (Er+)  varh / 0.001
            _n["Partial_rEr_pos"] = decoder.decode_16bit_uint() * sPI * 1e-1    # U16      (rEr+) varh / 10
            _n["Partial_Er_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3     # U32      (Er-)  varh / 0.001
            _n["Partial_rEr_neg"] = decoder.decode_16bit_uint() * sPI * 1e-1    # U16      (rEr-) varh / 10
            _n["Partial_Eap"] = decoder.decode_32bit_uint() * sPI * 1e+3        # U32      (Eap) VAh / 0.001
            _n["Partial_rEap"] = decoder.decode_16bit_uint() * sPI * 1e-1       # U16      (rEap) VAh / 10
            _n["LastPart_ResetDate"] = decoder.decode_32bit_uint() * 1e+0       # U32      DATETIME
            _n["LastPart_HourMeter"] = decoder.decode_32bit_uint() * 1e+0       # U32      s
            _n["LastPart_Ea_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3    # U32      (Ea+)  Wh / 0.001
            _n["LastPart_rEa_pos"] = decoder.decode_16bit_uint() * sPI * 1e-1   # U16      (rEa+) Wh / 10
            _n["LastPart_Ea_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3    # U32      (Ea-)  Wh / 0.001
            _n["LastPart_rEa_neg"] = decoder.decode_16bit_uint() * sPI * 1e-1   # U16      (rEa-) Wh / 10
            _n["LastPart_Er_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3    # U32      (Er+)  varh / 0.001
            _n["LastPart_rEr_pos"] = decoder.decode_16bit_uint() * sPI * 1e-1   # U16      (rEr+) varh / 10
            _n["LastPart_Er_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3    # U32      (Er-)  varh / 0.001
            _n["LastPart_rEr_neg"] = decoder.decode_16bit_uint() * sPI * 1e-1   # U16      (rEr-) varh / 10
            _n["LastPart_Eap"] = decoder.decode_32bit_uint() * sPI * 1e+3       # U32      (Eap) VAh / 0.001
            _n["LastPart_rEap"] = decoder.decode_16bit_uint() * sPI * 1e-1      # U16      (rEap) VAh / 10
        return obj


    #----------------------------------------------------------------------------------------------
    def readDirisCombinedMeasurement(self, channel=0):
        """
        This is to read essential power and energy to miniize data traffic.
        """
        baseAddress_P = [ 0x4800, 0x5000, 0x5800, 0x6000 ] # power
        baseAddress_E = [ 0x4D80, 0x5580, 0x5D80, 0x6580 ] # Energy
        d = {}
        sPI = self.scale_PI
        try:
            d["Status"] = -1
            # Power
            d["Timestamp"] = self.createTimestamp()
            holdingRegs = self.readHoldingRegisters(baseAddress_P[i] + 0x2c, 10)
            decoder = self.getDecoder(holdingRegs)
            d.P = decoder.decode_32bit_int() * scalePI * 1                       # W
            d.Q = decoder.decode_32bit_int() * scalePI * 1                       # var
            decoder.skip_bytes(4 * 2)
            d.S = decoder.decode_32bit_uint() *  scalePI * 1                     # VA
            # Energy
            holdingRegs = self.readHoldingRegisters(baseAddress_E[i] + 0x03, 14)
            decoder = self.getDecoder(holdingRegs)
            d.Ea_pos = decoder.decode_32bit_uint() * scalePI * (1e+3)             # U32      (Ea+)  Wh / 0.001
            decoder.skip_bytes(1 * 2)
            d.Ea_neg = decoder.decode_32bit_uint() * scalePI * (1e+3)             # U32      (Ea-)  Wh / 0.001
            decoder.skip_bytes(1 * 2)
            d.Er_pos = decoder.decode_32bit_uint() * scalePI * (1e+3)             # U32      (Er+)  varh / 0.001
            decoder.skip_bytes(1 * 2)
            d.Er_neg = decoder.decode_32bit_uint() * scalePI * (1e+3)             # U32      (Er-)  varh / 0.001
            decoder.skip_bytes(1 * 2)
            d.Eap    = decoder.decode_32bit_uint() * scalePI * (1e+3)             #U32      (Eap) VAh / 0.001  Apparent Energy
            d["Status"] = 1
        except Exception as ex:
            # ignore
            pass
        return d


#--------------------------------------------------------------------------------------------------
#  DIRIS A60
#--------------------------------------------------------------------------------------------------
class A60Meter(ModbusMeter):
    """
    This meter has only one single channel; to keep compatibility we define a channel parameter like
    the other diris have.
    """
    def __init__(self, connection, unit_address=None, channel=0, scale_PI=1, scale_U=1): # NOTE: the trailing comma is to generate a tuple from single integer
        self.scale_PI = scale_PI
        self.scale_U = scale_U
        self.channel_count = 1
        assert (channel < self.channel_count)
        super().__init__(connection, unit_address=unit_address, channel=channel)

    def to_json(self):
        d = super().to_json()
        d.update({
            "scale_PI": self.scale_PI,
            "scale_U": self.scale_U
        })
        return d

    def getDecoder(self, registers): # setup the endianess for DIRIS meters
        return BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.Big, wordorder=Endian.Big)

    # common functions
    def readConstData(self, channel=None):
        return self.readProductId_A60()

    def readAcPowerData(self, channel=None):
        d = self.readLoadMeasurement_A60()
        if d["std"]["Status"] <= 0:
            return None
        # clean it up a bit
        del d["std"]["Channel"]
        return d["std"]

    def readAcEnergyData(self, channel=None):
        d = self.readEnergyMeter_A60()
        if d["std"]["Status"] <= 0:
            return None
        # clean it up a bit
        del d["std"]["Channel"]
        return d["std"]

    def readDcPowerData(self, channel=None):
        log.warning(type(self).__qualname__ + "readDcPowerData Need implementation")
        return

    def readDcEnergyData(self, channel=None):
        log.warning(type(self).__qualname__ + "readDcEnergyData Need implementation")
        return

    def readTemperatureData(self, channel=None):
        log.warning(type(self).__qualname__ + "readTemperatureData Need implementation")
        return

    #----------------------------------------------------------------------------------------------
    def readProductId_A60(self):
        """
        DIRIS PRODUCT IDENTIFICATION
        """
        d = {}
        holdingRegs = self.readHoldingRegisters(0xc350, 66)
        decoder = self.getDecoder(holdingRegs)
        cc = "ascii"
        d["Timestamp"] = self.createTimestamp()
        # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
        #decoded = OrderedDict([('Timestamp', self.createTimestamp()), ...
        d["IdString"] =                    self.filterString(decoder.decode_string(8)) # string_16[4]
        d["ProdOrderId"] =                 decoder.decode_16bit_uint()          # U16
        d["ProductId"] =                   decoder.decode_16bit_uint()          # U16
        d["ModbusTableVersion"] =          decoder.decode_16bit_uint()          # U16
        d["ProductSoftwareVersion"] =      decoder.decode_16bit_uint()          # U16
        d["Serial_AA_SS"] =                decoder.decode_16bit_uint()          # U16_HEX
        d["Serial_SST_L"] =                decoder.decode_16bit_uint()          # U16_HEX
        d["Serial_Order"] =                decoder.decode_16bit_uint()          # U16
        d["Serial_Reserve"] =              decoder.decode_32bit_uint()          # U32
        d["CodeTable"] =                   decoder.decode_64bit_uint()          # U64_HEX
        d["CustomizationDataLoaded"] =     decoder.decode_16bit_uint()          # U8
        d["ProductVersionMajor"] =         decoder.decode_16bit_uint()          # U16
        d["ProductVersionMinor"] =         decoder.decode_16bit_uint()          # U16
        d["ProductVersionRevision"] =      decoder.decode_16bit_uint()          # U16
        d["ProductVersionBuild"] =         decoder.decode_16bit_uint()          # U16
        #d["ProductBuildDate"] =            binascii.hexlify(decoder.decode_string(6)).decode(cc) # DATETIME_3
        d["ProductBuildDate"] =            decoder.decode_16bit_uint() * 0x100000000 + \
                                           decoder.decode_16bit_uint() * 0x10000 + \
                                           decoder.decode_16bit_uint()          # DATETIME_3
        d["SoftwareTechBaseVerMajor"] =    decoder.decode_16bit_uint()          # U16
        d["SoftwareTechBaseVerMinor"] =    decoder.decode_16bit_uint()          # U16
        d["SoftwareTechBaseVerRevision"] = decoder.decode_16bit_uint()          # U16
        d["CustomVersionMajor"] =          decoder.decode_16bit_uint()          # U16
        d["CustomVersionMinor"] =          decoder.decode_16bit_uint()          # U16
        d["ProductVLO"] =                  self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["CustomVLO"] =                   self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["SoftwareTechBaseVLO"] =         self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["VendorName"] =                  self.filterString(decoder.decode_string(8*2))  # String[8*2]
        d["ProductName"] =                 self.filterString(decoder.decode_string(8*2))  # String[8*2]
        d["ExtendedName"] =                self.filterString(decoder.decode_string(8*2))  # String[8*2]
        return d

    #----------------------------------------------------------------------------------------------
    def readLoadMeasurement_A60(self):
        """
        Reads the instant measurement data of the Load at address 0xc550. There is only one Load.
        scale_xx= scalers for U and P and I measurements.
        Returns dataset d which is valid and filled, if d[Status]>0.
        """
        baseAddress = [0xc550]
        # setup dictionary for read
        obj = {
            "std": {},  # standard data set - all kind of meters have to provide these data as minimum
            "soco": {}, # manufacturer specific data (empty here)
        }
        d = obj["std"]
        channel=0 # channel is fixed
        d["Channel"] = channel
        d["Status"] = 1 # there is no status register, we assume its ok if all readings go through
        sPI = self.scale_PI
        sU = self.scale_U
        _ba = baseAddress[channel]
        holdingRegs = self.readHoldingRegisters(_ba, 62)
        decoder = self.getDecoder(holdingRegs)
        _n = obj["soco"]
        d["Timestamp"] = self.createTimestamp()
        # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
        #d["HourMeter"] = decoder.decode_32bit_uint() * 36             # 1/100h --> s
        decoder.skip_bytes(2 * 2)
        d["U_L1L2"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L2L3"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L3L1"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L1N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        d["U_L2N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        d["U_L3N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        d["Frequency"] = decoder.decode_32bit_uint() * sU * 1e-2      # U32      Hz/100
        d["I_L1"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        d["I_L2"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        d["I_L3"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        d["I_N"] = decoder.decode_32bit_uint() * sPI * 1e-3           # U32      A/1000
        d["P"] = decoder.decode_32bit_int() * sPI * 1e+1              # S32      W/0.1
        d["Q"] = decoder.decode_32bit_int() * sPI * 1e+1              # S32      var/0.1
        d["S"] = decoder.decode_32bit_uint() * sPI * 1e+1             # U32      VA/0.1
        d["PF"] = decoder.decode_32bit_int() * 1e-3                   # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["P_L1"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        d["P_L2"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        d["P_L3"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        d["Q_L1"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        d["Q_L2"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        d["Q_L3"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        d["S_L1"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        d["S_L2"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        d["S_L3"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        d["PF_L1"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["PF_L2"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["PF_L3"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["I"] = decoder.decode_32bit_uint() * sPI * 1e-3             # U32      A/1000
        d["U_LL"] = decoder.decode_32bit_uint() * sU * 1e-2           # U32      V/100
        d["U_LN"] = decoder.decode_32bit_uint() * sU * 1e-2           # U32      V/100
        return obj

    #----------------------------------------------------------------------------------------------
    # these measurements are NOT scaled with CT settings!
    def readRawMeasurement_A60(self):
        """
        Reads the instant measurement data of the Load at address 0xc550. There is only one Load.
        scale_xx= scalers for U and P and I measurements.
        Returns dataset d which is valid and filled, if d[Status]>0.
        """
        baseAddress = [0xc850]
        # setup dictionary for read
        obj = {
            "std" : {},  # standard data set - all kind of meters have to provide these data as minimum
            "soco": {}, # manufacturer specific data (empty here)
        }
        d = obj["std"]

        channel=0 # channel is fixed
        d["Channel"] = channel
        d["Status"] = 1 # there is no status register, we assume its ok if all readings go through
        sPI = self.scale_PI[channel]
        sU = self.scale_U[channel]
        _ba = baseAddress[channel]
        holdingRegs = self.readHoldingRegisters(_ba, 35)
        decoder = self.getDecoder(holdingRegs)
        _n = obj["soco"]
        d["Timestamp"] = self.createTimestamp()
        # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
        #d["HourMeter"] = decoder.decode_16bit_uint() * 36             # 1/100h --> s
        decoder.skip_bytes(1 * 2)
        d["U_L1L2"] = decoder.decode_16bit_uint() * sU * 1e-2         # U16      V/100
        d["U_L2L3"] = decoder.decode_16bit_uint() * sU * 1e-2         # U16      V/100
        d["U_L3L1"] = decoder.decode_16bit_uint() * sU * 1e-2         # U16      V/100
        d["U_L1N"] = decoder.decode_16bit_uint() * sU * 1e-2          # U16      V/100
        d["U_L2N"] = decoder.decode_16bit_uint() * sU * 1e-2          # U16      V/100
        d["U_L3N"] = decoder.decode_16bit_uint() * sU * 1e-2          # U16      V/100
        d["Frequency"] = decoder.decode_16bit_uint() * sU * 1e-2      # U16      Hz/100
        d["I_L1"] = decoder.decode_16bit_uint() * sPI * 1e-3          # U16      A/1000
        d["I_L2"] = decoder.decode_16bit_uint() * sPI * 1e-3          # U16      A/1000
        d["I_L3"] = decoder.decode_16bit_uint() * sPI * 1e-3          # U16      A/1000
        d["I_N"] = decoder.decode_16bit_uint() * sPI * 1e-3           # U16      A/1000
        d["P"] = decoder.decode_16bit_int() * sPI * 1e+1              # S16      W/0.1
        d["Q"] = decoder.decode_16bit_int() * sPI * 1e+1              # S16      var/0.1
        d["S"] = decoder.decode_16bit_uint() * sPI * 1e+1             # U16      VA/0.1
        d["PF"] = decoder.decode_16bit_int() * 1e-3                   # S16      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["P_L1"] = decoder.decode_16bit_int() * sPI * 1e+1           # S16      W/0.1
        d["P_L2"] = decoder.decode_16bit_int() * sPI * 1e+1           # S16      W/0.1
        d["P_L3"] = decoder.decode_16bit_int() * sPI * 1e+1           # S16      W/0.1
        d["Q_L1"] = decoder.decode_16bit_int() * sPI * 1e+1           # S16      var/0.1
        d["Q_L2"] = decoder.decode_16bit_int() * sPI * 1e+1           # S16      var/0.1
        d["Q_L3"] = decoder.decode_16bit_int() * sPI * 1e+1           # S16      var/0.1
        d["S_L1"] = decoder.decode_16bit_uint() * sPI * 1e+1          # U16      VA/0.1
        d["S_L2"] = decoder.decode_16bit_uint() * sPI * 1e+1          # U16      VA/0.1
        d["S_L3"] = decoder.decode_16bit_uint() * sPI * 1e+1          # U16      VA/0.1
        d["PF_L1"] = decoder.decode_16bit_int() * 1e-3                # S16      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["PF_L2"] = decoder.decode_16bit_int() * 1e-3                # S16      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["PF_L3"] = decoder.decode_16bit_int() * 1e-3                # S16      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["Ea_pos_NoReset"] = decoder.decode_16bit_uint() * sPI * 1e+6 # U16      (Ea+)  Wh/0.000001
        d["Er_pos_NoReset"] = decoder.decode_16bit_uint() * sPI * 1e+6 # U16      (Er+)  varh/0.000001
        d["Ea_neg_NoReset"] = decoder.decode_16bit_uint() * sPI * 1e+6 # U16      (Ea-)  Wh/0.000001
        d["Er_neg_NoReset"] = decoder.decode_16bit_uint() * sPI * 1e+6 # U16      (Er+)  varh/0.000001
        return obj

    #----------------------------------------------------------------------------------------------
    def readEnergyMeter_A60(self):
        """
        Reads the accumulated energy data of a Load depending on the base address (0x4D80).
        This device has only one load channel.
        scale_xx= scalers for E, P and I measurements.
        Returns dataset d which is valid and filled, if d[Status]>0.
        """
        baseAddress = [0xC650]
        # setup dictionary for read results
        obj = {
            "std": {},  # standard datensatz
            "soco": {}, # manufacturer specific data
        }
        d = obj["std"]

        channel = 0 # only one channel
        d["Channel"] = channel
        d["Status"] = 1 # assume ok until all measures done; there is no status register
        sPI = self.scale_PI
        _ba = baseAddress[channel]
        holdingRegs = self.readHoldingRegisters(_ba, 65)
        decoder = self.getDecoder(holdingRegs)
        _n = obj["soco"]
        d["Timestamp"] = self.createTimestamp()
        _n["Timestamp"] = d["Timestamp"]
        # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
        d["HourMeter"] = decoder.decode_32bit_uint() * 36                   # U32      1/100h --> s
        d["Er_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3              # U32      (partial Er+)  varh/0.001
        d["Eap"] = decoder.decode_32bit_uint() * sPI * 1e+3                 # U32      (partial Eap)  vah/0.001 Apparent Energy
        d["Ea_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3              # U32      (partial Ea-)  Wh/0.001
        d["Er_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3              # U32      (partial Er-)  varh/0.001
        # offset to 0x2a
        decoder.skip_bytes(16 * 2)
        _n["LastDateForRecordAvgPQS"] = decoder.decode_32bit_uint() * 1e+1  # U32      DATETIME in s since 2000/01/01
        _n["P_pos_LastAvg"] = decoder.decode_16bit_uint() * sPI * 1e-1      # U16      (P+) W/10
        _n["Q_pos_LastAvg"] = decoder.decode_16bit_uint() * sPI * 1e-1      # U16      (Q+) var/10
        _n["P_neg_LastAvg"] = decoder.decode_16bit_uint() * sPI * 1e-1      # U16      (P-) W/10
        _n["Q_neg_LastAvg"] = decoder.decode_16bit_uint() * sPI * 1e-1      # U16      (Q-) var/10
        _n["S_LastAvg"] = decoder.decode_16bit_uint() * sPI * 1e-1          # U16      (S) VA/10
        return obj


#--------------------------------------------------------------------------------------------------
#  COUNTIS E24
#--------------------------------------------------------------------------------------------------
class E24Meter(ModbusMeter):
    """
    This meter has only one single channel; to keep compatibility we define a channel parameter like
    the other diris have.
    """
    def __init__(self, connection, unit_address=None, channel=0, scale_PI=1, scale_U=1): # NOTE: the trailing comma is to generate a tuple from single integer
        self.scale_PI = scale_PI
        self.scale_U = scale_U
        self.channel_count = 1
        assert (channel < self.channel_count)
        super().__init__(connection, unit_address=unit_address, channel=channel)

    def to_json(self):
        d = super().to_json()
        d.update({
            "scale_PI": self.scale_PI,
            "scale_U": self.scale_U
        })
        return d

    def getDecoder(self, registers): # setup the endianess for DIRIS meters
        return BinaryPayloadDecoder.fromRegisters(registers, byteorder=Endian.Big, wordorder=Endian.Big)

    # common functions
    def readConstData(self, channel=None):
        return self.readProductId_CountisE24()

    def readAcPowerData(self, channel=None):
        d = self.readLoadMeasurement_CountisE24()
        if d["std"]["Status"] <= 0:
            return None
        # clean it up a bit
        del d["std"]["Channel"]
        return d["std"]

    def readAcEnergyData(self, channel=None):
        d = self.readEnergyMeter_CountisE24()
        if d["std"]["Status"] <= 0:
            return None
        # clean it up a bit
        del d["std"]["Channel"]
        return d["std"]

    def readDcPowerData(self, channel=None):
        log.warning(type(self).__qualname__ + "readDcPowerData Need implementation")
        return

    def readDcEnergyData(self, channel=None):
        log.warning(type(self).__qualname__ + "readDcEnergyData Need implementation")
        return

    def readTemperatureData(self, channel=None):
        log.warning(type(self).__qualname__ + "readTemperatureData Need implementation")
        return

    #--------------------------------------------------------------------------------------------------
    def readProductId_CountisE24(self):
        """
        DIRIS PRODUCT IDENTIFICATION
        """
        d = {}
        # read part I (keep number of bytes on the bus low)
        holdingRegs = self.readHoldingRegisters(0xc350, 30)
        decoder = self.getDecoder(holdingRegs)
        cc = "ascii"
        d["Timestamp"] = self.createTimestamp()
        d["IdString"] =                    self.filterString(decoder.decode_string(8)) # string_16[4]
        d["ProdOrderId"] =                 decoder.decode_16bit_uint()          # U16
        d["ProductId"] =                   decoder.decode_16bit_uint()          # U16
        d["ModbusTableVersion"] =          decoder.decode_16bit_uint()          # U16
        d["ProductSoftwareVersion"] =      decoder.decode_16bit_uint()          # U16
        d["Serial_AA_SS"] =                decoder.decode_16bit_uint()          # U16_HEX
        d["Serial_SST_L"] =                decoder.decode_16bit_uint()          # U16_HEX
        d["Serial_Order"] =                decoder.decode_16bit_uint()          # U16
        d["Serial_Reserve"] =              decoder.decode_32bit_uint()          # U32
        d["CodeTable"] =                   decoder.decode_64bit_uint()          # U64_HEX
        d["CustomizationDataLoaded"] =     decoder.decode_16bit_uint()          # U8

        d["ProductVersionMajor"] =         decoder.decode_16bit_uint()          # U16
        d["ProductVersionMinor"] =         decoder.decode_16bit_uint()          # U16
        d["ProductVersionRevision"] =      decoder.decode_16bit_uint()          # U16
        d["ProductVersionBuild"] =         decoder.decode_16bit_uint()          # U16
        #d["ProductBuildDate"] =            binascii.hexlify(decoder.decode_string(6)).decode(cc) # DATETIME_3
        d["ProductBuildDate"] =            decoder.decode_16bit_uint() * 0x100000000 + \
                                           decoder.decode_16bit_uint() * 0x10000 + \
                                           decoder.decode_16bit_uint()          # DATETIME_3
        d["SoftwareTechBaseVerMajor"] =    decoder.decode_16bit_uint()          # U16
        d["SoftwareTechBaseVerMinor"] =    decoder.decode_16bit_uint()          # U16
        d["SoftwareTechBaseVerRevision"] = decoder.decode_16bit_uint()          # U16
        d["CustomVersionMajor"] =          decoder.decode_16bit_uint()          # U16
        d["CustomVersionMinor"] =          decoder.decode_16bit_uint()          # U16
        # read part II : strings
        holdingRegs = self.readHoldingRegisters(0xc350+0x1e, 36)
        decoder = self.getDecoder(holdingRegs)
        d["ProductVLO"] =                  self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["CustomVLO"] =                   self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["SoftwareTechBaseVLO"] =         self.filterString(decoder.decode_string(4*2))  # String[4*2]
        d["VendorName"] =                  self.filterString(decoder.decode_string(8*2))  # String[8*2]
        d["ProductName"] =                 self.filterString(decoder.decode_string(8*2))  # String[8*2]
        d["ExtendedName"] =                self.filterString(decoder.decode_string(8*2))  # String[8*2]
        return d

    def readLoadMeasurement_CountisE24(self):
        """
        Reads the instant measurement data of the Load at address 0xc550. There is only one Load.
        scale_xx= scalers for U and P and I measurements.
        Returns dataset d which is valid and filled, if d[Status]>0.
        """
        baseAddress = [0xc550]
        # setup dictionary for read
        obj = {
            "std": {},  # standard data set - all kind of meters have to provide these data as minimum
            "soco": {}, # manufacturer specific data (empty here)
        }
        d = obj["std"]
        channel=0 # channel is fixed
        d["Channel"] = channel
        d["Status"] = 1 # there is no status register, we assume its ok if all readings go through
        sPI = self.scale_PI
        sU = self.scale_U
        _ba = baseAddress[channel]
        holdingRegs = self.readHoldingRegisters(_ba, 62)
        decoder = self.getDecoder(holdingRegs)
        _n = obj["soco"]
        d["Timestamp"] = self.createTimestamp()
        # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
        #d["HourMeter"] = decoder.decode_32bit_uint() * 36             # 1/100h --> s
        decoder.skip_bytes(2 * 2)
        d["U_L1L2"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L2L3"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L3L1"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L1N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        d["U_L2N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        d["U_L3N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        # reserved - d["Frequency"] = decoder.decode_32bit_uint() * sU * 1e-2      # U32      Hz/100
        decoder.skip_bytes(2 * 2)
        d["I_L1"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        d["I_L2"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        d["I_L3"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        d["I_N"] = decoder.decode_32bit_uint() * sPI * 1e-3           # U32      A/1000
        d["P"] = decoder.decode_32bit_int() * sPI * 1e+1              # S32      W/0.1
        d["Q"] = decoder.decode_32bit_int() * sPI * 1e+1              # S32      var/0.1
        d["S"] = decoder.decode_32bit_uint() * sPI * 1e+1             # U32      VA/0.1
        d["PF"] = decoder.decode_32bit_int() * 1e-3                   # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["P_L1"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        d["P_L2"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        d["P_L3"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        d["Q_L1"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        d["Q_L2"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        d["Q_L3"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        d["S_L1"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        d["S_L2"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        d["S_L3"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        d["PF_L1"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["PF_L2"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["PF_L3"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        # reserved - d["I"] = decoder.decode_32bit_uint() * sPI * 1e-3             # U32      A/1000
        # reserved - d["U_LL"] = decoder.decode_32bit_uint() * sU * 1e-2           # U32      V/100
        # reserved - d["U_LN"] = decoder.decode_32bit_uint() * sU * 1e-2           # U32      V/100
        return obj


    def readRawMeasurement_CountisE24(self):
        """
        these measurements are NOT scaled with CT settings!
        """
        baseAddress = [0xc850]
        # setup dictionary for read
        obj = {
            "std": {},  # standard data set - all kind of meters have to provide these data as minimum
            "soco": {}, # manufacturer specific data (empty here)
        }
        d = obj["std"]
        channel=0 # channel is fixed
        d["Channel"] = channel
        d["Status"] = 1 # there is no status register, we assume its ok if all readings go through
        sPI = self.scale_PI
        sU = self.scale_U
        _ba = baseAddress[channel]
        holdingRegs = self.readHoldingRegisters(_ba, 35)
        decoder = self.getDecoder(holdingRegs)
        _n = obj["soco"]
        d["Timestamp"] = self.createTimestamp()
        # ORDER OF DECODING IS IMPORTANT AS DECODER MOVES INTERNAL DATA POINTER
        #d["HourMeter"] = decoder.decode_32bit_uint() * 36             # 1/100h --> s
        decoder.skip_bytes(2 * 2)
        d["U_L1L2"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L2L3"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L3L1"] = decoder.decode_32bit_uint() * sU * 1e-2         # U32      V/100
        d["U_L1N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        d["U_L2N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        d["U_L3N"] = decoder.decode_32bit_uint() * sU * 1e-2          # U32      V/100
        decoder.skip_bytes(8 * 2)
        # reserved - d["Frequency"] = decoder.decode_32bit_uint() * sU * 1e-2      # U32      Hz/100
        # reserved - d["I_L1"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        # reserved - d["I_L2"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        # reserved - d["I_L3"] = decoder.decode_32bit_uint() * sPI * 1e-3          # U32      A/1000
        # reserved - d["I_N"] = decoder.decode_32bit_uint() * sPI * 1e-3           # U32      A/1000
        # reserved - d["P"] = decoder.decode_32bit_int() * sPI * 1e+1              # S32      W/0.1
        # reserved - d["Q"] = decoder.decode_32bit_int() * sPI * 1e+1              # S32      var/0.1
        # reserved - d["S"] = decoder.decode_32bit_uint() * sPI * 1e+1             # U32      VA/0.1
        d["PF"] = decoder.decode_32bit_int() * 1e-3                   # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        decoder.skip_bytes(9 * 2)
        # reserved - d["P_L1"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        # reserved - d["P_L2"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        # reserved - d["P_L3"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      W/0.1
        # reserved - d["Q_L1"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        # reserved - d["Q_L2"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        # reserved - d["Q_L3"] = decoder.decode_32bit_int() * sPI * 1e+1           # S32      var/0.1
        # reserved - d["S_L1"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        # reserved - d["S_L2"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        # reserved - d["S_L3"] = decoder.decode_32bit_uint() * sPI * 1e+1          # U32      VA/0.1
        d["PF_L1"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["PF_L2"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        d["PF_L3"] = decoder.decode_32bit_int() * 1e-3                # S32      -/1000  - kapazitiv/leading, +induktiv/lagging
        decoder.skip_bytes(3 * 2)
        d["Ea_pos_NoReset"] = decoder.decode_16bit_int() * sPI * 1e+6 # U16      (Ea+)  Wh/0.000001
        d["Er_pos_NoReset"] = decoder.decode_16bit_int() * sPI * 1e+6 # U16      (Er+)  varh/0.000001
        d["Ea_neg_NoReset"] = decoder.decode_16bit_int() * sPI * 1e+6 # U16      (Ea-)  Wh/0.000001
        d["Er_neg_NoReset"] = decoder.decode_16bit_int() * sPI * 1e+6 # U16      (Er+)  varh/0.000001
        return obj


    def readEnergyMeter_CountisE24(self):
        # setup dictionary for read
        obj = {
            "std": {},  # standard data set - all kind of meters have to provide these data as minimum
            "soco": {}, # manufacturer specific data (empty here)
        }
        d = obj["std"]
        d["Channel"] = 0 # channel is fixed
        d["Status"] = 1 # there is no status register, we assume its ok if all readings go through
        sPI = self.scale_PI
        sU = self.scale_U
        # 65 words of holding registers, but lot Unused/Reserved.
        # thus split reading into two smaller to save bus bandwidth
        _n = obj["soco"]
        _u100 = {}
        holdingRegs = self.readHoldingRegisters(0xC650, 20)
        decoder = self.getDecoder(holdingRegs)
        d["Timestamp"] = self.createTimestamp()
        # data Unit / 1000
        decoder.skip_bytes(2 * 2)
        d["Ea_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3                 # U32      (partial Ea+)  Wh/0.001
        d["Er_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3                 # U32      (partial Er+)  varh/0.001
        decoder.skip_bytes(2 * 2)
        d["Ea_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3                 # U32      (partial Ea-)  Wh/0.001
        decoder.skip_bytes(2 * 2)
        d["Ea_pos_partial"] = decoder.decode_32bit_uint() * sPI * 1e+3         # U32      (partial Ea+)  Wh/0.001
        d["Er_pos_partial"] = decoder.decode_32bit_uint() * sPI * 1e+3         # U32      (partial Er+)  varh/0.001
        decoder.skip_bytes(2 * 2)
        d["Ea_neg_partial"] = decoder.decode_32bit_uint() * sPI * 1e+3         # U32      (partial Ea-)  Wh/0.001

        # more precise data Unit/100
        holdingRegs = self.readHoldingRegisters(0xC700, 20)
        decoder = self.getDecoder(holdingRegs)
        _u100["Ea_pos"] = decoder.decode_32bit_uint() * sPI * 1e+1             # U32      (partial Ea+)  Wh/0.1
        _u100["Er_pos"] = decoder.decode_32bit_uint() * sPI * 1e+1             # U32      (partial Er+)  varh/0.1
        decoder.skip_bytes(2 * 2)
        _u100["Ea_neg"] = decoder.decode_32bit_uint() * sPI * 1e+1             # U32      (partial Ea-)  Wh/0.001
        decoder.skip_bytes(2 * 2)
        _u100["Ea_pos_partial"] = decoder.decode_32bit_uint() * sPI * 1e+1     # U32      (partial Ea+)  Wh/0.1
        _u100["Er_pos_partial"] = decoder.decode_32bit_uint() * sPI * 1e+1     # U32      (partial Er+)  varh/0.1
        decoder.skip_bytes(2 * 2)
        _u100["Ea_neg_partial"] = decoder.decode_32bit_uint() * sPI * 1e+1     # U32      (partial Ea-)  Wh/0.001

        # combine them
        d["Ea_pos"] += (_u100["Ea_pos"] % (1e+3))
        d["Er_pos"] += (_u100["Er_pos"] % (1e+3))
        d["Ea_neg"] += (_u100["Ea_neg"] % (1e+3))
        d["Ea_pos_partial"] += (_u100["Ea_pos_partial"] % (1e+3))
        d["Er_pos_partial"] += (_u100["Er_pos_partial"] % (1e+3))
        d["Ea_neg_partial"] += (_u100["Ea_neg_partial"] % (1e+3))
        return obj


    def readCombinedMeasurement_CountisE24(self):
        baseAddress_P = [ 0xc550 ] # power
        baseAddress_E = [ 0xC650, 0xC700 ] # Energy
        d={}
        d["Status"] = 1 # there is no status register, we assume its ok if all readings go through
        sPI = self.scale_PI
        sU = self.scale_U
        _u100 = {}
        try:
            d["Status"] = -1
            # Power
            holdingRegs = self.readHoldingRegisters(baseAddress_P[i] + 0x18, 6)
            decoder = self.getDecoder(holdingRegs)
            d["Timestamp"] = self.createTimestamp()
            d["P"] = decoder.decode_32bit_int() * sPI * 1e+1              # S32      W/0.1
            d["Q"] = decoder.decode_32bit_int() * sPI * 1e+1              # S32      var/0.1
            d["S"] = decoder.decode_32bit_uint() * sPI * 1e+1             # U32      VA/0.1
            # Energy
            holdingRegs = self.readHoldingRegisters(baseAddress_E[i] + 0x02, 8)
            decoder = self.getDecoder(holdingRegs)
            d["Ea_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3        # U32      (partial Ea+)  Wh/0.001
            d["Er_pos"] = decoder.decode_32bit_uint() * sPI * 1e+3        # U32      (partial Er+)  varh/0.001
            decoder.skip_bytes(2 * 2)
            d["Ea_neg"] = decoder.decode_32bit_uint() * sPI * 1e+3        # U32      (partial Ea-)  Wh/0.001
            # more precise data Unit/100
            holdingRegs = self.readHoldingRegisters(baseAddress_E[i + 1] + 0x02, 8)
            decoder = self.getDecoder(holdingRegs)
            _u100["Ea_pos"] = decoder.decode_32bit_uint() * sPI * 1e+1    # U32      (partial Ea+)  Wh/0.1
            _u100["Er_pos"] = decoder.decode_32bit_uint() * sPI * 1e+1    # U32      (partial Er+)  varh/0.1
            decoder.skip_bytes(2 * 2)
            _u100["Ea_neg"] = decoder.decode_32bit_uint() * sPI * 1e+1    # U32      (partial Ea-)  Wh/0.001
            # combine them
            d["Ea_pos"] += (_u100["Ea_pos"] % (1e+3))
            d["Er_pos"] += (_u100["Er_pos"] % (1e+3))
            d["Ea_neg"] += (_u100["Ea_neg"] % (1e+3))
            d["Status"] = 1
        except Exception as ex:
            pass
        return d


#--------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    print("Start test")

    diris1 = DirisMeter("tcp:192.168.32.40:502:25")
    diris1.open()

    diris2 = DirisMeter("tcp:192.168.32.40:502", unit_address=24)
    diris2.open()

    data = diris1.readProductId_Diris()
    data = diris1.readLoadMeasurement_Diris()

    # abstract functions
    data = diris2.readConstData()
    data = diris2.readAcPowerData()

    diris1.close()
    diris2.close()

    print("End test")
