
"""
Contains the drivers for stepper motor controller MOC-01/MOC-02 from Optics Focus Instruments Co., Ltd.
"""

from inspect import _V_contra
from typing import Tuple, Literal
from urllib import response
from rrc.eth2serial import Eth2SerialDevice
from rrc.serialport import SerialComportDevice



# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

DEBUG = 0

from rrc.custom_logging import getLogger, logger_init

# --------------------------------------------------------------------------- #

#--------------------------------------------------------------------------------------------------
class LinearStage():

    def __init__(self,
                name: str,  # either 'X' or 'Y' or 'Z'
                stage_type: str,  # either 'translation_stage', 'rotation_stage', 'goniometer_stage' or 'lab_jack'
                subdivision: int,  # from back of motion controller: e.g. 2
                step_angle: float, # from the side of the stage: either 0.9 or 1.8
                pitch: float,      # in mm - from the optics focus website, e.g. 4
                max_position: int, # maximum stage position in controller pulse units, e.g. 10000
                device: Eth2SerialDevice | SerialComportDevice = None,
                ) -> None:

        self.name = name.upper()
        self.stage_type = stage_type
        # calculation depending on the type of stage
        self.subdivision = subdivision
        self.step_angle = step_angle
        self.pitch = pitch
        self.max_position = max_position
        # precalculate pulse equivalent in mm
        self.pulse_equiv = pitch * step_angle / (360 * subdivision)
        self.position = None  # current position of the stage unkonwn at start
        self.dev = device

    #----------------------------------------------------------------------------------------------

    def setup_device(self, device: Eth2SerialDevice | SerialComportDevice) -> None:
        """Sets up the device connection for the linear stage

        :param device: device connection to be used for the linear stage
        :type device: Eth2SerialDevice | SerialComportDevice
        """
        self.dev = device

    #----------------------------------------------------------------------------------------------

    def command(self, command, message: str = None) -> int | Literal[True]:
        if message:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.info(message)
        response = self.dev.request(command)
        #self.Ins.clear()
        #response = self.Ins.query_ascii_values(command, converter='s')[0]
        if 'OK' in response:
            return True
        elif not 'ERR' in response:
            return int(''.join(x for x in response if x.isdigit()))
        else:
            # decode error message
            _err_msg = {
                "ERR1": "communication error/sent invalid commands/communication is a timeout ",
                "ERR2": "communication not established",
                "ERR3": "invalid command",
                "ERR4": "stop command",
                "ERR5": "limit switch is valid"
            }
            if response in _err_msg:
                raise Exception(f"Stage error: {response} -> {_err_msg[response]}")
            else:
                raise Exception(f"Something wen't wrong: {response}")

    #----------------------------------------------------------------------------------------------

    def _convert_speed_stage_to_physical(self, v_speed: float | int) -> float:
        """Converts a stage speed into mm/s"""
        return round((v_speed + 1) * self.pulse_equiv * (22000 / 720), 2)  # convert from Vspeed to mm/s

    def _convert_speed_physical_to_stage(self, speed_mm_s: float | int) -> float:
        """Converts a speed given in mm/s into a speed value recognisable by the stage"""
        return (speed_mm_s / (22000 / 720) / self.pulse_equiv) - 1  # convert from mm/s to Vspeed


    def _convert_displacement_to_command(self, displacement: float | int) -> str:
        """Converts a positive or negative displacement (in mm) into a command recognisable by the stage"""

        direction = '+' if displacement > 0 else '-'
        # convert from mm to steps for motioncontroller
        magnitude = int(abs(displacement) / self.pulse_equiv)
        return f"{self.name}{direction}{magnitude}"  # command for motion controller


    #----------------------------------------------------------------------------------------------

    def get_speed(self) -> float:
        """Get the speed of the stage and return it in mm/s."""
        response = self.command("?V", message="Getting stage speed")
        _v_speed = int(response.split('\r')[-1][1:])  # returns "?V\rV 0000\n"
        return self._convert_speed_stage_to_physical(_v_speed)

    def set_speed(self, speed: float | int) -> bool:
        """Set the speed of the stage

        :param speed: speed of the stage in mm/s
        :type stage_speed: float, int
        """

        _v_speed = self._convert_speed_physical_to_stage(speed)
        return self.command(f"V{int(round(_v_speed))}", message="Setting stage speed")

    #----------------------------------------------------------------------------------------------

    @property
    def position(self) -> Tuple[int, int]:
        response = self.command(f"?{self.name}", message=f'Getting {self.name}-position')
        position = int(response.split('\r')[-1][1:])  # returns "?X\rX+0000\n" with X=stage name
        self.position = position
        return self.position

    #----------------------------------------------------------------------------------------------

    def is_connected(self) -> int | Literal[True]:
        return self.command('?R')

    #----------------------------------------------------------------------------------------------


    def goto(self, new_position: float | int | str) -> Tuple[str, str]:
        """Get the command string to go to an absolute position on the linear stage

        :param position: absolute position of stage in controller pulse units - see manual
        :type position: float, int
        """

        if not new_position or new_position == 'start':
            return self.reset()

        if isinstance(new_position, str):
            if new_position == 'center':
                new_position = self.max_position / 2
            elif new_position == 'end':
                new_position = self.max_position
            else:
                raise ValueError(f"{new_position} is not a valid command for the linear stage '{self.name}'")

        if new_position > self.max_position:
            new_position = self.max_position  # limit to max position
        elif new_position <= 0:
            return self.reset()

        if self.position is None:
            return False  # not yet on defined position -> need to HOME or MAX first

        displacement = int(new_position - self.position)
        if not displacement:
            return True  # already on position

        return self.command(f"{self.name}{displacement:+}", message=f"Setting {self.name}-position")  # command to motion controller



    def center(self) -> int | bool:
        """Moves stage to the absolute center"""
        return self.goto('center')


    def move(self, displacement: float | int) -> int | Literal[True]:
        """Moves the stage in the positive or negative direction

        :param displacement: positive or negative displacement [in mm]
        :type displacement: float, int
        """

        command = self._convert_displacement_to_command(displacement)
        return self.command(command, message=f"Moving stage '{self.name}' {displacement}mm")


    def reset(self) -> Tuple[str, str]:
        """Get the command string to reset the stage position so that the absolute position = 0"""
        self.position = 0  # to only way to set position
        return self.command(f"H{self.name}0", message=f"Resetting stage '{self.name}'...")  # HOME command of stage to motion controller


    def stop(self) -> Tuple[str, str]:
        """Get the command string to stop the stage movement immediately"""
        return self.command("S", message=f"Stopping stage '{self.name}'...")  # STOP command of stage to motion controller



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
            # serial port which connects only on send or receive respecting the given timeouts in the send/request call.
            self.dev = SerialComportDevice(resource_string, termination=("\n", "\r"))
        else:
            # socket port which needs an open connection with timeout. The first call does not set the timeout.
            self.dev = Eth2SerialDevice(resource_string, termination=("\n", "\r"), open_connection=True)
            # now the connection is open with timeout setting
            self.dev.connect_socket(timeout=timeout)

        X.setup_device(self.dev)
        self.X_stage = X
        Y.setup_device(self.dev)
        self.Y_stage = Y



    #----------------------------------------------------------------------------------------------


    def command(self, command, message: str = None) -> int | Literal[True]:
        if message:
            global DEBUG
            _log = getLogger(__name__, DEBUG)
            _log.info(message)
        response = self.dev.request(command)
        #self.Ins.clear()
        #response = self.Ins.query_ascii_values(command, converter='s')[0]
        if 'OK' in response:
            return True
        elif not 'ERR' in response:
            return int(''.join(x for x in response if x.isdigit()))
        else:
            raise Exception("Something wen't wrong")


    #----------------------------------------------------------------------------------------------


    @property
    def position(self) -> Tuple[int, int]:
        x = self.X_stage.position
        y = self.Y_stage.position
        return x, y


    def is_connected(self) -> int | Literal[True]:
        return self.X_stage.is_connected()


    def center(self) -> bool:
        """Moves both stages to the absolute center"""
        ok1 = self.X_stage.center()
        ok2 = self.Y_stage.center()
        return ok1 and ok2


    def move(self, displacement_x: float | int, displacement_y: float | int) -> bool:
        """Moves the stages in the positive or negative direction

        :param displacement_x: positive or negative displacement in x direction [in mm]
        :type displacement_x: float, int
        :param displacement_y: positive or negative displacement in y direction [in mm]
        :type displacement_y: float, int
        """

        ok1 = self.X_stage.move(displacement_x)
        ok2 =self.Y_stage.move(displacement_y)
        return ok1 and ok2


    def goto(self, x: float | int | str, y: float | int | str) -> bool:
        """Go to an absolute position on the linear stages

        :param x: absolute position of stage in controller pulse units - see manual
        :type x: float, int, str
        :param y: absolute position of stage in controller pulse units - see manual
        :type y: float, int, str
        """

        ok1 = self.X_stage.goto(x)
        ok2 = self.Y_stage.goto(y)
        return ok1 and ok2


    def set_speed(self, stage_speed: float | int) -> bool:
        """Get or set the speed of the stage

        :param stage_speed: speed of the stage in mm/s
        :type stage_speed: float, int
        """

        ok = self.X_stage.set_speed(stage_speed)
        #self.Y_stage.set_speed(stage_speed)


    def get_speed(self) -> float:
        """Get the speed of the stage and return it in mm/s."""
        return self.X_stage.get_speed()


    def go_home(self) -> bool:
        """Moves furnace to the center of the stage (x = 5000)
        """
        ok1 = self.X_stage.go_home()
        ok2 = self.Y_stage.go_home()
        return ok1 and ok2


    def reset(self) -> bool:
        """Resets the stages positions so that the absolute position = 0 (origin)"""
        ok1 = self.X_stage.reset()
        ok2 = self.Y_stage.reset()
        return ok1 and ok2



#--------------------------------------------------------------------------------------------------

def test_xydevice(resource_string: str) -> None:
    """Test function for the XY device driver."""
    from time import sleep

    X_stage = LinearStage(
        name = 'X',
        #stage_type = 'translation_stage',  # either 'translation_stage', 'rotation_stage', 'goniometer_stage' or 'lab_jack'
        #running_unit = 'mm',  # either 'mm','degree' or 'step'
        step_angle = 0.9,
        subdivision = 2,
        #screw_lead = 1,
        pitch = 4,
        #transmission_ratio = None,
        #travel_range = 50,
        max_position = 10000,
    )

    Y_stage = LinearStage(
        name = 'Y',
        #stage_type = 'translation_stage',  # either 'translation_stage', 'rotation_stage', 'goniometer_stage' or 'lab_jack'
        #running_unit = 'mm',  # either 'mm','degree' or 'step'
        step_angle = 0.9,
        subdivision = 2,
        #screw_lead = 1,
        pitch = 4,
        #transmission_ratio = None,
        #travel_range = 50,
        max_position = 20000,
    )
    dev = XYLinearStage(X_stage, Y_stage, resource_string)
    X_stage.setup_device(dev.dev)
    Y_stage.setup_device(dev.dev)

    POSITIONS_OF_PART = [  # RRC3570 42 positions
        (50,100),
        (150,100),
        (250,100),
        (350,100),
    ]

    for _x,_y in POSITIONS_OF_PART[2:5]:
        dev.goto(_x, _y)
        print(f"Moved to position X={_x} Y={_y}, current position: {dev.position}")
        sleep(0.3)

    #print(dev.request("POS?"))
    print(dev.position)


#--------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from time import perf_counter

    ## Initialize the logging
    logger_init(filename_base=None)  ## init root logger with different filename
    _log = getLogger(__name__, DEBUG)

    tic = perf_counter()

    RESOURCE_STR = "COM5,9600,8N1"

    test_xydevice(RESOURCE_STR)


    toc = perf_counter()
    _log.info(f"DONE in {toc - tic:0.4f} seconds.")


# END OF FILE