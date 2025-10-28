"""
PETA Design PCBA Adapter.
"""

#import unittest
from traceback import print_exception
from re import A
from typing import Never, Tuple
from time import sleep, perf_counter
from pathlib import Path
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

def rack_test(cartridge: CartridgePETA, gpio: RelayBoard4Relay4GPIO,
              vsim: CellVoltageSimulation, calib: CalibrationStorage,
              feasa: FEASA_CH9121,
              psu1: M3400, psu2: M3400,
              daq: DAQ970A) -> None:
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

    #cartridge.switch_some_io(7, 0)  # enable microcontroller
    cartridge.switch_some_io(7, 1)  # disable microcontroller

    # push button
    gpio.set_gpio_n_as_output(6)  # pin 6 as output
    #gpio.set_gpio_n_low(6)  # push button enabled
    gpio.set_gpio_n_high(6)
    #gpio.set_gpio_n_low(6)

    #cartridge.select_bus_to_micro("i2c")
    print("BACKYARD:", cartridge.backyard_bus.i2c_bus_scan())
    print("MICRO:", cartridge.bus_to_mirco.i2c_bus_scan())
    #for n in range(1,9):
    #    print(cartridge.get_muxed_i2c_bus_for(n).i2c_bus_scan())


    def read_voltages_from_daq() -> Tuple[Tuple[Never] | Tuple[float] | Tuple[float]]:
        u_cell = ()
        for channel in [11, 12, 14, 10, 18, 19, 5]:
            u_cell += (daq.get_VDC(channel),)
        u_xtra = ()
        u_xtra += (daq.get_VDC(15),)  # full pack voltage
        u_xtra += (daq.get_VDC(8),)   # should be +3.3v
        u_xtra += (daq.get_VDC(9),)   # should be +1.8v
        return u_cell, u_xtra

    print("Read voltages from DAQ:")
    u_cells, u_xtras = read_voltages_from_daq()
    print("Cells: ", u_cells)
    print("Pack: ", u_xtras[0])
    print("+3.3v VCC: ", u_xtras[1])
    print("+1.8v VCC: ", u_xtras[2])

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

        if 1:
            afe = BQ76942(cartridge.backyard_bus, slvAddress=0x08, pec=True, retry_limit=5)
            #afe.disable_checksum()

            print(afe.read_control_status())
            print(afe.read_battery_status())

            print(afe.read_safety_status(hexi=True))
            print(afe.read_dastatus(hexi=True))

            afe.read_temperature_calibration_offsets() # stores them into afe.temperature_calibration_offsets

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


            # === calibrate temperature ===
            # 1) apply known temperature TEMP(cal)
            temp_cal = 21.4
            # 2) measure the temperatures
            t_meas = [0.0] * 10
            for n in range(5):
                t0, _ = afe.read_temperatures()
                for i in range(len(t_meas)):
                    t_meas[i] += t0[i]
                sleep(0.050)
            t_meas = [t/5 for t in t_meas]
            # 3) calculate the offsets
            #temp_offsets = [round((((temp_cal - t) + KELVIN_ZERO_DEGC) * 10), 0) for t in t_meas]
            temp_offsets = [(temp_cal - t)  for t in t_meas]
            print(temp_offsets)

            # write the temperature calibration values
            afe.read_temperature_calibration_offsets() # stores them into afe.temperature_calibration_offsets
            afe.enter_config_update_mode()
            afe.write_temperature_calibration_offsets(temp_offsets)
            afe.exit_config_update_mode()

            # re-check temperature measurement (repeat the calibration if not successful!)
            print(afe.read_temperature_calibration_offsets(hexi=True))
            print(afe.read_temperatures())


            # This step will enable the FETs to calibrate Top-of-Stack, PACK, and LD voltages.
            # Make sure FETs are closed for PACK and LD measurements
            afe.disable_sleepmode()  # Sleep Disable 0x009A to prevent CHG FET from opening
            #psu1.set_output_state(0)

            print(afe.read_manufacturing_status())
            print(afe.read_alarm_status())
            #print(afe.all_fets_on())
            #print(afe.discharge_test())
            #print(afe.charge_test())
            print(afe.read_manufacturing_status())
            print(afe.read_alarm_status())
            print("FET status: ", afe.read_fet_status())

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

            _enable_fets()
            print("FET status: ", afe.read_fet_status())
            _disable_fets()
            print("FET status: ", afe.read_fet_status())


            print("TOS Gain stored:", afe.read_tos_gain())
            print("PACK Gain stored:", afe.read_pack_gain())
            print("LD Gain stored:", afe.read_ld_gain())

            if 1:
                # === Voltage calibration ===
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
                pack_voltage_daq_a = u_psu1
                ld_voltage_daq_a = u_xtra[0]
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
                pack_voltage_daq_b = u_psu1
                ld_voltage_daq_b = u_xtra[0]
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


                # recheck voltage measurement
                print("Recheck cell voltages after voltage calibration:")
                sleep(1.0)
                print("TOS Gain stored:", afe.read_tos_gain())
                print("PACK Gain stored:", afe.read_pack_gain())
                print("LD Gain stored:", afe.read_ld_gain())
                u_recheck = afe.read_cell_voltages()
                for i, v in enumerate(u_recheck):
                    print(f"Cell {i+1}: {round(v, 3)}V")
                print("TOS:", afe.read_tos_voltage())
                print("PACK:", afe.read_pack_voltage())
                print("LD:", afe.read_ld_voltage())
                print(read_voltages_from_daq())

            # === Current calibration ===

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
                x = cc["cc2_counts"]
                value += x
                sleep(0.1)
            print(cc)
            value = 64 * int(round(value / 10))
            board_offset = -(value & 0x8000) | (value & 0x7fff)
            #if board_offset < 0:
            #    board_offset = (0xFFFF + board_offset) & 0xFFFF
            print("Board offset", value)
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
            print("Measure PSU1", psu1.get_all_measurements())
            print("Measure PSU2", psu2.get_all_measurements())
            sleep(2.0)

            value = 0
            for i in range(10):
                cc = afe.read_cal1()
                value += cc["cc2_counts"]
                sleep(0.1)
            print(cc)
            value = int(round(value / 10))
            cc_counts_a = -(value & 0x8000) | (value & 0x7fff)
            print(cc_counts_a)

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
            sleep(2.0)

            value = 0
            for i in range(10):
                cc = afe.read_cal1()
                value += cc["tos_adc_counts"]
                sleep(0.1)
            print(cc)
            value = int(round(value / 10))
            cc_counts_b = -(value & 0x8000) | (value & 0x7fff)
            print(cc_counts_b)



            # bq34Z100 calculation of CC Gain and Capacity Gain




            #
            # set PSU1 and PSU2 to safe state avoiding damadge on DUT
            #
            psu1.set_output_state(0)  # SINK OFF
            psu2.configure_supply(u_supply, 0.080, 50, 1)  # SUPPLY SAFE STATE
            _disable_fets()
            print("FET status: ", afe.read_fet_status())
            print("Measure PSU1", psu1.get_all_measurements())
            print("Measure PSU2", psu2.get_all_measurements())

            if (cc_counts_a == cc_counts_b) or (cc_counts_a == 0) or (cc_counts_b == 0):
                raise ValueError(f"Current calibration results will cause div by zero error: {cc_counts_a}, {cc_counts_b}")

            current_diff = (i_pack_b - i_pack_a)  # in Amps
            cc_gain_float = current_diff * 1e+3 / (cc_counts_b - cc_counts_a)
            capacity_gain, cap_gain_hex = afe.dec2flash(298261.6178 * cc_gain_float)  # Note: constant 298261.6178 comes from TI doc

            # write calibration into RAM
            afe.enter_config_update_mode()
            # CC Offset, CC Gain, Capacity Gain
            afe.write_board_offset(board_offset)
            afe.write_cc_gain(cc_gain_float)
            afe.write_capacity_gain(capacity_gain)
            afe.exit_config_update_mode()

            # recheck current measurement -> repeat if necessary



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

        # ---------------------------------------------------------------------------------------------
        else:
        # ---------------------------------------------------------------------------------------------

            gg = BQ34Z100(BusMaster(cartridge.backyard_bus, retry_limit=5), slvAddress=0x55, pec=False)
            print(gg.get_voltage_scale())
            print(gg.get_current_scale())
            print(gg.get_energy_scale())
            print(gg.voltage())
            print(gg.temperature())

            if 0:
                # write FLASH
                ff2 = BQStudioFileFlexFlasher(gg, base_path / "3412185B-02_A_RRC3570-4_BMS-Files.bq.fs" )
                ff2.validate_file()
                tic = perf_counter()
                ff2.program_fw_file()
                toc = perf_counter()
                print(f"DONE in {toc - tic:0.4f} seconds.")

            cs = gg.read_control_status()
            if cs["CALEN"] == 0:
                gg.toggle_cal_enable()
                sleep(0.1)

            gg.enter_calibration()

            print("CC offset")
            t0 = perf_counter()
            is_calibrating = False
            n = 5*2
            while not is_calibrating:
                # CC offset calibration
                gg.calibrate_cc_offset()
                cs = gg.read_control_status()
                if cs["CCA"] == 1:
                    is_calibrating = True
                    break
                sleep(0.5)
            if not is_calibrating:
                raise RuntimeError("CCA bit not set after starting CC offset calibration!")
            # wait until CCA cleared
            n = 60*2
            while n:
                cs = gg.read_control_status()
                if cs["CCA"] == 0:
                    break
                sleep(0.5)
                n -= 1
            if n == 0:
                raise RuntimeError("CCA bit not cleared after CC offset calibration!")
            gg.cc_offset_save()
            print("Needed time:", perf_counter()-t0)
            sleep(0.1)

            # -- board offset --
            print("Board offset")
            t0 = perf_counter()
            is_calibrating = False
            n = 5*2
            while not is_calibrating:
                # CC offset calibration
                gg.calibrate_board_offset()
                cs = gg.read_control_status()
                if cs["CCA"] == 1 and cs["BCA"] == 1:
                    is_calibrating = True
                    break
                sleep(0.5)
            if not is_calibrating:
                raise RuntimeError("CCA bit not set after starting board offset calibration!")

            # wait until BCA cleared
            n = 60*2
            while n:
                cs = gg.read_control_status()
                if cs["BCA"] == 0:
                    break
                sleep(0.5)
                n -= 1
            if n == 0:
                raise RuntimeError("CCA bit not cleared after board offset calibration!")
            gg.cc_offset_save()
            print("Needed time:", perf_counter()-t0)
            sleep(0.1)



            gg.exit_calibration()
            print("Done.")

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

    print("expected: 150")
    _test = [113, 0, 118, 0, 74, 0, 152, 247, 255, 255, 220, 255, 73, 0, 222, 247, 255, 255, 186, 165, 73, 0, 207, 248, 255, 255, 107, 60, 73, 0, 69, 249, 255, 255]
    _test2 = bytearray(b'v\x00J\x00\x98\xf7\xff\xff\xdc\xffI\x00\xde\xf7\xff\xff\xba\xa5I\x00\xcf\xf8\xff\xffk<I\x00E\xf9\xff\xff')
    _test3 = bytearray([113, 0]) + bytearray(b'v\x00J\x00\x98\xf7\xff\xff\xdc\xffI\x00\xde\xf7\xff\xff\xba\xa5I\x00\xcf\xf8\xff\xffk<I\x00E\xf9\xff\xff')
    print(sum(_test) & 0xFF)
    print(~sum(_test) & 0xFF)
    print(sum(_test2) & 0xff)
    print(~sum(_test2) & 0xff)
    print(sum(_test3) & 0xff)
    print(~sum(_test3) & 0xff)
    #exit()

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

    if SOCKET == 0:
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.31:2000")  # socket 0
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.30:3000")  # PCBA test, socket 0
        i2cbus = I2CPort(f"{LINE_NETWORK}.30:2101")  # socket 0
        #can = CANBus(f"{LINE_NETWORK}.30:3303")  # socket 0
    if SOCKET == 1:
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.33:2000")  # socket 1
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.32:3000")  # PCBA test, socket 1
        i2cbus = I2CPort(f"{LINE_NETWORK}.32:2101")  # socket 1
        can = CANBus(f"{LINE_NETWORK}.32:3303")  # socket 1
    if SOCKET == 2:
        scanner = create_barcode_scanner(f"{LINE_NETWORK}.35:2000")  # socket 2
        feasa = FEASA_CH9121(f"{LINE_NETWORK}.34:3000")  # PCBA test, socket 2
        i2cbus = I2CPort(f"{LINE_NETWORK}.34:2101")  # socket 2
        can = CANBus(f"{LINE_NETWORK}.34:3303")  # socket 2



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

    # .... do some tests here ....

    rack_test(cart, gpio, vsim, calib, feasa, psu1, psu2, daq)

    i2cbus.close()

# END OF FILE
