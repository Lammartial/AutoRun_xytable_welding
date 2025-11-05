"""
PETA Design PCBA Adapter.
"""

#import unittest
from traceback import print_exception
from re import A
from typing import Tuple
from struct import pack, unpack, unpack_from, pack_into
from binascii import hexlify
from time import sleep, perf_counter
from pathlib import Path
from unicodedata import ucd_3_2_0
from scipy.constants import zero_Celsius as KELVIN_ZERO_DEGC
from rrc.eth2can import CANBus
from rrc.eth2i2c import I2CPort
from rrc.i2cbus import BusMux, I2CMuxedBus
from rrc.smbus import BusMaster
from rrc.chipsets import BQ40Z50R1, BQStudioFileFlexFlasher, BQ34Z100, BQ76942
from rrc.gpio_tcal6416 import TCAL6416
from rrc.cartridge_peta import CartridgePETA
from rrc.relayboard_i2cio4r4xdpdt import RelayBoard4Relay4GPIO
from rrc.cell_voltage_simulation import CellVoltageSimulation
from rrc.calibration_storage import CalibrationStorage
from rrc.temperature_sts21 import STS21
from rrc.barcode_scanner import create_barcode_scanner
from rrc.feasa import FEASA_CH9121
from rrc.itech import M3400
from rrc.keysight import DAQ970A
from rrc.petalite_programmer import AlgocraftProgrammer
from rrc.smartbattery import Battery


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 1

from rrc.custom_logging import getLogger, logger_init



#--------------------------------------------------------------------------------------------------


def test_calibration_storage_only(calib: CalibrationStorage) -> None:
    print("Read calibration EEPROM values")
    print("Inventory Number: ", calib.load_inventory_number())
    print("Shunt Resistance: ", calib.load_shunt_resistance_ohm())
    [print(f"Leakage Current: {i}# {calib.load_leakcurrent_amps(i)}") for i in range(3)]


def test_cartridge_only(cart: CartridgePETA) -> None:

    #cart.gpio.set_pin(7) # enable the AFE and Gasgauge
    cart.select_bus_to_micro("i2c")
    #print("I2C to MICRO: ", cart.get_muxed_i2c_bus_for(1).i2c_bus_scan())
    #print("I2C to BACKYARD: ", cart.get_muxed_i2c_bus_for(2).i2c_bus_scan())
    #print("I2C to GPIO: ", cart.get_muxed_i2c_bus_for(8).i2c_bus_scan())
    for i in range(3):
        cart.switch_mosfet(i, 1)
        sleep(0.15)
        cart.switch_mosfet(i, 0)
        sleep(0.15)
    cart.select_bus_to_micro("can")
    #print("I2C to MICRO: ", cart.get_muxed_i2c_bus_for(1).i2c_bus_scan())
    #print("I2C to BACKYARD: ", cart.get_muxed_i2c_bus_for(2).i2c_bus_scan())
    #print("I2C to GPIO: ", cart.get_muxed_i2c_bus_for(8).i2c_bus_scan())
    cart.select_bus_to_micro("i2c")

#--------------------------------------------------------------------------------------------------

def rack_test(cartridge: CartridgePETA,
              gpio: RelayBoard4Relay4GPIO,
              vsim: CellVoltageSimulation,
              calib: CalibrationStorage,
              feasa: FEASA_CH9121,
              psu1: M3400, psu2: M3400,
              daq: DAQ970A,
              can: CANBus,
              ap: AlgocraftProgrammer,
            ) -> None:

    # prepare the microcontroller programming
    ap.set_filenames("petalite-test-image.wni", "petalite-test.wnp", erase_flash_project_file="petalite-flash-erase.wnp")
    print("Integrity check MD5: ")
    if ap.verify_all_files_on_programmer(
        "821C93A15324CC4E05E839E8D04521AE",
        "322D36DAE4DBA54A1B06164744D266E4",
        erase_project_file_hash="0711D04EFD02FA4E3317F3D6829FDA0D"):
        print("Ok.")
    else:
        print("Need to send Files to the programmer.")
        ap.send_all_files()


    #psu.configure_voltage_rise_times(pos="DEF", neg="DEF")
    #psu.configure_current_rise_times(pos="DEF", neg="DEF")

    # verify that PSU does not trigger battery protection
    num_cells = 7
    print("PSU Output on")
    u_cell = 3.5
    u_supply = u_cell*num_cells
    print(u_supply, u_cell)
    psu1.configure_supply(u_supply, 0.080, 50, 0)
    psu2.configure_supply(u_supply, 0.080, 50, 0)
    u_supply = u_cell * num_cells
    #psu2.configure_cc_mode(0.05, 10.8*1.15, (10.8*1.15) * 0.8, 50, 1)

    sleep(0.5)  # wait PSU powered up

    print("Measure PSU1", psu1.get_all_measurements())
    print("Measure PSU2", psu2.get_all_measurements())

    #vsim.power_down_all_cell_channels()
    #sleep(0.2)
    vsim.enable_all_cell_channels()
    for cell_no in range(1, num_cells):
        vsim.set_cell_n_voltage(cell_no, u_cell)

    # switch cell side on first
    psu2.set_output_state(1)
    sleep(0.25)
    psu1.set_output_state(1)
    sleep(0.5)

    print("Measure PSU1", psu1.get_all_measurements())
    print("Measure PSU2", psu2.get_all_measurements())

   
    # sleep(0.5)
    # cartridge.select_bus_to_micro("can")
    # can.send(0x11, (1,2,3,4,5,6,7,8))
    # print(can.receive(0x11))
    # cartridge.select_bus_to_micro("i2c")
    # sleep(0.5)


    # # push button
    # gpio.set_gpio_n_as_output(6)  # pin 6 as output
    # #gpio.set_gpio_n_low(6)  # push button enabled
    # gpio.set_gpio_n_high(6)
    # #gpio.set_gpio_n_low(6)

    #cartridge.select_bus_to_micro("i2c")
    print("BACKYARD:", cartridge.backyard_bus.i2c_bus_scan())
    print("MICRO:", cartridge.bus_to_mirco.i2c_bus_scan())
    #for n in range(1,9):
    #    print(cartridge.get_muxed_i2c_bus_for(n).i2c_bus_scan())


    # ENABLE FETs
    def _enable_fets(timeout: float = 10.0) -> None:
        n = int(round(timeout * 10))
        while n > 0:
            status = afe.read_fet_status()
            if (status["DDSG_PIN"] == 0) and (status["CHG_FET"] == 1) and (status["DSG_FET"] == 1):
                return
            print(status)  # DEBUG
            #if (status["DDSG_PIN"] == 0):
            _ok = afe.toggle_fet_enable()
            sleep(0.1)
            n -= 1
        raise RuntimeError(f"Could not enable FET {status}")

    # DISABLE FETs
    def _disable_fets(timeout: float = 10.0) -> None:
        n = int(round(timeout * 10))
        while n > 0:
            status = afe.read_fet_status()
            if (status["DDSG_PIN"] == 1) and (status["CHG_FET"] == 0) and (status["DSG_FET"] == 0):
                return
            print(status)  # DEBUG
            #if (status["DDSG_PIN"] == 1):
            _ok = afe.toggle_fet_enable()
            sleep(0.1)
            n -= 1
        raise RuntimeError(f"Could not disable FET {status}")

    def setup_daq_range_and_resolution() -> bool:

        _config = [
            (c, "10 V", "DEF") for c in (11, 12, 14, 10, 18, 19, 5, 8, 9)] + [
            (15, "100 V", "DEF"), (4, "100 V", "DEF"),  # Stack and PACK+
        ]
        for channel, range, resolution in _config:
            daq.setup_voltage_range_and_resolution_preset(channel, range, resolution)
        print(daq.read_error_status())

        _config_delay = [
            (11, 0.002), (12, 0.002), (14, 0.002), (10, 0.002), (18, 0.002), (19, 0.002), (5, 0.002),  # cells
            (8, 0.002), (9, 0.002),  # VCC supplies
            (15, 0.002), (4, 0.002), # Stack and PACK+
        ]
        #for channel, delay_in_s in _config_delay:
        #    daq.setup_channel_delay_preset(channel, delay_in_s=delay_in_s)

        print(daq.read_error_status())
        return True

    def read_voltages_from_daq() -> Tuple[Tuple[float], Tuple[float]]:
        u_cell = ()
        for channel in [11, 12, 14, 10, 18, 19, 5]:
            u_cell += (daq.get_VDC(channel),)
            sleep(0.02)
        u_xtra = ()
        u_xtra += (daq.get_VDC(15),)  # full pack voltage at cellstack side
        sleep(0.02)
        u_xtra += (daq.get_VDC(8),)   # should be +3.3v
        sleep(0.02)
        u_xtra += (daq.get_VDC(9),)   # should be +1.8v
        sleep(0.02)
        u_xtra += (daq.get_VDC(4),)   # pack+ voltage at connector side
        sleep(0.02)
        return u_cell, u_xtra


    setup_daq_range_and_resolution()

    print("Read voltages from DAQ:")
    u_cells, u_xtras = read_voltages_from_daq()
    print("Cells: ", u_cells)
    print("Cellstack: ", u_xtras[0])
    print("+3.3v VCC: ", u_xtras[1])
    print("+1.8v VCC: ", u_xtras[2])
    print("Pack: ", u_xtras[3])

    # print("DAQ - channel 11", daq.get_VDC(11))
    # print("DAQ - channel 12", daq.get_VDC(12))
    # print("DAQ - channel 14", daq.get_VDC(14))
    # print("DAQ - channel 10", daq.get_VDC(10))
    # print("DAQ - channel 18", daq.get_VDC(18))
    # print("DAQ - channel 19", daq.get_VDC(19))
    # print("DAQ - channel 5", daq.get_VDC(5))

    # print("DAQ - channel 15", daq.get_VDC(15))  # full pack voltage

    # print("DAQ - channel 8", daq.get_VDC(8))  # should be +3.3v
    # print("DAQ - channel 9", daq.get_VDC(9))  # should be +1.8v

    # cartridge.gpio.reset_pin(7)  # disable gg
    # cartridge.gpio.reset_pin(4)  # disable micro
    # cartridge.switch_mosfet(0, 0)  # disable micro
    


    base_path = Path(__file__).parent / "../../Battery-PCBA-Test/filestore"

   
    try:

        afe = BQ76942(cartridge.backyard_bus, slvAddress=0x08, pec=True, retry_limit=5)
        #afe.disable_checksum()

        print(afe.read_control_status())
        print(afe.read_battery_status())
        print(afe.read_safety_status(hexi=True))
        print(afe.read_dastatus())

        afe.read_temperature_calibration_offsets() # stores them into afe.temperature_calibration_offsets


        print("AFE: SEALED?", afe.is_sealed(refresh=True))
        print("AFE: FULL ACCESS?", afe.is_unsealed(check_fullaccess=True, refresh=True))
        #print("AFE: SEALING...", afe.seal())
        print("AFE: enable full access ...", afe.enable_full_access())
        print("AFE: FULL ACCESS?", afe.is_unsealed(check_fullaccess=True, refresh=True))


        # AFE need always transfer into RAM
        ff = BQStudioFileFlexFlasher(afe, base_path / "GG_3412185A-02_A_draft4_unsealed_PF_Fet_dis_CDFETOFF_PDwn_Petalite_AFE_settings.gm.fs" )
        ff.validate_file()
        tic = perf_counter()
        ff.program_fw_file()
        toc = perf_counter()
        _log.info(f"DONE in {toc - tic:0.4f} seconds.")

        #psu1.set_output_state(0)
        sleep(1.0)


        #print(afe.read_subcommand(0x00a0))
        #print(afe.read_subcommand(0x9234))
        print(afe.read_cell_voltages())
        print(afe.read_temperatures())

        # This step will enable the FETs to calibrate Top-of-Stack, PACK, and LD voltages.
        # Make sure FETs are closed for PACK and LD measurements
        afe.disable_sleepmode()  # Sleep Disable 0x009A to prevent CHG FET from opening
        #psu1.set_output_state(0)

        print("MFG STATUS:", afe.read_manufacturing_status())
        print("SAFETY STATUS:", afe.read_safety_status())
        #print(afe.all_fets_on())
        #print(afe.discharge_test())
        #print(afe.charge_test())
        #print(afe.read_manufacturing_status())
        print("ALARM STATUS:", afe.read_alarm_status())
        print("FET status: ", afe.read_fet_status())

        print("GPIO Cartridge:", hex(cartridge.gpio.read_input()))

        if 0:
            cartridge.switch_some_io(7, 0)  # enable microcontroller
            ap.erase_flash()
            ap.program_flash()
            cartridge.switch_some_io(7, 1)  # disable microcontroller
        
        if 0:
            cartridge.switch_some_io(7, 1)  # disable microcontroller
            cartridge.switch_mosfet(0, 0)  # 0ohm
            cartridge.switch_mosfet(1, 0)  # 20kohm
            cartridge.switch_mosfet(2, 0)  # 200kohm
            cartridge.switch_mosfet(3, 0)  # 400kohm
            #------------------------------------------------------------------
            cartridge.select_bus_to_micro("i2c")
            cartridge.switch_some_io(7, 0)  # enable microcontroller
     
            for n in range(1,9):
                print(cartridge.get_muxed_i2c_bus_for(n).i2c_bus_scan())

            bat = Battery(BusMaster(cartridge.bus_to_mirco))
            print(bat.temperature())
        
        # NOTE: The µ-controller interacts with AFE and GG so program it
        # after all things are set for AFE and GG.
        #------------------------------------------------------------------
        cartridge.switch_some_io(7, 1)  # disable microcontroller
        #print("Program FLASH:", ap.program_flash())
        cartridge.switch_mosfet(0, 0)  # 0ohm
        cartridge.switch_mosfet(1, 0)  # 20kohm
        cartridge.switch_mosfet(2, 1)  # 200kohm
        cartridge.switch_mosfet(3, 0)  # 400kohm
        #------------------------------------------------------------------
        cartridge.select_bus_to_micro("can")
        cartridge.switch_some_io(7, 0)  # enable microcontroller
        sleep(1.0)
        print(can.receive(0x7ff))
        print(can.send(0x620, (0x40,0x09,0x20,0x00,0x00,0x00,0x00,0x00)))  # voltage
        print(can.send(0x620, (0x40,0x0a,0x20,0x00,0x00,0x00,0x00,0x00)))  # current
        print(can.receive(0x5a0))
        print(can.receive(0xffff))
        print(can.recover_can_driver_on_remote())
        print(can.reinstall_can_driver_on_remote())
        # expected response: 0x5a0 8 0x4b 0x09 0x20 0x00 0xd2 0x5d 0x00 0x00 (voltage at 4 and 5)
        cartridge.select_bus_to_micro("i2c")
        sleep(0.5)
        cartridge.switch_some_io(7, 1)  # diable microcontroller
    


        # # NOTE: The µ-controller interacts with AFE and GG so program it
        # # after all things are set for AFE and GG.
        # #------------------------------------------------------------------
        # cartridge.switch_some_io(7, 1)  # diable microcontroller
        # #print("Program FLASH:", ap.program_flash())
        # #------------------------------------------------------------------
        # sleep(1.0)
        # cartridge.select_bus_to_micro("can")
        # cartridge.switch_some_io(7, 0)  # enable microcontroller
        # print(can.send(0x620, (0x40,0x09,0x20,0x00,0x00,0x00,0x00,0x00))) 
        # print(can.receive(0x5a0))
        # # expected response: 0x5a0 8 0x4b 0x09 0x20 0x00 0xd2 0x5d 0x00 0x00 (voltage at 4 and 5)
        # cartridge.select_bus_to_micro("i2c")
        # sleep(0.5)
        # cartridge.switch_some_io(7, 1)  # diable microcontroller






        #------------------------------------------------------------------
        # GG: Gas Gauge FW update
        gg = BQ34Z100(BusMaster(cartridge.backyard_bus, retry_limit=5), slvAddress=0x55, pec=False)
        v = gg.read_version_information()
        print(v)
        print(gg.teststand_read_version_information())

        if (v["hw_version"] == "0x0080") and (v["fw_version"] == "0x0202") and (v["device_type"] == "0x0100"):
            # differencial only
            ff2 = BQStudioFileFlexFlasher(gg, base_path / "3412185B-02_A_RRC3570-4_BMS-Files.df.fs" )
            ff2.validate_file()
            tic = perf_counter()
            ff2.program_fw_file()
            toc = perf_counter()
            print(f"DONE in {toc - tic:0.4f} seconds.")

        else:
            # full update necessary
            # write FLASH -----------
            ff2 = BQStudioFileFlexFlasher(gg, base_path / "3412185B-02_A_RRC3570-4_BMS-Files.bq.fs" )
            ff2.validate_file()
            tic = perf_counter()
            ff2.program_fw_file()
            toc = perf_counter()
            print(f"DONE in {toc - tic:0.4f} seconds.")

        print(gg.get_voltage_scale())
        print(gg.get_current_scale())
        print(gg.get_energy_scale())
        print(gg.voltage())
        print(gg.temperature())

        print("GG: SEALED?", gg.is_sealed(refresh=True))
        print("GG: FULL ACCESS?", gg.is_unsealed(check_fullaccess=True, refresh=True))
        #print("GG: SEALING...", gg.seal())
        print("GG: enable full access ...", gg.enable_full_access())
        print("GG: FULL ACCESS?", gg.is_unsealed(check_fullaccess=True, refresh=True))

        # GG: enter calibration mode ----------

        gg.read_control_status()
        if gg._control_status["CALEN"] == 0:
            gg.enable_enter_and_exit_of_calibration_mode()
            sleep(0.1)

        gg.enter_calibration()
        v = gg.read_calibration_flash_data()
        gg_cc_gain_stored = v["cc_gain"]
        gg_cc_delta_stored = v["cc_delta"]
        gg_cc_offset_stored = v["cc_offset"]
        gg_voltage_divider_stored = v["voltage_divider"]
        gg_board_offset_stored = v["board_offset"]
        gg_int_temperature_offset_stored = v["int_temperature_offset"]
        gg_ext_temperature_offset_stored = v["ext_temperature_offset"]
        print("GG: stored calibration values:")
        print(" Voltage divider:", gg_voltage_divider_stored)
        print(" Board offset:", gg_board_offset_stored)
        print(" Int. temp. offset:", gg_int_temperature_offset_stored)
        print(" Ext. temp. offset:", gg_ext_temperature_offset_stored)
        print(" CC Gain:", gg_cc_gain_stored)
        print(" CC Delta:", gg_cc_delta_stored)
        print(" CC Offset:", gg_cc_offset_stored)
        print(" Magic constant:", gg_cc_delta_stored / gg_cc_gain_stored, " = 1193046.0 ?")

        # =====================================================================================
        # === calibrate temperature ===
        # =====================================================================================

        # 1) apply known temperature TEMP(cal)
        #temp_cal = 21.4
        temp_cal = daq.get_temp(3, "RTD", 1000, 0, "")  # channel 3 + 13
        print("T_ambient:", temp_cal)
        # 2) measure the temperatures
        new_t_ofs = afe.calib_write_temperature(temp_cal)
        print(new_t_ofs)
        # re-check temperature measurement (repeat the calibration if not successful!)
        sleep(1.0)
        print("Recheck temperature measurement after temperature calibration:")
        print(afe.read_temperatures())
        
        # t_meas = [0.0] * 10
        # for n in range(5):
        #     t0 = afe.read_temperatures()
        #     for i in range(len(t_meas)):
        #         t_meas[i] += t0[i]
        #     sleep(0.050)
        # t_meas = [t/5 for t in t_meas]
        # # 3) calculate the offsets
        # temp_offsets = [((temp_cal - t) if t > -100 else 0) for t in t_meas]
        # print("T-OFFSETS:", temp_offsets)

        # # write the temperature calibration values
        # afe.read_temperature_calibration_offsets() # stores them into afe.temperature_calibration_offsets
        # afe.enter_config_update_mode()
        # afe.write_temperature_calibration_offsets(temp_offsets)
        # afe.exit_config_update_mode()
        # sleep(1.0)
        # # re-check temperature measurement (repeat the calibration if not successful!)
        # print("Recheck temperature measurement after temperature calibration:")
        # print(afe.read_temperatures())
        # afe.enter_config_update_mode()
        # print(afe.read_temperature_calibration_offsets(hexi=True))
        # afe.exit_config_update_mode()


        gg.calib_write_temperature(temp_cal)

        # gg_temperature = gg.temperature()  # in degC
        # gg_ext_temperature_offset = temp_cal - gg_temperature
        # print("T_ambient GG:", temp_cal , "meas:", gg_temperature, "offset to store:", gg_ext_temperature_offset)
        # gg.write_calibration_flash_data({
        #     "ext_temperature_offset": int(round(gg_ext_temperature_offset * 1e+1)),  # -> 0.1C
        # })
        # gg.exit_calibration()
        # verify GG
        sleep(2.0)
        print(gg.temperature())  # in degC


        _enable_fets()
        print("FET status: ", afe.read_fet_status())
        _disable_fets()
        print("FET status: ", afe.read_fet_status())


        print("TOS Gain stored:", afe.read_tos_gain())
        print("PACK Gain stored:", afe.read_pack_gain())
        print("LD Gain stored:", afe.read_ld_gain())

        # =================================================================================
        # === Voltage calibration ===
        # =================================================================================

        # Apply 3.0V to all cells -----------
        u_cell_a = 3.0
        u_supply = u_cell_a * num_cells
        print("Apply 2.5v (LOW) cell voltages for voltage calibration")
        print(u_supply, u_cell_a)
        psu1.configure_supply(u_supply, 0.080, 50, 1)  # wakeup AFE
        for cell_no in range(1, num_cells):
            vsim.set_cell_n_voltage(cell_no, u_cell_a)
        psu2.configure_supply(u_supply, 0.080, 50, 1)
        sleep(1.0)
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())
        print(read_voltages_from_daq())


        # GG: Calibrate Voltage DIVIDER ---------
        gg_voltage = gg.voltage()
        u_cells, u_xtras = read_voltages_from_daq()
        known_voltage = u_xtras[0]
        print("GG V meas ERROR vefore:", (known_voltage - gg_voltage), "V")
        if gg_voltage_divider_stored <= 0:
            gg_voltage_divider_stored = 5000  # default value
        new_voltage_divider = gg_voltage_divider_stored * known_voltage / gg_voltage
        new_voltage_divider_int = int(round(new_voltage_divider))
        gg.write_calibration_flash_data(data={"voltage_divider": new_voltage_divider_int})
        gg.exit_calibration()

        sleep(0.5)
        # verify
        gg_voltage = gg.voltage()
        u_cells, u_xtras = read_voltages_from_daq()
        known_voltage = u_xtras[0]  # full pack voltage
        print("GG V meas ERROR after cal:", (known_voltage - gg_voltage), "V")
        print("Voltage divider calibration done:", new_voltage_divider)


        # AFE: Calibrate Cell, TOS, PACK, LD gains ---------

        # psu1.set_output_state(0)  # disable PACK supply and enable the FETs to use the DAQ measurement for PACK and LD voltages too
        # # print(afe.discharge_test())
        # # print(afe.charge_test())
        # #print(afe.toggle_fet_enable())
        # _enable_fets()
        # print("FET status: ", afe.read_fet_status())

        cell_voltage_daq_a = [0] * 16
        pack_voltage_daq_a = 0
        cell_voltage_counts_a = [0] * 16
        tos_voltage_counts_a = 0
        pack_voltage_counts_a = 0
        ld_voltage_counts_a = 0
        u_daq, u_xtra = read_voltages_from_daq()
        u_psu1 = psu1.get_voltage()
        # transform DAQ voltages to counts positions
        for i in range(6):
            cell_voltage_daq_a[i] = u_daq[i]
        cell_voltage_daq_a[9] = u_daq[6]
        tos_voltage_daq_a = u_xtra[0]
        pack_voltage_daq_a = u_xtra[3]
        ld_voltage_daq_a = u_xtra[3]
        # get the ADC reading from the AFE
        for i in range(10):
            _u_counts, _i_counts = afe.read_dastatus()
            _cal1 = afe.read_cal1()
            for j, u in enumerate(_u_counts):
                cell_voltage_counts_a[j] += u
            tos_voltage_counts_a += _cal1["tos_adc_counts"]
            pack_voltage_counts_a += _cal1["pack_pin_adc_counts"]
            ld_voltage_counts_a += _cal1["ld_pin_adc_counts"]
        # calc average
        cell_voltage_counts_a = [n / 10 for n in cell_voltage_counts_a]
        tos_voltage_counts_a /= 10
        pack_voltage_counts_a /= 10
        ld_voltage_counts_a /= 10


        # Apply 4.2V to all cells -----------
        u_cell_b = 4.2
        u_supply = u_cell_b * num_cells
        print("Apply 4.2v (HIGH) cell voltages for voltage calibration")
        print(u_supply, u_cell_b)
        psu1.configure_supply(u_supply, 0.080, 50, 1)
        for cell_no in range(1, num_cells):
            vsim.set_cell_n_voltage(cell_no, u_cell_b)
        psu2.configure_supply(u_supply, 0.080, 50, 1)

        sleep(1.0)
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())
        print(read_voltages_from_daq())


        # GG: CC Offset Calibration GG -----------
        # (need zero current flow)

        print("CC offset")
        gg.enter_calibration()
        is_calibrating = False
        n = 5*2
        while not is_calibrating:
            # CC offset calibration
            gg.calibrate_cc_offset()
            gg.read_control_status()
            if gg._control_status["CCA"] == 1:
                is_calibrating = True
                break
            # here we can insert another calibration task while waiting
            # ...
            #
            sleep(0.5)
        if not is_calibrating:
            raise RuntimeError("CCA bit not set after starting CC offset calibration!")

        #--------------------------------------------

        cell_voltage_daq_b = [0] * 16
        pack_voltage_daq_b = 0
        cell_voltage_counts_b = [0] * 16
        tos_voltage_counts_b = 0
        pack_voltage_counts_b = 0
        ld_voltage_counts_b = 0
        u_daq, u_xtra = read_voltages_from_daq()
        u_psu1 = psu1.get_voltage()
        # transform DAQ voltages to counts positions
        for i in range(6):
            cell_voltage_daq_b[i] = u_daq[i]
        cell_voltage_daq_b[9] = u_daq[6]
        tos_voltage_daq_b = u_xtra[0]
        pack_voltage_daq_b = u_xtra[3]
        ld_voltage_daq_b = u_xtra[3]

        print(afe.read_dastatus_average(10))
        print(afe.read_cal1_average(10))

        # get the ADC reading from the AFE
        for i in range(10):
            _u_counts, _i_counts = afe.read_dastatus()
            _cal1 = afe.read_cal1()
            for j, u in enumerate(_u_counts):
                cell_voltage_counts_b[j] += u
            tos_voltage_counts_b += _cal1["tos_adc_counts"]
            pack_voltage_counts_b += _cal1["pack_pin_adc_counts"]
            ld_voltage_counts_b += _cal1["ld_pin_adc_counts"]
        # # Take the average of the 10 measurements and calculate gains
        cell_voltage_counts_b = [n / 10 for n in cell_voltage_counts_b]
        tos_voltage_counts_b /= 10
        pack_voltage_counts_b /= 10
        ld_voltage_counts_b /= 10

        # Take the average of the 10 measurements and calculate gains
        _dummy_gain = 0  # 12100
        cell_gain = [0] * len(cell_voltage_counts_a)
        for i in range(0, len(cell_gain)):
            _test_voltage_diff = (cell_voltage_daq_b[i] - cell_voltage_daq_a[i])  # in Volts
            _d = cell_voltage_counts_b[i] - cell_voltage_counts_a[i]
            print(_test_voltage_diff, _d)
            if _d == 0:
                # avoid div by zero
                cell_gain[i] = _dummy_gain
                continue
            #gain = 2**24 * (_test_voltags_diff * 1e+3) / (cell_voltage_counts_b[i] - cell_voltage_counts_a[i])
            gain = 2**24 * ((_test_voltage_diff * 1e+3) / _d)
            if gain < -32768 or gain > 32767:
                gain = _dummy_gain
            cell_gain[i] = int(round(gain))
            print("Cell ",i+1," Gain = ", cell_gain[i])


        # PSU1 and PSU2 are in safe state which avoid damadge on DUT

        print(cell_gain)
        print("FET status: ", afe.read_fet_status())

        # Calculate Cell Offset based on Cell1
        #cell_offset = ((cell_gain[0] * cell_voltage_counts_a[0]) / 2**24) - 2500
        cell_offset_float = ((cell_gain[0] * cell_voltage_counts_a[0]) / 2**24) - (cell_voltage_daq_a[0] * 1e+3)
        cell_offset = int(round(cell_offset_float))
        #if cell_offset < 0:
        #    cell_offset_x = 0xFFFF + cell_offset
        #print("Cell Offset:", cell_offset, cell_offset_x)
        print("Cell Offset:", cell_offset_float, "->", cell_offset)
        # Calculate TOS, PACK, LD Gains by using the measured voltages in cV (not mV !!)
        TOS_Gain = int(round(2**16 * (((tos_voltage_daq_b - tos_voltage_daq_a) * 1e+2) / (tos_voltage_counts_b - tos_voltage_counts_a))))
        PACK_Gain = int(round(2**16 * (((pack_voltage_daq_b - pack_voltage_daq_a) * 1e+2) / (pack_voltage_counts_b - pack_voltage_counts_a))))
        LD_Gain = int(round(2**16 * (((ld_voltage_daq_b - ld_voltage_daq_a) * 1e+2) / (ld_voltage_counts_b - ld_voltage_counts_a))))

        print("TOS new Gain", TOS_Gain)
        print("Pack new Gain", PACK_Gain)
        print("LD new Gain", LD_Gain)

        # _disable_fets()
        # print("FET status: ", afe.read_fet_status())
        # psu1.set_output_state(1)
        # sleep(0.5)

        # write voltage calibration into RAM
        afe.enter_config_update_mode()

        afe.write_cell_offset(cell_offset)
        # Cell Voltage Gains
        afe.write_cell_gain(cell_gain)
        # PACK, LD, TOS Gains
        afe.write_pack_gain(PACK_Gain)
        afe.write_ld_gain(LD_Gain)
        afe.write_tos_gain(TOS_Gain)

        afe.exit_config_update_mode()

        # -------------------------------------------------------------
        # CC offset calibration: wait until CCA cleared
        x = False
        n = 60*2
        while n:
            gg.read_control_status()
            if gg._control_status["CCA"] == 0:
                break
            # here we can insert another calibration task while waiting
            # ...
            #if not x:
            #    print("Erase FLASH:", ap.erase_flash())
            #    x = True
            # ...
            sleep(0.5)
            n -= 1
        if n == 0:
            raise RuntimeError("CCA bit not cleared after CC offset calibration!")
        gg.cc_offset_save()
        gg.exit_calibration()
        sleep(0.1)
        #--------------------------------------------------------------


        # recheck voltage measurement
        print("Recheck cell voltages after voltage calibration:")
        sleep(1.0)
        print("AFE: TOS Gain stored:", afe.read_tos_gain())
        print("AFE: PACK Gain stored:", afe.read_pack_gain())
        print("AFE: LD Gain stored:", afe.read_ld_gain())
        u_recheck = afe.read_cell_voltages()
        for i, v in enumerate(u_recheck):
            print(f"AFE: Cell {i+1}: {round(v, 3)}V")
        print("AFE: TOS:", afe.read_tos_voltage())
        print("AFE: PACK:", afe.read_pack_voltage())
        print("AFE: LD:", afe.read_ld_voltage())
        print(read_voltages_from_daq())

        print("GG: Voltage", gg.voltage())

        # =====================================================================================
        # === Current calibration ===
        # =====================================================================================



        # -----------------------------------------------------------------
        # GG: board offset --
        print("Board offset")
        gg.enter_calibration()
        is_calibrating = False
        n = 5*2
        while not is_calibrating:
            # CC offset calibration
            gg.calibrate_board_offset()
            gg.read_control_status()
            if gg._control_status["CCA"] == 1 and gg._control_status["BCA"] == 1:
                is_calibrating = True
                break
            # here we can insert another calibration task while waiting
            # ...
            sleep(0.5)
        if not is_calibrating:
            raise RuntimeError("CCA bit not set after starting board offset calibration!")

        #-------------------------------------------------------------


        # Apply a known current I_CAL of 0mA
        # psu1 and psu2 already in mode that no current is flowing
        u_cell = 3.2
        u_supply = u_cell * num_cells
        i_pack = 0.0
        print("Apply 0A discharge current")
        print(u_supply, u_cell, i_pack)
        print("FET status: ", afe.read_fet_status())
        psu1.configure_supply(u_supply, 0.080, 50, 1)
        for cell_no in range(1, num_cells):
            vsim.set_cell_n_voltage(cell_no, u_cell)
        psu2.configure_supply(u_supply, 0.080, 50, 1)
        sleep(1.0)
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())

        value = 0
        for i in range(10):
            cc = afe.read_cal1()
            value += cc["cc2_counts"]
            sleep(0.1)
        print(cc)

        print("AFE stored board offset:", afe.read_board_offset())
        _offset_samples = afe.read_coulomb_counter_offset_sample()
        print("OFFSET Samples:", _offset_samples)
        _offset_samples = 1
        board_offset = _offset_samples * int(round(value / 10))
        #board_offset = -(value & 0x8000) | (value & 0x7fff)
        if board_offset < -32768 or board_offset > 32767:
            print(f"Board_offset out of boundaries -> cannot calibrate current: {board_offset}")
            may_calibrate_current = False
        else:
            may_calibrate_current = True
        print("Board offset", board_offset)
        if may_calibrate_current:
            afe.enter_config_update_mode()
            afe.write_board_offset(board_offset)
            afe.exit_config_update_mode()

        # Apply 1A discharge current through sense resistor
        print("FET status: ", afe.read_fet_status())
        psu1.set_output_state(0)
        _enable_fets()
        print("FET status: ", afe.read_fet_status())
        #print(afe.discharge_test())
        #print(afe.charge_test())
        #print("FET status: ", afe.read_fet_status())


        #------------------------------------------------------------------
        # GG: wait until BCA cleared
        x = False
        n = 60*2
        while n:
            cs = gg.read_control_status()
            if cs["BCA"] == 0:
                break
            # here we can insert another calibration task while waiting
            # ...
            # if not x:
            #     print("Program FLASH:", ap.program_flash())
            #     x = True
            # ...
            sleep(0.5)
            n -= 1
        if n == 0:
            raise RuntimeError("CCA bit not cleared after board offset calibration!")
        gg.cc_offset_save()
        gg.exit_calibration()
        #--------------------------------------------------------------


        i_pack_a = 1.0
        print(f"Apply {i_pack_a}A discharge current")
        p_pack_a = (u_supply * i_pack_a)
        print(u_supply, u_cell, i_pack_a, p_pack_a)
        #psu1.set_output_state(0)
        psu1.configure_sink(-i_pack_a, None, -(i_pack_a*1.05), u_supply, -(p_pack_a * 1.05), 0)
        psu2.configure_supply(u_supply, i_pack_a*1.25, (p_pack_a * 1.10), 1)
        for cell_no in range(1, num_cells):
            vsim.set_cell_n_voltage(cell_no, u_cell)
        sleep(0.1)
        _enable_fets()
        print("FET status: ", afe.read_fet_status())
        psu1.set_output_state(1)
        sleep(0.5)
        i_psu_a = psu1.get_current()
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())
        #sleep(2.0)
        cc2_current_a = afe.read_cc2_current()
        print("PSU1 current:", i_psu_a)
        print("AFE CC2 current:", cc2_current_a)
        # check if we have 1A

        # value = 0
        # for i in range(10):
        #     cc = afe.read_cal1()
        #     value += cc["cc2_counts"]
        #     sleep(0.1)
        # print("CC a:", cc, value)
        # cc_counts_a = int(round(value / 10))
        # #cc_counts_a = -(value & 0x8000) | (value & 0x7fff)
        # print(cc_counts_a)

        # Apply HIGH discharge current through sense resistor
        i_pack_b = 10.0
        print(f"Apply {i_pack_b}A discharge current")
        p_pack_b = (u_supply * i_pack_b)
        print(u_supply, u_cell, i_pack_b, p_pack_b)
        psu2.configure_supply(u_supply, i_pack_b*1.25, p_pack_b * 1.10, 1)
        #psu1.configure_cc_mode(-1.000, None, 22.09, 10.0, -60, 1)
        psu1.configure_sink(-i_pack_b, None, -(i_pack_b*1.05), u_supply, -(p_pack_b * 1.05), 1)
        sleep(0.5)
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())
        i_psu_b = psu1.get_current()
        sleep(2.0)
        cc2_current_b = afe.read_cc2_current()
        print("PSU1 current:", i_psu_b)
        print("AFE CC2 current:", cc2_current_b)
        value = 0
        for i in range(10):
            cc = afe.read_cal1()
            value += cc["cc2_counts"]
            sleep(0.1)
        print("CC b:", cc, value)
        cc_counts_b = int(round(value / 10))
        #cc_counts_b = -(value & 0x8000) | (value & 0x7fff)
        print(cc_counts_b)


        # -----------------------------------------------------------------
        # GG: bq34Z100 calculation of CC Gain and Capacity Gain
        gg.enter_calibration()
        gg_current = gg.current()
        if (gg_current > -0.1) and (gg_current < 0.1):
            print("No current flow - skip CC Gain calibration")
        else:
            gg_cc_gain = gg_cc_gain_stored * i_psu_b / gg_current * 1  # * 1 Ohm
            gg_cc_delta = gg_cc_gain * 1193046.0  # magic constant
            print("New CC Gain:", gg_cc_gain)
            print("New CC Delta:", gg_cc_delta)
            gg.write_calibration_flash_data(data={"cc_gain": gg_cc_gain, "cc_delta": gg_cc_delta})
            print("CC Gain calibration done:", gg_cc_gain)
            sleep(0.1)
        gg.exit_calibration()
        #------------------------------------------------------------------

        #
        # set PSU1 and PSU2 to safe state avoiding damadge on DUT
        #
        psu1.set_output_state(0)  # SINK OFF
        psu1.configure_supply(u_supply, 0.080, 50, 0)  # PACK supply safe state
        psu2.configure_supply(u_supply, 0.080, 50, 1)  # Cell Stack SAFE STATE
        _disable_fets()
        print("FET status: ", afe.read_fet_status())
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())

        #if (cc_counts_a == cc_counts_b) or (cc_counts_a == 0) or (cc_counts_b == 0):
        if (cc_counts_b == 0):
            raise ValueError(f"Current calibration results will cause div by zero error: {cc_counts_b}")

        stored_cc_gain = afe.read_cc_gain()
        stored_capacity_gain = afe.read_capacity_gain()
        print("AFE stored CC Gain:", stored_cc_gain)
        print("AFE stored Cap Gain:", stored_capacity_gain)

        #current_diff = (i_psu_b - i_psu_a)  # in Amps
        #cc_counts_diff = (cc_counts_b - cc_counts_a)
        #cc2_current_diff = (cc2_current_b - cc2_current_a)
        #print("DIFFS:", current_diff, cc_counts_diff, cc2_current_diff)
        #cc_gain_float = (current_diff / cc_counts_diff) / 1e-3
        #cc_gain_float = (current_diff / cc2_current_diff) * stored_cc_gain  # alternative calculation using CC2 current directly
        cc_gain_float = (i_psu_b / cc2_current_b) * stored_cc_gain  # alternative calculation using CC2 current directly
        capacity_gain_float = 298261.6178 * cc_gain_float  # Note: constant 298261.6178 comes from TI doc

        print("AFE new CC Gain:", cc_gain_float)
        print("AFE new Cap Gain:", capacity_gain_float)

        if may_calibrate_current:
            # write calibration into RAM
            afe.enter_config_update_mode()
            # CC Offset, CC Gain, Capacity Gain
            afe.write_board_offset(board_offset)
            afe.write_cc_gain(cc_gain_float)
            afe.write_capacity_gain(capacity_gain_float)
            afe.exit_config_update_mode()

        # recheck current measurement -> repeat if necessary
        print("Recheck current measurement after current calibration:")

        u_cell = 3.6
        u_supply = u_cell * num_cells
        i_pack = 7.5
        print(f"Apply {i_pack}A discharge current")
        p_pack = (u_supply * i_pack)
        print(u_supply, u_cell, i_pack, p_pack)
        psu1.configure_sink(-i_pack, None, -(i_pack*1.05), u_supply, -(p_pack * 1.05), 0)
        psu2.configure_supply(u_supply, i_pack*1.25, p_pack * 1.10, 1)
        for cell_no in range(1, num_cells):
            vsim.set_cell_n_voltage(cell_no, u_cell)
        sleep(0.1)
        _enable_fets()
        print("FET status: ", afe.read_fet_status())
        psu1.set_output_state(1)
        sleep(0.5)
        print("PSU current:", psu2.get_current())
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())
        sleep(2.0)
        print("AFE current:", afe.read_cc2_current())
        print("AFE TOS:", afe.read_tos_voltage())
        print("AFE PACK:", afe.read_pack_voltage())
        print("AFE LD:", afe.read_ld_voltage())

        # GG test also
        print("GG voltage:", gg.voltage())
        print("GG current:", gg.current())
        print("GG temperature:", gg.temperature())


        psu1.set_output_state(0)  # SINK OFF
        psu1.configure_supply(u_supply, 0.080, 50, 0)  # PACK supply safe state
        psu2.configure_supply(u_supply, 0.080, 50, 1)  # Cell Stack SAFE STATE
        _disable_fets()
        print("FET status: ", afe.read_fet_status())
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())


        # === COV/CUV calibration ===
        # Apply the desired value for the cell over-voltage threshold to device cell inputs.
        # Calibration will use the voltage applied to the top cell of the device.
        # For example, Apply 4350mV: measure cells 1-6 voltage, then set psu2 to this +4.350v
        #
        # psu2... vsim...
        #afe.enter_config_update_mode()
        #afe.calibrate_cell_over_voltage()
        #afe.exit_config_update_mode()


        # apply desired CUV voltage value to device cell inputs
        # Apply the desired value for the cell under-voltage threshold to device cell inputs.
        # Calibration will use the voltage applied to the top cell of the device.
        # For example, Apply 2400mV: measure cells 1-6 voltage, then set psu2 to this +2.4v


        # psu2... vsim...
        #afe.enter_config_update_mode()
        #afe.calibrate_cell_under_voltage()
        #afe.exit_config_update_mode()

        # # === write all calibration into RAM ===
        # afe.enter_config_update_mode()
        # # Cell Voltage Gains
        # afe.write_cell_gain(cell_gain)
        # # PACK, LD, TOS Gains
        # afe.write_pack_gain(PACK_Gain)
        # afe.write_ld_gain(LD_Gain)
        # afe.write_tos_gain(TOS_Gain)
        # # CC Offset, CC Gain, Capacity Gain
        # afe.write_board_offset(board_offset)
        # afe.write_cc_gain(cc_gain_float)
        # afe.write_capacity_gain(capacity_gain)
        # # Temperature offsets
        # afe.write_temperature_calibration_offsets(temp_offsets)
        # afe.exit_config_update_mode()


            #--------------------------------------------------------------------------------------
        # MOSFET Test

        # Apply 3.0V to all cells -----------
        u_cell = 3.6
        u_supply = u_cell * num_cells
        print(f"Apply {u_cell} cell voltages for MOSFET test")
        print(u_supply, u_cell)
        psu1.configure_sink(-0.040, 1000.0, -0.050, u_supply, -5.0, 0)
        for cell_no in range(1, num_cells):
            vsim.set_cell_n_voltage(cell_no, u_cell)
        psu2.configure_supply(u_supply, 0.080, 50, 1)
        sleep(1.0)
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())
        print(read_voltages_from_daq())
        _disable_fets()
        print("FET status: ", afe.read_fet_status())
        print("Measure PSU1 (should be 0)", psu1.get_all_measurements())  # should be 0
        psu1.set_output_state(1)  # sink ON
        afe.discharge_test()  # discharge FET ON
        print("FET status: ", afe.read_fet_status())
        sleep(2.0)
        print("Measure PSU1 (should show current)", psu1.get_all_measurements())
        afe.charge_test()
        print("FET status: ", afe.read_fet_status())
        sleep(2.0)
        print("Measure PSU1 (voltage should be equal)", psu1.get_all_measurements())
        afe.discharge_test()  # OFF
        print("FET status: ", afe.read_fet_status())
        sleep(1.0)
        print("Measure PSU1 (should be 0)", psu1.get_all_measurements())  # should be 0
        psu1.set_output_state(0)  # sink OFF
        print("FET status: ", afe.read_fet_status())


        #--------------------------------------------------------------------------------------
        # Test FUSE pin

        #daq.get_VDC(16)  # FUSE pin



        #--------------------------------------------------------------------------------------



        # === write to OTP ===

        u_supply = 11.0  # target stack voltage for OTP programming
        u_cell = round(u_supply / num_cells, 2)
        print(f"Apply {u_supply}v stack voltage for OTP programming")
        print(u_supply, u_cell)
        psu1.configure_supply(u_supply, 0.080, 50, 1)
        for cell_no in range(1, num_cells):
            vsim.set_cell_n_voltage(cell_no, u_cell)
        psu2.configure_supply(u_supply, 0.080, 50, 1)
        _disable_fets()
        print("FET status: ", afe.read_fet_status())
        sleep(1.0)
        print("Measure PSU1", psu1.get_all_measurements())
        print("Measure PSU2", psu2.get_all_measurements())

        afe.enter_config_update_mode()
        results, data_fail_addr = afe.read_otp_wr_check()
        if results == 0x80:
            # all ok -> write to OTP
            print(f"AFE ready: 0x{results:02X} -> write to OTP")
            afe.write_otp()
            sleep(0.5)
            afe.exit_config_update_mode()
        else:
            afe.exit_config_update_mode()
            raise RuntimeError(f"OTP write check failed at address 0x{data_fail_addr:04X} with result 0x{results:02X}")


        # NOTE: The µ-controller interacts with AFE and GG so program it
        # after all things are set for AFE and GG.
        #------------------------------------------------------------------
        cartridge.switch_some_io(7, 0)  # enable microcontroller
        print("Program FLASH:", ap.program_flash())
        #------------------------------------------------------------------
        # sleep(1.0)
        # cartridge.select_bus_to_micro("can")
        # can.send(0x11, (1,2,3,4,5,6,7,8))
        # print(can.receive(0x11))
        # cartridge.select_bus_to_micro("i2c")
        # sleep(0.5)
        cartridge.switch_some_io(7, 1)  # diable microcontroller

    

    except Exception as ex:
        print_exception(type(ex), ex, ex.__traceback__)

    # reset testrack in save state

    cartridge.reset_mux()
    vsim.power_down_all_cell_channels()

    psu1.set_output_state(0)
    psu2.set_output_state(0)

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    # print("expected: 150")
    # _test = [113, 0, 118, 0, 74, 0, 152, 247, 255, 255, 220, 255, 73, 0, 222, 247, 255, 255, 186, 165, 73, 0, 207, 248, 255, 255, 107, 60, 73, 0, 69, 249, 255, 255]
    # _test2 = bytearray(b'v\x00J\x00\x98\xf7\xff\xff\xdc\xffI\x00\xde\xf7\xff\xff\xba\xa5I\x00\xcf\xf8\xff\xffk<I\x00E\xf9\xff\xff')
    # _test3 = bytearray([113, 0]) + bytearray(b'v\x00J\x00\x98\xf7\xff\xff\xdc\xffI\x00\xde\xf7\xff\xff\xba\xa5I\x00\xcf\xf8\xff\xffk<I\x00E\xf9\xff\xff')
    # print(sum(_test) & 0xFF)
    # print(~sum(_test) & 0xFF)
    # print(sum(_test2) & 0xff)
    # print(~sum(_test2) & 0xff)
    # print(sum(_test3) & 0xff)
    # print(~sum(_test3) & 0xff)
    # #exit()

    LINE_NETWORK = "172.21.101"  # HOM Warehouse
    #LINE_NETWORK = "172.25.101"  # VN line 1
    #LINE_NETWORK = "172.25.102"  # VN line 2
    #LINE_NETWORK = "172.25.103"  # VN line 3


    SOCKET = 0  # 0, 1 or 2
    # following assumes own IF-OLIMEX breakout adapter
    if SOCKET == 0:
        psu1 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=1)  # socket 0 / share
        psu2 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=2)  # socket 0 / share
    if SOCKET == 1:
        psu1 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=3)  # socket 1 / share
        psu2 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=4)  # socket 1 / share
    if SOCKET == 2:
        psu1 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=5)  # socket 2 / share
        psu2 = M3400(f"{LINE_NETWORK}.37:30000", dev_channel=6)  # socket 2 / share
    psu1.set_output_state(0)
    psu2.set_output_state(0)

    _filestore_path = Path(__file__).parent / "../../Battery-PCBA-Test/filestore/"

    if SOCKET == 0:
        i2cbus = I2CPort(f"{LINE_NETWORK}.30:2101")  # socket 0
        can = CANBus(f"{LINE_NETWORK}.30:3303")  # socket 0
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.31:2000")  # socket 0
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.31:3000")  # PCBA test, socket 0
        ap = AlgocraftProgrammer(f"{LINE_NETWORK}.38:2101", _filestore_path)  # socket 0
    if SOCKET == 1:
        i2cbus = I2CPort(f"{LINE_NETWORK}.32:2101")  # socket 1
        can = CANBus(f"{LINE_NETWORK}.32:3303")  # socket 1
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.33:2000")  # socket 1
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.33:3000")  # PCBA test, socket 1
        ap = AlgocraftProgrammer(f"{LINE_NETWORK}.39:2101", _filestore_path)  # socket 1
    if SOCKET == 2:
        i2cbus = I2CPort(f"{LINE_NETWORK}.34:2101")  # socket 2
        can = CANBus(f"{LINE_NETWORK}.34:3303")  # socket 2
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.35:2000")  # socket 2
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.35:3000")  # PCBA test, socket 2
        ap = AlgocraftProgrammer(f"{LINE_NETWORK}.29:2101", _filestore_path)  # socket 2


    print("Change clock frequency and timeout - RRC: ",
          str(i2cbus.i2c_change_clock_frequency(400000, timeout_ms=20)))
    print("MASTER:", i2cbus.i2c_bus_scan())

    mux = BusMux(i2cbus, address=0x77)
    vsim = CellVoltageSimulation(I2CMuxedBus(i2cbus, mux, 4))
    vsim.initialize()
    vsim.power_down_all_cell_channels()

    sleep(0.5)

    for c in range(8,0,-1):
        mux.setChannel(c)
        print("CH:", c, i2cbus.i2c_bus_scan())

    dutcom = I2CMuxedBus(i2cbus, mux, 2)  # i2c to the DUT
    #mux_on_cartridge = BusMux(dutcom, address=0x70)  # this is the MUX on the DUT board
    # print("MUX ON CARTRIDGE:")
    # for c in range(1,9):
    #     mux_on_cartridge.setChannel(c)
    #     print("CH:", c, dutcom.i2c_bus_scan())

    cart = CartridgePETA(dutcom)
    test_cartridge_only(cart)

    #cart.select_bus_to_micro("can")
    #can.send(0x11, (1,2,3,4,5,6,7,8))
    #print(can.receive(0x11))

    # double MUX'd
    # dut_micro = BusMaster(I2CMuxedBus(dutcom, mux_on_cartridge, 1), retry_limit=7, verify_rounds=3, pause_us=50)
    # dut_gasgauge = BQ34Z100(I2CMuxedBus(dutcom, mux_on_cartridge, 2))
    # dut_afe = BQ76942(I2CMuxedBus(dutcom, mux_on_cartridge, 2))
    # dut_gpio = TCAL6416(I2CMuxedBus(dutcom, mux_on_cartridge, 8), i2c_address_7bit=0x20)
    # # testdummy for double, transparent MUX
    # print(dut_micro.i2c.i2c_bus_scan())
    # print(dut_gasgauge.bus.i2c_bus_scan())
    # print(dut_afe.bus.i2c_bus_scan())
    # print(dut_gpio.bus.i2c_bus_scan())

    # which EEPROM type do we need to implement ?

    calib = CalibrationStorage(I2CMuxedBus(i2cbus, mux, 1))
    print("Inventory:", calib.load_inventory_number())

    gpio = RelayBoard4Relay4GPIO(I2CMuxedBus(i2cbus, mux, 3))

    #sleep(0.5)

    if SOCKET == 0:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=1)  # socket 0
    if SOCKET == 1:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=2)  # socket 1
    if SOCKET == 2:
        daq = DAQ970A(f"{LINE_NETWORK}.36:5025", card_slot=3)  # socket 2

    print(daq.ident())
    print(daq.read_error_status())
    #print(daq.selftest())

    # .... do some tests here ....
    
    rack_test(cart, gpio, vsim, calib, feasa, psu1, psu2, daq, can, ap)

    i2cbus.close()

# END OF FILE
