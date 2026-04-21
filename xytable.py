
"""
Contains the drivers for stepper motor controller MOC-01/MOC-02 from Optics Focus Instruments Co., Ltd.
"""

from time import sleep
from math import e
from typing import Tuple, List
from enum import Enum

from rrc.eth2serial import Eth2SerialDevice
# from rrc.gcode.machine import Machine 
from rrc.modbus.aws3 import AWS3Modbus
from rrc.serialport import SerialComportDevice, SerialComportDevicePermanentlyOpen
from adam6xxx import ADAM6052

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 2

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #


#--------------------------------------------------------------------------------------------------


class BaseOfStage():

    def __init__(self,
            name: str,  # either 'X' or 'Y' or 'Z' or 'R' or 'T1' or 'T2'
            step_angle: float, # from stage motor's data sheet: either 0.9 or 1.8
        ) -> None:

        _AXIS_NAME_TO_CONTROLLER_NAME = {
            'X': 'X',
            'Y': 'Y',
            'Z': 'Z',
            'R': 'r',
            'T1': 't',
            'T2': 'T',
        }
        n = name.upper()
        assert n in _AXIS_NAME_TO_CONTROLLER_NAME.keys(), f"Stage name '{n}' is not valid. Must be one of {_AXIS_NAME_TO_CONTROLLER_NAME.keys()}"
        self.name = n
        self.axis_name = _AXIS_NAME_TO_CONTROLLER_NAME[n]
        assert step_angle in (0.9, 1.8), "Step angle must be either 0.9 or 1.8 degrees."
        self.step_angle = step_angle
        self.position = None

    #----------------------------------------------------------------------------------------------


    def home_command(self) -> Tuple[str, str]:
        """Get the command string to reset/home the stage position so that the absolute position is defined as 0."""
        return f"H{self.axis_name}0", f"Resetting stage '{self.name}'..."  # HOME command of stage to motion controller


    #----------------------------------------------------------------------------------------------


    def read_position_command(self) -> Tuple[str, str]:
        """Get the command string to get the current position on the linear stage.

        Returns:
            Tuple[str, str]: command to motion controller and log message.
        """

        return f"?{self.axis_name}", f'Reading {self.name}-position'  # command to motion controller


    #----------------------------------------------------------------------------------------------

    def convert_stage_speed_to_velocity(self, speed_value: int) -> float:
        # virtual method to be overridden in child classes
        pass

    def convert_velocity_to_stage_speed(self, velocity_mm_s: float) -> int:
        # virtual method to be overridden in child classes
        pass

    def physical_displacement_to_motion_command(self, displacement_mm: float | int) -> Tuple[str, str]:
        #virtual method to be overridden in child classes
        pass

    def absolute_position_to_motion_command(self, new_position: float | int | str) -> Tuple[str | None, str]:
        # virtual method to be overridden in child classes
        pass

    def convert_mm_to_steps(self, mm: float | int) -> int:
        # virtual method to be overridden in child classes
        pass

    def convert_steps_to_mm(self, steps: int) -> float:
        # virtual method to be overridden in child classes
        pass


#--------------------------------------------------------------------------------------------------


class RotaryStage(BaseOfStage):

    def __init__(self,
            name: str,  # either 'X' or 'Y' or 'Z' or 'R' or 'T1' or 'T2'
            subdivision: int = 2,    # from back panel of motion controller (DIP setting): e.g. 2
            step_angle: float = 1.8, # from the side of the stage: either 0.9 or 1.8
            transmission_ratio: float = 180.0, # depending on the product
        ) -> None:

        super().__init__(name, step_angle)
        self.stage_type: str = "rotary_stage"
        self.unit: str = "degree"
        self.position = None  # current position of the stage unkonwn at start
        # calculation depending on the type of stage
        self.subdivision = subdivision
        self.transmission_ratio = transmission_ratio  # for rotation stages
        # precalculate pulse equivalent in degrees
        self.pulse_equiv = step_angle / (transmission_ratio * subdivision)  # from manufacturers manual


#--------------------------------------------------------------------------------------------------


class GoniometerStage(BaseOfStage):

    def __init__(self,
            name: str,  # either 'X' or 'Y' or 'Z' or 'R' or 'T1' or 'T2'
            step_angle: float, # from the side of the stage: either 0.9 or 1.8
            subdivision: int,  # from back of motion controller: e.g. 2
            transmission_ratio: float,
            travel_range_mm: int, # maximum stage travel range in mm; will be converted into controller steps and stored in max_position
        ) -> None:

        super().__init__(name, step_angle)
        self.stage_type = "goniometer_stage"
        self.unit = "degree"
        self.position = None  # current position of the stage unkonwn at start
        # calculation depending on the type of stage
        self.subdivision = subdivision
        self.transmission_ratio = transmission_ratio  # for rotation stages
        self.travel_range_mm = travel_range_mm
        # precalculate pulse equivalent in degrees
        self.pulse_equiv = step_angle / (transmission_ratio * subdivision)  # from manufacturers manual
        self.max_position = int(round(travel_range_mm / self.pulse_equiv))  # in controller pulse units

#--------------------------------------------------------------------------------------------------


class LabJackStage(BaseOfStage):

    def __init__(self,
            name: str,  # either 'X' or 'Y' or 'Z' or 'R' or 'T1' or 'T2'
            subdivision: int,  # from back of motion controller: e.g. 2
            step_angle: float, # from the side of the stage: either 0.9 or 1.8
            pitch_of_lead_screw: float, # in mm - from the optics focus website, e.g. 1.25
            travel_range_mm: int, # maximum stage travel range in mm; will be converted into controller steps and stored in max_position
        ) -> None:

        super().__init__(name, step_angle)
        self.stage_type = "lab_jack_stage"
        self.unit = "step"
        self.position = None  # current position of the stage unkonwn at start
        # calculation depending on the type of stage
        self.subdivision = subdivision
        self.pitch_of_lead_screw = pitch_of_lead_screw
        self.transmission_ratio = 1.0  # for lab jack stages
        self.travel_range_mm = travel_range_mm
        # precalculate pulse equivalent in mm
        self.pulse_equiv = pitch_of_lead_screw * step_angle / (360 * subdivision)  # from manufacturers manual
        self.max_position = int(round(travel_range_mm / self.pulse_equiv))  # in controller pulse units


#--------------------------------------------------------------------------------------------------

class LinearStage(BaseOfStage):

    def __init__(self,
            name: str,  # either 'X' or 'Y' or 'Z' or 'R' or 'T1' or 'T2'
            subdivision: int,  # from back of motion controller: e.g. 2
            step_angle: float, # from the side of the stage: either 0.9 or 1.8
            pitch_of_lead_screw: float,  # in mm - from the optics focus website, e.g. 1.0
            travel_range_mm: float, # maximum stage travel range in mm; will be converted into controller steps and stored in max_position
        ) -> None:

        super().__init__(name, step_angle)
        self.stage_type = "translation_stage"
        self.unit = "mm"
        self.position = None  # current position of the stage unkonwn at start
        # calculation depending on the type of stage
        self.subdivision = subdivision
        self.pitch_of_lead_screw = pitch_of_lead_screw
        self.travel_range_mm = travel_range_mm
        # precalculate pulse equivalent in mm
        self.pulse_equiv = pitch_of_lead_screw * step_angle / (360 * subdivision)  # from manufacturers manual
        self.max_position = int(round(travel_range_mm / self.pulse_equiv))  # in controller pulse units

    #----------------------------------------------------------------------------------------------

    def convert_stage_speed_to_velocity(self, speed_value: int) -> float:
        """Converts a stage speed value (0..255) into physical (mm/s)"""
        return round((speed_value + 1) * self.pulse_equiv * (22000 / 720), 2)  # convert from speed value to mm/s

    def convert_velocity_to_stage_speed(self, velocity_mm_s: float) -> int:
        """Converts a physical speed given in mm/s into a speed value recognisable by the stage (0..255)"""
        return int(round((velocity_mm_s / (22000 / 720) / self.pulse_equiv) - 1))  # convert from mm/s to speed value

    def convert_mm_to_steps(self, mm: float | int) -> int:
        """Converts a physical displacement given in mm into steps for the motion controller"""
        return int(round(mm / self.pulse_equiv))

    def convert_steps_to_mm(self, steps: int) -> float:
        """Converts a displacement given in steps into physical mm"""
        return round(steps * self.pulse_equiv, 4)


    #----------------------------------------------------------------------------------------------


    def physical_displacement_to_motion_command(self, displacement_mm: float | int) -> Tuple[str, str]:
        """Converts a positive or negative displacement (in mm) into a motion command for the stage"""

        direction = '+' if displacement_mm > 0 else '-'
        # convert from mm to steps for motioncontroller
        magnitude = self.convert_mm_to_steps(abs(displacement_mm))
        return f"{self.axis_name}{direction}{magnitude}", f"Setting {self.name}-displacement of {displacement_mm}mm"   # command for motion controller

    #----------------------------------------------------------------------------------------------


    def displacement_to_motion_command(self, displacement: int) -> Tuple[str, str]:
        """Converts a positive or negative displacement (in steps) into a motion command for the stage"""

        return f"{self.axis_name}{displacement:+}", f"Setting {self.name}-displacement of {displacement} steps"   # command for motion controller

   #----------------------------------------------------------------------------------------------


    def absolute_position_to_motion_command(self, new_position: float | int | str) -> Tuple[str | None, str]:
        """Calculates the absolute new position on the linear stage based on
        the current position and returns the displacement to reach this position.
        If the current position is unknown, Freturns None.

        Args:
            new_position (float | int | str): _description_

        Raises:
            ValueError: if new_position is an unknown string.

        Returns:
            tuple[str, str] | None: The displacement command in mm to reach the new position, or None if current position is unknown.
                Second value is a log message.
        """

        if isinstance(new_position, str):
            if new_position == 'start':
                return self.home_command()
            elif new_position == 'center':
                new_position = self.max_position / 2
            elif new_position == 'end':
                new_position = self.max_position
            else:
                raise ValueError(f"{new_position} is not a valid command for the linear stage '{self.name}'")

        if new_position > self.max_position:
            new_position = self.max_position  # limit to max position
        elif new_position <= 0:
            return self.home_command()

        if self.position is None:
            return None, "Not yet on defined position"  # need to HOME or MAX first

        displacement = int(round(new_position - self.position))
        if not displacement:
            return "", f"Already on position '{new_position}'"  # already on position
        cmd, msg = self.displacement_to_motion_command(displacement)
        return cmd, f"Setting {self.name}-position: {msg}"  # command to motion controller



    #----------------------------------------------------------------------------------------------



#--------------------------------------------------------------------------------------------------

class ParsingStage():
    """Driver for a stages that is just parsing scripts."""

    def __init__(self, resource_string: str, timeout: float = 5.0) -> None:

        if "," in resource_string:
            # serial com port which keeps the connection open all the time
            self.dev = SerialComportDevicePermanentlyOpen(resource_string, termination=("\n", "\r"), timeout=timeout)
        else:
            # socket port which needs an open connection with timeout. The first call does not set the timeout.
            self.dev = Eth2SerialDevice(resource_string, termination=("\n", "\r"), open_connection=True)
            # now the connection is open with timeout setting
            self.dev.connect_socket(timeout=timeout)


    #----------------------------------------------------------------------------------------------


    def is_connected(self) -> bool:
        #
        # this command is for all stages
        #
        cmd = "?R"
        response = self.dev.request(cmd)
        r = response.strip().split("\r")
        if (r[0] == cmd) and ("OK" in r[1]):
            return True
        else:
            return False


    #----------------------------------------------------------------------------------------------


    def parse_script(self, script: str) -> Tuple[bool, Tuple[str, str, float | str]]:
        """Parses a script containing commands .

        Args:
            script (str): Multiline string with each line containing "X_mm,Y_mm"

        Returns:
            Tuple[bool, Tuple[str, str, float | str]]: list of tuples with (command, response, value)
        """

        log = []
        # clear CR, use ; as line separator, accept line separator
        lines = script.replace("\r", "").replace(";", "\n").strip().split('\n')
        for line in lines:
            try:
                if line == "UI":
                    # wait for user input
                    pass
                elif line[0] == "W":
                    # wait
                    w = float(line[1:])
                    sleep(w / 1000.0)  # w is in ms
                    v = w
                else:
                    # send the lines to the motion controller as they come
                    response = self.dev.request(line, timeout=5.0, pause_after_write=5)
                    # the response should include the command, split by CR
                    r = response.split("\r")
                    if r[0] != line:
                        raise ValueError(f"Response '{response}' does not match command '{line}'")
                    # parse the position from the response
                    if "OK" in r[1]:
                        # command executed successfully
                        v = r[1].strip()
                    elif not 'ERR' in r[1]:
                        # got a number
                        v = float(r[1].strip())
                        # ... what should we do with it ?
                    else:
                        # ERR found -> decode error message
                        v = r[1].strip()
                        #raise ValueError(f"Stage error '{response}'")
                # collect the log of positions
                log.append((line, response, v))
            except ValueError as e:
                raise ValueError(f"Invalid line in script: '{line}'. Error: {e}")
        return log


#--------------------------------------------------------------------------------------------------

class XYLinearStage():
    """Driver for the XY table using linear stages for X and Y direction."""

    def __init__(self, X: LinearStage, Y: LinearStage, resource_string: str, timeout: float = 5.0) -> None:
        """Creates a XY linear stage device using an MOC-01/MOC-02 from Optics Focus Instruments Co., Ltd.

        Depending on the resource string, it creates either a network socket or a COM port connection to the stage.
        The Termination is set to CR for send and LF for receive direction.

        Valid resource strings:
            hostname:port, e.g. "172.25.101.43:2000" for IPv4 172.25.101.43 at port 2000
            comport,baud,linesettings, e.g."COM7,9600,8N1" for COM7 with 9600 baud and 8 bits No parity, 1 stop bit

        Args:
            config (dict): configuration dictionary for the stage:

                'subdivision': 2,  # from back of motion controller
                'step_angle': 0.9,  # from the side of the stage
                'pitch': 4,  # in mm - from the optics focus website
                'max_stage_position': 10000,

            resource_string (str): Resource connection of the XY-table.
            timeout (float): timeout for socket or serial connection.

        Returns:
            Eth2SerialDevice | SerialComportDevice: a device that can transparently being used
                by its function .request() to scan for input.

        """

        if "," in resource_string:
            ## serial port which connects only on send or receive respecting the given timeouts in the send/request call.
            #self.dev = SerialComportDevice(resource_string, termination=("\n", "\r"))
            # serial com port which keeps the connection open all the time
            self.dev = SerialComportDevicePermanentlyOpen(resource_string, termination=("\r","\n"), timeout=timeout)
        else:
            # socket port which needs an open connection with timeout. The first call does not set the timeout.
            self.dev = Eth2SerialDevice(resource_string, termination=("\r","\n"), open_connection=True)
            # now the connection is open with timeout setting
            self.dev.connect_socket(timeout=timeout)

        # create a tuple of stages
        self.stages = (X, Y)
        self.pulse_period = 30 / (0 + 1)  # assuming the initial speed is 0  -> pulses/ms
        # -> _duration = abs(displacement) / self.pulse_period   # in ms


    #----------------------------------------------------------------------------------------------

    def clear(self) -> None:
        """Clears the input and output buffer of the device."""
        _ = self.dev.request(None, timeout=0.2)  # clear buffers

    #----------------------------------------------------------------------------------------------

    def command(self, command, message: str = None) -> Tuple[int | bool, str | None]:
        if message:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.debug(message)

        response = self.dev.request(command, timeout=5.0, pause_after_write=5)

        if 'OK' in response:
            return True, response
        elif not 'ERR' in response:
            # a number with sign
            return True, int(''.join(x for x in response if x.isdigit()))
        else:
            # ERR found -> decode error message
            _err = int(response.split('ERR')[-1])
            _err_msg = {
                1: "communication error/sent invalid commands/communication is a timeout ",
                2: "communication not established",
                3: "invalid command",
                4: "stop command",
                5: "limit switch is valid",
            }
            if _err in _err_msg:
                return False, f"Stage error '{response}': {_err_msg[_err]}"

        raise Exception(f"Something went wrong: {response}")


    #----------------------------------------------------------------------------------------------


    def _extract_position_from_response(self, from_string: str) -> int:
        position = int(from_string.split('\r')[-1][1:])  # returns "?X\rX+0000\n" with X=stage name
        return position


    #----------------------------------------------------------------------------------------------

    @property
    def position(self) -> Tuple[int, int]:
        for stage in self.stages:
            cmd, msg = stage.read_position_command()
            ok, response = self.command(cmd, message=msg)
            if ok:
                # update stage position from motion controller response
                # stage.position = self._extract_position_from_response(response)
                stage.position = int(response)
        return tuple([stage.position for stage in self.stages])

    #----------------------------------------------------------------------------------------------


    def get_current_stage_speed(self) -> int | None:
        """Get the speed of the current stage and return it plain.

        Returns:
            int, float: _description_
        """

        ok, response = self.command("?V", message="Getting stage speed")
        if ok:
            _v_speed = int(response.split('\r')[-1][1:])  # returns "?V\rV 0000\n"
            self.pulse_period = 30 / (_v_speed + 1)  # update pulse period -> pulses/ms
            return _v_speed
        return None


    #----------------------------------------------------------------------------------------------


    def set_current_stage_speed(self, v_speed: float | int) -> bool:
        """Set the velocity of the current stage as stage speed value.

        Args:
            speed (float | int): speed of the stage in mm/s

        Returns:
            bool: _description_
        """

        _v_speed = int(round(v_speed))
        assert _v_speed >= 0 and _v_speed <= 255, "Stage speed must be between 0 and 255."
        ok, _ = self.command(f"V{_v_speed}", message="Setting stage speed")
        return ok


    #----------------------------------------------------------------------------------------------

    def is_connected(self) -> bool:
        # this command is for all stages
        ok, response = self.command('?R')
        # if 'OK' in response:
        #     return True
        # else:
        #     return False
        return ok

    #----------------------------------------------------------------------------------------------


    def goto_position(self, new_position_x: float | int | str, new_position_y: float | int | str, units_in_mm: bool = True) -> bool:
        """Calculates the absolute new position on the linear stages and moves them to this position.

        Args:
            new_position_x (float | int | str): _description_
            new_position_y (float | int | str): _description_

        Raises:
            ValueError: _description_

        Returns:
            bool: _description_
        """

        for stage, new_position in zip(self.stages, (new_position_x, new_position_y)):
            if units_in_mm:
                _new_position = stage.convert_mm_to_steps(new_position)
            else:
                _new_position = new_position
            cmd, msg = stage.absolute_position_to_motion_command(_new_position)
            if cmd is not None and cmd != "":
                ok, response = self.command(cmd, message=msg)
                if not ok:
                    return False  # error during motion command
        x, y = self.position # update positions after motion
        return True


    #----------------------------------------------------------------------------------------------


    def center_position(self) -> int | bool:
        """Moves stage to the absolute center"""
        return self.goto_position('center', 'center')


    #----------------------------------------------------------------------------------------------


    def end_position(self) -> int | bool:
        """Moves stage to the absolute end"""
        return self.goto_position('end', 'end')


    #----------------------------------------------------------------------------------------------


    def move(self, x_displacement: float | int, y_displacement: float | int, units_in_mm: bool = True) -> bool:
        """Moves the stage in the positive or negative direction depending on the displacement value's sign.

        Args:
            x_displacement (float | int): positive or negative displacement in x direction [in mm if units_in_mm=True]
            y_displacement (float | int): positive or negative displacement in y direction [in mm if units_in_mm=True]
            units_in_mm (bool, optional): If true, displacements are interpreted as millimeters otherwise in steps. Defaults to True.

        Returns:
            int | Literal[True]: _description_
        """

        for stage, displacement in zip(self.stages, (x_displacement, y_displacement)):
            if units_in_mm:
                cmd, msg = stage.physical_displacement_to_motion_command(displacement)
            else:
                cmd, msg = stage.displacement_to_motion_command(displacement)
            ok, response = self.command(cmd, message=f"Moving stage {msg}")
            if not ok:
                return False  # error during motion command
        return True


    #----------------------------------------------------------------------------------------------


    def home(self) -> bool:
        """Get the command string to reset the stage position so that the absolute zero position (home)."""

        for stage in self.stages:
            cmd, msg = stage.home_command()
            ok, _ = self.command(cmd, message=msg)
            if ok:
                stage.position = 0  # to only way to set position initially
            else:
                return False  # error during homing
        return True


    #----------------------------------------------------------------------------------------------


    def reset(self) -> bool:
        return self.home()

    #----------------------------------------------------------------------------------------------


    def stop(self) -> bool:
        """Get the command string to stop the stage movement immediately"""

        ok, msg = self.command("S", message=f"Stopping current stage ")  # STOP command of stage to motion controller
        # response should contain an ERRx code then it sends an OK.
        if ok:
            self.clear()
        return ok




#--------------------------------------------------------------------------------------------------
# this definition can be stored herein or into a separate configuration file (.yaml)
DEFINITION_OF_STAGES = {
    "xytable_A" :{
        "resource_str": "COM5,9600,8N1",  # can also come from station_config.yaml
        "type": "translation_stage",
        "axis": [
            {
                "name": "X",
                'subdivision': 2,
                'step_angle': 1.8,
                'pitch_of_lead_screw': 4,
                'travel_range_mm': 350.0,
            },
            {
                "name": "Y",
                'subdivision': 2,
                'step_angle': 1.8,
                'pitch_of_lead_screw': 4,
                'travel_range_mm': 400.0,
            },
        ],
    },
    # define more stages here as needed
    # reference it by name in the database table `spsconfig`, column `parameter`
}


#
# from the database table `spsconfig`, column `parameter`
#


DEMO_PARAMETERS = {
    # already existing parameters used to show the cell position on screen
    "sequence_to_cell_pole": "Cell1-,Cell2+,Cell3-Cell4+,Cell5-,Cell6+,Cell7-,Cell8-,Cell9+,Cell10-,Cell11+,Cell12-,Cell13+,Cell14-,Cell15-,Cell16+,Cell17-,Cell18+,Cell19-,Cell20+,Cell21-,Cell15+,Cell16-,Cell17+,Cell18-,Cell19+,Cell20-,Cell21+,Cell8+,Cell9-,Cell10+,Cell11-,Cell12+,Cell13-,Cell14+,Cell1+,Cell2-,Cell3+,Cell4-,Cell5+,Cell6-,Cell7+",
    # this is for xy table automation
    "automation": {
        "stage": "xytable_A",
        "positions": {
            "units_in_mm": True,
            "home": (50.0, 100.5),  # position to insert the cellstack for start or to flip its side at 50% of welding
            "welding": [
                (150.0, 100.0),
                (150.0, 118.0),
                (150.0, 136.0),
                # ... 41 positions total ...
            ],
        }
    },
}

#----------------------------------------------------------

def generate_stage_from_parameter(parameter: dict) -> None | XYLinearStage:
    """Generates a LinearStage object from the given parameters dictionary.

    Args:
        parameters (dict): Dictionary containing stage parameters.
        name (str): Name of the stage ('X' or 'Y').

    Returns:
        LinearStage: Configured LinearStage object.
    """

    global DEFINITION_OF_STAGES

    stage = None
    if parameter is not None and "automation" in parameter:
        if "stage" in parameter["automation"]:
            if parameter["automation"]["stage"] in DEFINITION_OF_STAGES:
                stage_definition = DEFINITION_OF_STAGES[parameter["automation"]["stage"]]
                _resource_string = stage_definition["resource_str"]
                # prepare the stages of a linear XY table
                stages = ()
                if "translation_stage" == stage_definition["type"]:
                    for stage in stage_definition["axis"]:
                        # adds x,y etc. stages as they come from configuration
                        stages += (LinearStage(
                            name = stage["name"],
                            subdivision = stage["subdivision"],
                            step_angle = stage["step_angle"],
                            pitch_of_lead_screw = stage["pitch_of_lead_screw"],
                            travel_range_mm = stage["travel_range_mm"],
                        ),)
                    # create the XY table driver
                    if len(stages) > 1:
                        stage = XYLinearStage(stages[0], stages[1], _resource_string)

    return stage


#--------------------------------------------------------------------------------------------------

class StageStates(Enum):
    INIT = 0
    START = 1
    MOVE_POSITION = 4
    WAIT_POSITION_REACHED = 5
    POSITION_REACHED = 6
    FLIP_STACK = 8
    FEEDBACK_FROM_USER = 9
    END = 10
    STOP = 99


#--------------------------------------------------------------------------------------------------

class SatgeStateMachineBase(object):

    def __init__(self, dev: XYLinearStage, extra_parameter: dict = None) -> None:
        self.state: StageStates = StageStates.INIT
        self.dev = dev
        self.positions = extra_parameter["automation"]["positions"]
        self.units_in_mm = self.positions.get("units_in_mm", True)
        global DEBUG
        self._log = getLogger(__name__, DEBUG)
        self.is_sequence_done = False
        self.position_index = 0


    def set_state(self, new_state: StageStates) -> None:
        self.state = new_state


    # --- Rotating loop ---
    def do_one_loop(self) -> None:
        try:
            match self.state:

                case StageStates.INIT:
                    self.set_state(StageStates.START)

                case StageStates.START:
                    self.dev.reset()
                    x, y = self.positions["home"]
                    self.dev.goto_position(x, y, units_in_mm=self.units_in_mm)
                    # ???? how to get feedback from user that stage is ready ?

                case StageStates.MOVE_POSITION:
                    num_positions = len(self.positions)
                    self.position_index += 1
                    if self.position_index >= num_positions - 1:
                        self.is_sequence_done = True
                        self.set_state(StageStates.END)
                    elif self.position_index == num_positions / 2:
                        # need to flip the stack
                        self.set_state(StageStates.FLIP_STACK)
                    else:
                        x, y = self.positions[self.position_index]
                        self.dev.goto_position(x, y, units_in_mm=self.units_in_mm)
                        self.set_state(StageStates.WAIT_POSITION_REACHED)

                case StageStates.WAIT_POSITION_REACHED:
                    x, y = self.positions["welding"][self.position_index]
                    current_x, current_y = self.dev.position
                    if abs(current_x - x) < 0.01 and abs(current_y - y) < 0.01:
                        self.set_state(StageStates.POSITION_REACHED)


                case StageStates.POSITION_REACHED:
                    # trigger welding process here
                    # check for welding done
                    # if welding done:
                    self.set_state(StageStates.MOVE_POSITION)


                case StageStates.FLIP_STACK:
                    self.dev.reset()
                    # how do we get a feedback from the user ?
                    # if user confirmed:
                    x, y = self.positions["welding"][self.position_index]
                    self.dev.goto_position(x, y, units_in_mm=self.units_in_mm)
                    self.set_state(StageStates.WAIT_POSITION_REACHED)


                case StageStates.END:
                    self.dev.reset()
                    x, y = self.positions["home"]
                    self.dev.goto_position(x, y, units_in_mm=self.units_in_mm)


                #
                # Note: here we do not have a STOP
                #
                case other:
                    self.set_state(StageStates.START)

        except Exception as ex:
            self._log.critical(f"Stage complains: {type(ex)}:{ex}")
            #raise
            pass  # swallow
        finally:
            # do not change the state here
            pass


#--------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------


# def test_gcode_parser() -> None:
#     from rrc.gcode import gcodes, words
#     from rrc.gcode import Machine

#     gcs = gcodes.text2gcodes('G91 S1000 G1 X1 Y2 M3')
#     print(gcs)
#     gcs = gcodes.text2gcodes('G1 X1 Y2 G90')
#     print(gcs)
#     assert (len(gcs) == 2)
#     # G1 X1 Y2
#     assert (gcs[0].word == words.Word('G', 1))
#     assert (gcs[0].X == 1)
#     assert (gcs[0].Y == 2)
#     # G90
#     assert (gcs[1].word == words.Word('G', 90))

#     m = Machine()

#     gcs = gcodes.text2gcodes('G18 G1 X1 Y2 G90 G1 X100 Y100 F1500')
#     print(gcs)
#     m.process_gcodes(*gcs)  # has a DEBUG print of position changes
#     print(m.pos)
#     gcs = gcodes.text2gcodes('G1X1Y2G90G1X100Y100F1500')
#     print(gcs)
#     gcs = gcodes.text2gcodes('G1 X0 Y0 G2 X0 Y10 I5 J5')
#     print(gcs)
#     m.process_gcodes(*gcs)  # has a DEBUG print of position changes


def test_xydevice(resource_string: str) -> None:
    """Test function for the XY device driver."""

    X_stage = LinearStage(
        name = 'X',
        subdivision = 2,
        step_angle = 1.8,
        pitch_of_lead_screw = 5,
        travel_range_mm = 216.0,
    )

    Y_stage = LinearStage(
        name = 'Y',
        subdivision = 2,
        step_angle = 1.8,
        pitch_of_lead_screw = 5,
        travel_range_mm = 400.0,
    )
    dev = XYLinearStage(X_stage, Y_stage, resource_string)
    print(f"Connected: {dev.is_connected()}")
    dev.clear()

    POSITIONS_OF_PART = [  # RRC3570 42 positions (define them in mm)
        (165.738, 62.525),       # Worker position
        ("PAUSE", 1.0),
        (165.738, 162.525),       # First welding position - Face 1
        ("PAUSE", 1.0),
        (165.738, 185.975),
        ("PAUSE", 1.0),
        (165.738, 209.425),
        ("PAUSE", 1.0),
        (165.738, 232.875),
        ("PAUSE", 1.0),
        (165.738, 256.325),
        ("PAUSE", 1.0),
        (165.738, 279.775),
        ("PAUSE", 1.0),
        (165.738, 303.225),    
        ("PAUSE", 1.0),
        (145.428, 291.505),      # Start position of column 2 - Face 1
        ("PAUSE", 1.0),
        (145.428, 268.055),
        ("PAUSE", 1.0),
        (145.428, 244.605),
        ("PAUSE", 1.0),
        (145.428, 221.155),
        ("PAUSE", 1.0),
        (145.428, 197.705),
        ("PAUSE", 1.0),
        (145.428, 174.255),
        ("PAUSE", 1.0),
        (145.428, 150.805),      
        ("PAUSE", 1.0),   
        (125.118, 162.525),      # Start position of column 3 - Face 1
        ("PAUSE", 1.0),  
        (125.118, 185.975),
        ("PAUSE", 1.0), 
        (125.118, 209.425),
        ("PAUSE", 1.0), 
        (125.118, 232.875),
        ("PAUSE", 1.0),
        (125.118, 256.325),
        ("PAUSE", 1.0),    
        (125.118, 279.775),
        ("PAUSE", 1.0),
        (125.118, 303.225),      
        ("PAUSE", 1.0),
        (165.738, 62.525),       # Worker position (flip)
        ("PAUSE", 10.0),          
        (165.738, 162.525),      # First welding position - Face 2
        ("PAUSE", 1.0),
        (165.738, 185.975),
        ("PAUSE", 1.0),
        (165.738, 209.425),
        ("PAUSE", 1.0),
        (165.738, 232.875),
        ("PAUSE", 1.0),
        (165.738, 256.325),
        ("PAUSE", 1.0),
        (165.738, 279.775),    
        ("PAUSE", 1.0),
        (165.738, 303.225),
        ("PAUSE", 1.0),
        (145.428, 291.505),     # Start position of column 2 - Face 2
        ("PAUSE", 1.0),
        (145.428, 268.055),
        ("PAUSE", 1.0),
        (145.428, 244.605),
        ("PAUSE", 1.0),
        (145.428, 221.155),
        ("PAUSE", 1.0),
        (145.428, 197.705),
        ("PAUSE", 1.0),
        (145.428, 174.255),      
        ("PAUSE", 1.0),   
        (145.428, 150.805),
        ("PAUSE", 1.0),  
        (125.118, 162.525),      # Start position of column 3 - Face 2
        ("PAUSE", 1.0), 
        (125.118, 185.975),
        ("PAUSE", 1.0), 
        (125.118, 209.425),
        ("PAUSE", 1.0),
        (125.118, 232.875),
        ("PAUSE", 1.0),    
        (125.118, 256.325),
        ("PAUSE", 1.0), 
        (125.118, 279.775),
        ("PAUSE", 1.0), 
        (125.118, 303.225),
        ("PAUSE", 1.0), 
        (165.738, 62.525),
        ("PAUSE", 1.0),     
        # ... (add more positions as needed) ...
    ]

    # for _x, _y in POSITIONS_OF_PART[:]:
    #     if isinstance(_x, str):
    #         if _x == "PAUSE" and _y is not None:
    #             print(f"Pause for {_y} seconds!")
    #             sleep(_y)
    #         elif _x == "USER":
    #             # Need to interact with user (read io port, etc.)
    #             pass
    #         else:
    #             print(f"Unknown statement {_x}!")
    #         continue
    #     if not dev.goto_position(_x, _y, units_in_mm=True):
    #         print(f"Error moving to position X={_x} Y={_y}")
    #     else:
    #         print(f"Moved to position X={_x} Y={_y}, current position: {dev.position}")
    #         # Start welding here
    #     sleep(0.3)

    # Test movement
    dev.home()
    dev.goto_position(165.738, 62.525)
    dev.goto_position(165.738, 162.525)
    # dev.goto_position(100.0, 110.0)
    # dev.goto_position(150.0, 110.0)


#--------------------------------------------------------------------------------------------------

class OurXYAWS3Modbus(AWS3Modbus):

    def setup_device(self):
        self.machine_name = self.read_name().strip()
        self._toggle_bits = self._read_toggle_bits()

    def is_machine_ready(self) -> tuple:
        self._sync_modbus_timing()
        # following includes a verification helper to simulate a weld process with
        # a real machinge but without really doing the welding process (saves material and time)
        bits = self.read_coils(97-1, 8, unit_address=3) if not self._verification_weld_resultbits else self._verification_weld_resultbits
        d = {
            "ready": 1 if bits[0] else 0,
            "operational_mode": 1 if bits[1] else 0,  # 0=auto, 1=step
            "reject": 1 if (bits[2] or bits[4]) else 0,  # combine both axes: either one fails
            "hfi_device_fault": 1 if bits[5] else 0,
            "ok": 1 if (bits[6] and bits[7]) else 0  # combine both axes: both need to be good
        }
        return bits[0], d


def test_aws3_communication(resource_str: str) -> None:

    try:
        dev = OurXYAWS3Modbus(resource_str)
        dev.open()
        dev.setup_device()
        # keep open

        while True:
            print(f"Machine name: {dev.machine_name}")
            print(dev.is_machine_ready())
            print(dev.read_program_name(axis=1), dev.read_program_no())
            print(dev.read_axis_counter(1))
            print(dev.read_machine_lock_status())
            sleep(1.0)

    except Exception as ex:
        print(ex)
        print("Using dummy AWS3 Modbus driver for test purposes.")


def auto_run(xy_table, welder, POSITIONS_OF_PART, WORKER_POSITION_X, WORKER_POSITION_Y):
    welding_position = 0

    for _x, _y in POSITIONS_OF_PART[:]:
        if isinstance(_x, str):
            if _x == "PAUSE" and _y is not None:
                print(f"Pause for {_y} seconds!")
                sleep(_y)
            elif _x == "USER":
                # Wait for operator to press "MOVE" button (connected with ADAM-6052)

                c = input("Please press 'c' to continue or 's' to stop: ").strip()
                if c.lower() == 's':
                    print(f"Process stopped at welding position {welding_position}.")
                    xy_table.goto_position(WORKER_POSITION_X, WORKER_POSITION_Y)
                    return
                
            elif _x == "RESTART":
                pass
                # Need to rerun the process from the beginning (or run the next process)
                # c = input("Please press 'c' to continue or 's' to stop: ").strip()
                # if c.lower() == 'c':
                #     auto_run(xy_table, welder, POSITIONS_OF_PART, WORKER_POSITION_X, WORKER_POSITION_Y)
                # else:
                #     return
                
                
            elif _x == "WELD":
                welding_position += 1
                # Need to trigger welding machine and wait for finish
                while True:
                    _ready, _ = welder.is_machine_ready()
                    if _ready:
                        break
                    sleep(0.01)
                
                # Make sure program is set
                welder.write_program_no(int(_y))
                sleep(0.01)
                while welder.read_program_no() != int(_y):
                    sleep(0.01)
                pass

                # Welding automated start could be implemented here (Full automation)
                # Write your code here

                print(f"Welding position {welding_position}.")
                print("Wait until welding is done.")
                while True: 
                    sleep(0.01)
                    _ready, _ = welder.is_machine_ready()
                    if not _ready:
                        continue

                    if welder.is_toggle_bit_changed():
                        break  # Welding is done
                
                # Get welding results
                _, weld_result = welder.is_machine_ready()
                # ''' SIMULATION MOVING XYTABLE IN CASE WELDING MACHINE DOES NOT WORK'''
                # weld_test_result = input("Welding result ok or failed or No signal: ").lower().strip()
                weld_test_result = ""

                if weld_result["ok"] == 1 or weld_test_result == "ok":          # Case when welding result is ok
                    #is_operator_button_ok()   # Check operator press
                    print("Welding ok")

                    continue
                elif weld_result["reject"] == 1 or weld_test_result == "failed":    # Case when welding failed

                    print("Welding failed")
                    # Stops welding at failed position. Then, operator changes to new pack, then scans in new label -> 
                    # xy table moves back to worker position to restart new welding process
                    xy_table.goto_position(WORKER_POSITION_X,WORKER_POSITION_Y)

                    # c = input("Please press 'c' to continue or 's' to stop: ").strip()
                    # if c.lower() == 'c':
                    #     break
                    # else:
                    #     return


                else:
                    # Case when no welding signal is received
                    # In this case, xytable stops. Operator moves battey pack out, and puts pack back in position
                    # Then, operator can press 'c' to continue moving the xytable to the next welding position
                    
                    print("No welding signal received!")
                    c = input("Please press 'c' to continue or 's' to stop: ").strip()
                    if c.lower() == 's':
                        print(f"Process stopped at welding position {welding_position}.")
                        xy_table.goto_position(WORKER_POSITION_X, WORKER_POSITION_Y)
                    else:
                        continue

                # Stop parsing
                break

            else:
                print(f"Unknown statement {_x}!")
            continue

        if not xy_table.goto_position(_x, _y, units_in_mm=True):
            print(f"Error moving to position X={_x} Y={_y}")
        else:
            print(f"Moved to position X={_x} Y={_y}, current position: {xy_table.position}")
            # Start welding here
        sleep(0.3)
    
def is_move_button_pressed(adam) -> bool:
            
    # button_state = adam.get_digital_input(index=7)
    # # time.sleep(0.1)
    
    # return button_state 

    print("Waiting for Operator to press 'MOVE'...")
    
    while True:
        # 1. Read the button state
        is_pressed = adam.get_digital_input(index=0)
        
        # 2. If pressed, exit the loop and return
        if is_pressed:
            print("Button pressed! Moving to next position...")
            return is_pressed
        
        # 3. VERY IMPORTANT: Sleep for a short time
        # This prevents your laptop CPU from hitting 100% 
        sleep(0.1)

def is_light_curtain_activated(adam) -> bool:
    return not adam.get_digital_input(index=1)

def is_emergency_button_pressed(adam) -> bool:
    return adam.get_digital_input(index=2)

def table_state_machine(xy_table, welder, adam, current_state: int, table_of_positions: list, table_index: int, welding_position: int) -> Tuple[int, int, int]:

    _next_state = current_state
    sleep(0.01)    # Limit communication on LAN
    if current_state != 99 and (is_light_curtain_activated(adam) or is_emergency_button_pressed(adam)):
        try:
            xy_table.stop()
        except Exception:
            pass
        print("Light curtain activated -> Move to state 99")
        return 99, table_index, welding_position

    match current_state:

        case 0:  # initialize

            # if not is_light_curtain_activated(adam):
            xy_table.goto_position(165.738, 62.525, units_in_mm=True)  # Go to worker position

            table_index = -1  # reset table index
            welding_position = 0  # reset welding position
            print("Move to state 1")
            _next_state = 1  # move to next state


        case 1:
            # check move button or other user input to move to next position
            if is_move_button_pressed(adam):
                _next_state = 2  # move to next position
            # stay in current state until user input

        case 2:
            # move to next 
            table_index += 1
            # Check if table is finished
            if table_index >= len(table_of_positions):
                _next_state = 0
            else:
                print("Moved to state 3")
                _next_state = 3  # evaluate table entry

        case 3:
            # evaluate table entry
            x, y = table_of_positions[table_index]
            if isinstance(x, str):
                if x == "PAUSE" and y is not None:
                    print(f"Pause for {y} seconds!")
                    sleep(y)  # wait a bit before moving to the next position
                    _next_state = 2  # next table position
                elif x == "USER":
                    # Need to interact with user (read io port, etc.)
                    print("Move to state 1")
                    _next_state = 1  # wait for user input
                elif x == "WELD":
                    # trigger welding process here
                    # check for welding done
                    print("Move to state 4")
                    _next_state = 4  # next table position                    
                else:
                    print(f"Unknown statement {x}!")
                    _next_state = 0
            else:  
                # position change
                xy_table.goto_position(x, y, units_in_mm=True)
                _next_state = 3
                table_index += 1  # Move to next command

        case 4:
            _next_state = 5     # This line is for testing in case welder is not working
            print(f"Welding position {welding_position}.")
            print("Wait until welding is done.")
            # _ready, _ = welder.is_machine_ready()
            # if _ready:
            #     if welder.is_toggle_bit_changed():
            #         print("Move to state 5")
            #         _next_state = 5  # check welding result

        case 5:
            # Get welding results
            _, weld_result = welder.is_machine_ready()

            # ''' SIMULATION MOVING XYTABLE IN CASE WELDING MACHINE DOES NOT WORK'''
            weld_test_result = ""
            weld_test_result = input("Welding result ok or failed or No signal: ").lower().strip()

            if weld_test_result == "ok":
            # if weld_result["ok"] == 1:          # Case when welding result is ok
                #is_operator_button_ok()   # Check operator press
                print("Welding ok")
                # print("Move to state 6")
                # _next_state = 6   # wait for user input to move to next position

                welding_position += 1
                print("Move to state 2")
                _next_state = 2

            elif weld_test_result == "failed":
            # elif weld_result["reject"] == 1:    # Case when welding failed

                print("Welding failed")
                print("Move to state 7")
                _next_state = 7  # move to error handling state

            else:
                # Case when no welding signal is received
                # In this case, xytable stops. Operator moves battey pack out, and puts pack back in position
                # Then, operator can press 'c' to continue moving the xytable to the next welding position
                
                print("No welding signal received!")
                _next_state = 4

            # sleep(3) Delay time to wait for welding head to move up + operator detect if sticky electrode happens

        case 6:
            # wait for user input to move to next position or another welding result
            if is_move_button_pressed(adam):
                # position done, move to next position
                welding_position += 1
                print("Move to state 2")
                _next_state = 2
            # if is_welding_done():
            # _ready, _ = welder.is_machine_ready()
            # if _ready:
            #     if welder.is_toggle_bit_changed():
            #         _next_state = 5  # check welding result again

        case 7:
            # error handling state
            print("Error during welding process! Please check the machine and try again.")
            _next_state = 0  # reset to initial state

        case 99: # SAFETY LOCK STATE
            # Stay here as long as the curtain is blocked

            if not is_light_curtain_activated(adam) and not is_emergency_button_pressed(adam):
                print("Light curtain clear and Emergency button released. Press MOVE button to resume.")
                print("Move to state 1")
                _next_state = 1  # Move to state 1 to check for move button pressed

        case _:
            # reset to initial state if something goes wrong
            _next_state = 0

    return _next_state, table_index, welding_position

def read_input_from_scanner() -> str:
    return ""  # TODO: implement this function to read from a barcode scanner or other input device

def test_combined_controllers(resource_str_aws: str, resource_str_xy: str, resource_str_adam: str):
    adam = ADAM6052(ip=resource_str_adam, connect=True)
    welder = OurXYAWS3Modbus(resource_str_aws)
    welder.open()
    welder.setup_device()

    X_stage = LinearStage(
        name = 'X',
        subdivision = 2,
        step_angle = 1.8,
        pitch_of_lead_screw = 5,
        travel_range_mm = 1000.0,
    )

    Y_stage = LinearStage(
        name = 'Y',
        subdivision = 2,
        step_angle = 1.8,
        pitch_of_lead_screw = 5,
        travel_range_mm = 1000.0,
    )

    xy_table = XYLinearStage(X_stage, Y_stage, resource_str_xy)
    print(f"Connected: {xy_table.is_connected()}")
    xy_table.clear()
    WORKER_POSITION_X, WORKER_POSITION_Y = 165.738, 62.525
    POSITIONS_OF_PART = [  # RRC3570 42 positions (define them in mm)
        
        # (WORKER_POSITION_X, WORKER_POSITION_Y),       # Worker position
        (165.738, 162.525),       # First welding position - Face 1
        ("WELD", 1),             # Trigger welding with program number
        (165.738, 185.975),
        ("WELD", 2),
        (165.738, 209.425),
        ("WELD", 3),
        (165.738, 232.875),
        ("WELD", 4),
        (165.738, 256.325),
        ("WELD", 5),
        (165.738, 279.775),
        ("WELD", 6),
        (165.738, 303.225),    
        ("WELD", 7),
        (145.428, 291.505),      # Start position of column 2 - Face 1
        ("WELD", 8),
        (145.428, 268.055),
        ("WELD", 9),
        (145.428, 244.605),
        ("WELD", 10),
        (145.428, 221.155),
        ("WELD", 11),
        (145.428, 197.705),
        ("WELD", 12),
        (145.428, 174.255),
        ("WELD", 13),
        (145.428, 150.805),      
        ("WELD", 14),
        (125.118, 162.525),      # Start position of column 3 - Face 1
        ("WELD", 15),
        (125.118, 185.975),
        ("WELD", 16),
        (125.118, 209.425),
        ("WELD", 17),
        (125.118, 232.875),
        ("WELD", 18),
        (125.118, 256.325),
        ("WELD", 19),
        (125.118, 279.775),
        ("WELD", 20),
        (125.118, 303.225),      
        ("WELD", 21),
        (WORKER_POSITION_X, WORKER_POSITION_Y),       # Worker position (flip)
        ("USER", None),          # Operator stops to flip pack, then press 'MOVE' button to continue.
        (165.738, 162.525),      # First welding position - Face 2
        ("WELD", 22),
        (165.738, 185.975),
        ("WELD", 23),
        (165.738, 209.425),
        ("WELD", 24),
        (165.738, 232.875),
        ("WELD", 25),
        (165.738, 256.325),
        ("WELD", 26),
        (165.738, 279.775),    
        ("WELD", 27),
        (165.738, 303.225),
        ("WELD", 28),
        (145.428, 291.505),     # Start position of column 2 - Face 2
        ("WELD", 29),
        (145.428, 268.055),
        ("WELD", 30),
        (145.428, 244.605),
        ("WELD", 31),
        (145.428, 221.155),
        ("WELD", 32),
        (145.428, 197.705),
        ("WELD", 33),
        (145.428, 174.255),      
        ("WELD", 34),  
        (145.428, 150.805),
        ("WELD", 35),  
        (125.118, 162.525),      # Start position of column 3 - Face 2
        ("WELD", 36),
        (125.118, 185.975),
        ("WELD", 37),
        (125.118, 209.425),
        ("WELD", 38),
        (125.118, 232.875),
        ("WELD", 39),  
        (125.118, 256.325),
        ("WELD", 40),
        (125.118, 279.775),
        ("WELD", 41),
        (125.118, 303.225),
        ("WELD", 42),
        (WORKER_POSITION_X, WORKER_POSITION_Y),
        ("USER", None),      # Go back home, let operator change to new pack and continue with new welding process  
        # ... (add more positions as needed) ...
    ]

    # Combine control for controller and reading from welding machine
    xy_table.home()

    welding_position = 0
    table_index = 0
    state_of_machine = 0
    while True:
        _udi = read_input_from_scanner()
        if _udi != "":
            print(f"Received input: {_udi}")
            # reset state machine which then resets table index and welding position
            state_of_machine = 0

        # call the state machine in a loop to process the positions and user input
        state_of_machine , table_index, welding_position = table_state_machine(xy_table, welder, adam, state_of_machine, POSITIONS_OF_PART, table_index, welding_position)


    # auto_run(xy_table, welder, POSITIONS_OF_PART, WORKER_POSITION_X, WORKER_POSITION_Y)


#--------------------------------------------------------------------------------------------------

def test_db_driven_stage() -> None:

    global DEMO_PARAMETERS

    dev = generate_stage_from_parameter(DEMO_PARAMETERS)
    SM = SatgeStateMachineBase(dev, DEMO_PARAMETERS)

    while SM.state != StageStates.END:
        SM.do_one_loop()  # call this in a timed loop
        sleep(0.2)

#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    #test_gcode_parser()

    RESOURCE_STR_MOTION_CONTROLLER = "COM9,9600,8N1"  # Port for motion controller
    RESOURCE_STR_AWS = "tcp:172.25.103.100:502"
    RESOURCE_STR_ADAM = "172.25.103.202"
    # test_xydevice(RESOURCE_STR_MOTION_CONTROLLER)
    test_combined_controllers(RESOURCE_STR_AWS, RESOURCE_STR_MOTION_CONTROLLER, RESOURCE_STR_ADAM)

    # test_aws3_communication("tcp:172.25.103.100:502")
    # test_db_driven_stage()

    toc = perf_counter()
    _log.info(f"DONE in {toc - tic:0.4f} seconds.")

# END OF FILE