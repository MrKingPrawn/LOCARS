"""Module to control IPS laser by comunnicating in serial with pyvisa."""

import time
from typing import Dict

import pyvisa

LASER_STATE = {0: "Idle", 1: "ON", 2: "Not connected"}
ERROR_CODES = {
    0: "NO_ERROR",  # Hardware error
    3011: "HOUSEKEEPING",  # Hardware error
    3012: "FLASH_INITIALIZATION_FAILED",  # Hardware error
    3013: "FLASH_HOUSEKEEPING_FAILED",  # Hardware error
    3014: "LOW_VOLTAGE_EVENT",  # Hardware error
    3015: "BAD_VOLTAGE_3V3",  # Hardware error
    3016: "BAD_VOLTAGE_VIN",  # Hardware error
    3017: "BAD_VOLTAGE_VTEC",  # Hardware error
    3018: "HIGH_INPUT_CURRENT",  # Hardware error
    3019: "TEC_UPDT_ON_BRD_STATE_BAD",  # Hardware error
    3020: "TEC_UPDT_ON_TEMP_LONG_BAD",  # Hardware error
    3021: "TEC_UPDT_ON_TEMP_OUT_SETPT",  # Hardware error
    3022: "TEC_UPDT_ON_TEMP_OUT_RANGE",  # Hardware error
    3097: "FAILED_INITIAL_POST",  # Hardware error
    3098: "FLASH_PARAMS_REINITIALIZED",  # Hardware error
    3099: "UNIDENTIFIED_ERROR",  # Hardware error
    -102: "Syntax error",  # Communication error
    -103: "Invalid separator",  # Communication error
    -108: "Parameter not allowed",  # Communication error
    -109: "Missing parameter",  # Communication error
    -113: "Undefined header",  # Communication error
    -131: "Invalid suffix",  # Communication error
    -138: "Suffix not allowed",  # Communication error
    -200: "Execution error",  # Communication error
    -224: "Illegal parameter value",  # Communication error
}

STATUS = {
    0: "unknown state",
    1: "board passed POST",
    2: "board failed POST",
    3: "board in normal state",
    4: "board in fault state",
    5: "board in boot load state",
    6: "board not attached",
}


class IpsLaser:
    """Control IPS Dual Laser."""

    def __init__(self):
        self.idn = None
        self.comport = None
        self.serial = None
        self.status = 2
        self.isconnected = False
        self.laser_current = None
        self.laser_temp = None
        self.laser_power = None

        self.ressource_manage = pyvisa.ResourceManager("@py")

    def find_acm_devices(self) -> Dict[str, pyvisa.highlevel.ResourceInfo]:
        """
        find_acm_devices find_ACM_devices finds and returns a tuple of ACM ressources that can be
        detected by pyvisa's ressource manage.

        IPS lasers appear as `ASRL/dev/ttyACMX::INSTR`

        Returns
        -------
        dict
            Mapping of resource name to ResourceInfo from pyvisa.
        """
        acm_resources = self.ressource_manage.list_resources_info(query="?*ACM?*")
        return acm_resources

    def find_ips_laser(self) -> dict:
        """
        find_ips_laser finds ips lasers available for connection through the pyvisa ressource
        manager

        Returns
        -------
        dict
            Available laser ressources connected
        """
        acm_resources = self.find_acm_devices()
        connected_lasers = {}

        for k, v in acm_resources.items():
            device = self.ressource_manage.open_resource(k)
            device.timeout = 50
            idn = device.query("*IDN?")
            if "IPS" in idn:
                connected_lasers[k] = {"ressourceInfo": v, "idn": idn.strip()}

        return connected_lasers

    def connect(self):
        """Open the serial connection to the laser."""
        try:
            rm = pyvisa.ResourceManager("@py")
            self.serial = rm.open_resource(self.comport)
            self.idn = self.serial.query("*IDN?")
            self.status = 0
            self.isconnected = True
            # time.sleep(0.5)
            return "Success"
        except Exception as e:
            return str(e)

    def disconnect(self):
        """Close the serial connection to the laser,
        disable laser if enabled."""
        try:
            self.enable(0)
            self.serial.close()
            self.status = 2
            self.isconnected = False
            self.idn = None
            return "Success"
        except Exception as e:
            return str(e)

    def identification(self):
        """Reports the device identification string. Will read back:
        IPS, HPU, laser serial number, factory measured wavelength, FW revision.

        Returns: <idn> : device identification string
        <err_code> : communication error code
        <err_message> : communication error message
        """
        self.idn, err_code, err_message = self.write_read("*IDN?")
        return self.idn, err_code, err_message

    def get_board_current(self):
        """Reports the measured current draw in mA.

        Returns: <board_current> : measured current draw in mA
        <err_code> : communication error code
        <err_message> : communication error message"""
        board_current, err_code, err_message = self.write_read("Board:Current?")
        board_current = float(board_current)
        return board_current, err_code, err_message

    def get_board_temperature(self):
        """Reports the module case temperature in °C.

        Returns: <board_temp> : module case temperature in °C
        <err_code> : communication error code
        <err_message> : communication error message"""
        board_temp, err_code, err_message = self.write_read("Board:Temperature?")
        board_temp = float(board_temp)
        return board_temp, err_code, err_message

    def set_calibrate_number(self, num_entries: int, save_state: int = 0):
        """Sets number of desired entries in the calibration Look Up Table (LUT).

        Parameters :
        <num_entries> (int) : from 2 to 9
        <save_state> (int) : 1 = store permanently, and 0 = use until next power cycle
        If no value entered for <save state> default is to 0

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write(
            "Calibrate:Number " + str(num_entries) + " " + str(save_state)
        )
        return err_code, err_message

    def get_calibrate_number(self):
        """Reports number of entries in the LUT.

        Returns: <cal_num> : number of entries in the LUT
        <err_code> : communication error code
        <err_message> : communication error message"""
        cal_num, err_code, err_message = self.write_read("Calibrate:Number?")
        cal_num = int(cal_num)
        return cal_num, err_code, err_message

    def set_calibrate_monitor(self, num: int, value: int, save_state: int = 0):
        """Sets photodiode (PD) monitor value in LUT in mV.

        Parameters:
        <num> (int) : the entry number in the LUT. Integers from 1 to 9
        <value> (int) : the value in the LUT. Integers from 0 to 3000
        <save_state> (int) : 1 = store permanently, and 0 = use until next power cycle
        If no value entered for <save state> default is to 0

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write(
            "Calibrate:Monitor " + str(num) + " " + str(value) + " " + str(save_state)
        )
        return err_code, err_message

    def get_calibrate_monitor(self, num: int):
        """Reports the PD monitor value in the requested <num> LUT entry in mV.

        Parameter: <num> (int) : the entry number in the LUT. Integers from 1 to 9

        Returns: <cal_mon> : PD monitor value in mV
        <err_code> : communication error code
        <err_message> : communication error message
        """
        cal_mon, err_code, err_message = self.write_read(
            "Calibrate:Monitor? " + str(num)
        )
        cal_mon = float(cal_mon)
        return cal_mon, err_code, err_message

    def set_calibrate_power(self, num: int, value: float, save_state: int = 0):
        """Sets LUT power value in mW.

        Parameters:
        <num> (int) : the entry number in the LUT. Integers from 1 to 9
        <value> (float) : <value> – the power value into the LUT. Floats from: 0 to 6553.5
        <save_state> (int) : 1 = store permanently, and 0 = use until next power cycle
        If no value entered for <save state> default is to 0

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write(
            "Calibrate:Power " + str(num) + " " + str(value) + " " + str(save_state)
        )
        return err_code, err_message

    def get_calibrate_power(self, num: int):
        """Reports the laser power value in the requested <num> LUT entry in mW.

        Parameter: <num> (int) : the entry number in the LUT. Integers from 1 to 9

        Returns: <cal_pow> : laser power value in the LUT in mW
        <err_code> : communication error code
        <err_message> : communication error message
        """
        cal_pow, err_code, err_message = self.write_read("Calibrate:Power? " + str(num))
        cal_pow = float(cal_pow)
        return cal_pow, err_code, err_message

    def error(self):
        """Returns the hardware error number, a sub-code, and a brief description."""
        err = self.serial.query("Error?").strip()
        return err

    def set_laser_current(self, current: float):
        """Sets laser operating current setpoint in mA.

        Parameter : <current> is the laser operating current in mA

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("Laser:Current " + str(current))
        return err_code, err_message

    def get_laser_current(self):
        """Reports measured laser operating current in mA.

        Returns: <laser_current> : measured laser operating current in mA
        <err_code> : communication error code
        <err_message> : communication error message
        """
        laser_current, err_code, err_message = self.write_read("Laser:Current?")
        self.laser_current = float(laser_current)
        return self.laser_current, err_code, err_message

    def get_laser_setpoint(self):
        """Reports the laser operating current setpoint in mA.

        Returns: <setpoint> : laser operating current setpoint in mA
        <err_code> : communication error code
        <err_message> : communication error message
        """
        setpoint, err_code, err_message = self.write_read("Laser:Setpoint?")
        return setpoint, err_code, err_message

    def enable(self, enable: int):
        """Controls whether the laser is enabled or disabled.

        Parameter : <enable> (int) : 1/ON = Enables the Laser, 0/OFF = Disables the laser

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("Laser:Enable " + str(enable))
        self.get_enable_state()  # update self.status
        return err_code, err_message

    def get_enable_state(self):
        """Reports laser enable state.

        Returns: <state> : laser enable state
        <err_code> : communication error code
        <err_message> : communication error message
        """
        state, err_code, err_message = self.write_read("Laser:Enable?")
        state = int(state)
        self.status = state
        return state, err_code, err_message

    def laser_hours(self):
        """Reports the number of hours of ON time of the laser.

        Returns: <hours> : number of hours of ON time of the laser
        <err_code> : communication error code
        <err_message> : communication error message
        """
        hours, err_code, err_message = self.write_read("Laser:Hours?")
        return hours, err_code, err_message

    def enable_analog_mode(self, enable: int):
        """Enable/Disable VBIAS input from external hardware connection on pin 8 of module.
        This function allows the user to adjust the output power of the laser
        via an external voltage bias.

        Parameter : <enable> (int): 1/ON = Enables VBIAS input to control the laser current,
        0/OFF = Disables external VBIAS input;

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("Laser:Mode:Analog " + str(enable))
        return err_code, err_message

    def get_analog_mode_state(self):
        """Reports the external VBIAS enable state.

        Returns: <state> : external VBIAS enable state
        <err_code> : communication error code
        <err_message> : communication error message
        """
        state, err_code, err_message = self.write_read("Laser:Mode:Analog?")
        return state, err_code, err_message

    def enable_digital_mode(self, enable: int):
        """Reports digital mode (PWM) enable status.

        Parameter : <enable> (int): 1 = Allows digital modulation of the laser current,
        0 = Do not allow digital modulation of the laser

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("Laser:Mode:Digital " + str(enable))
        return err_code, err_message

    def get_digital_mode_state(self, default: int = 0):
        """Reports the external VBIAS enable state.

        Parameter : <default> (int) : None or 0 to report current laser mode digital (PWM) enable
        status, 1 to report laser mode digital (PWM) factory default setting

        Returns: <state> : external VBIAS enable state
        <err_code> : communication error code
        <err_message> : communication error message
        """
        state, err_code, err_message = self.write_read(
            "Laser:Mode:Digital? " + str(default)
        )
        return state, err_code, err_message

    def set_pwm_digital_mode(self, duty_cycle: float):
        """Sets PWM percent (0 – 100) for digital mode.

        Parameter : <duty cycle> (float): PWM duty cycle in percent from 10.0% to 100%

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("Laser:Mode:PWM " + str(duty_cycle))
        return err_code, err_message

    def get_pwm_digital_mode(self, default: int = 0):
        """Reports the PWM duty cycle of laser current.

        Parameter : <default> (int) : None or 0 to report current laser PWM setting,
        1 to report factory default PWM setting

        Returns: <pmw> : PWM duty cycle of laser current
        <err_code> : communication error code
        <err_message> : communication error message
        """
        pwm, err_code, err_message = self.write_read("Laser:Mode:PWM? " + str(default))
        return pwm, err_code, err_message

    def get_laser_monitor(self):
        """Reports the monitor photodiode (PD) signal level.

        Returns: <signal> : monitor photodiode (PD) signal level
        <err_code> : communication error code
        <err_message> : communication error message
        """
        signal, err_code, err_message = self.write_read("Laser:Monitor?")
        return signal, err_code, err_message

    def get_laser_power(self):
        """Reports the Laser Power in mW as derived from the calibration Look Up Table (LUT).

        Returns: <laser_power> : laser Power in mW as derived from the calibration Look Up Table
        (LUT)
        <err_code> : communication error code
        <err_message> : communication error message
        """
        laser_power, err_code, err_message = self.write_read("Laser:Power?")
        self.laser_power = float(laser_power)
        return self.laser_power, err_code, err_message

    def get_laser_temperature(self):
        """Reports the Laser/TEC Temperature in °C.

        Returns: <laser_temp> : Laser/TEC Temperature in °C
        <err_code> : communication error code
        <err_message> : communication error message
        """
        laser_temp, err_code, err_message = self.write_read("Laser:Temperature?")
        self.laser_temp = float(laser_temp)
        return self.laser_temp, err_code, err_message

    def parameters_restore(self):
        """Restores the default power-up configuration to the IPS factory default.
        To save the default parameters, you must add a "Parameters:Save command"
        following the "Parameters:Restore" command.

        The parameters restored are: TEC_Setpoint, Laser_Drive, Laser Enable Mode,
        Analog Mode Enable, Digital Mode Enable, and PWM Duty Cycle.

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("Parameters:Restore")
        return err_code, err_message

    def parameters_save(self):
        """Saves current parameter settings to FLASH for use as default power-up configuration
        (Note: At present, there is no IPS factory “as shipped” setting,
        so it is recommended that users document parameters before changing them
        so that they can be returned to the IPS default set state if desired).

        The parameters stored to FLASH are: TEC_Setpoint, Laser_Drive, Laser Enable Mode,
        Analog Mode Enable, Digital Mode Enable and PWM Duty Cycle.

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("Parameters:Save")
        return err_code, err_message

    def get_status(self):
        """Requests the status of the digital U-type.

        Response : 2 decimal numbers; the first number represents the board state:
        0 = unknown state
        1 = board passed POST
        2 = board failed POST
        3 = board in normal state
        4 = board in fault state
        5 = board in boot load state 6 = board not attached
        The second number is the number of errors in the hardware error queue.
        Use the “ERRor?” command to read the error code and information

        Returns: <status> : status of the digital U-type
        <err_code> : communication error code
        <err_message> : communication error message
        """
        status, err_code, err_message = self.write_read("Status?")
        return status, err_code, err_message

    def system_errors_count(self):
        """Reports the number of errors in the communication error queue."""
        count = self.serial.query("System:Error:Count?").strip()
        return count

    def system_errors(self):
        # TODO: multiples errors messages
        """Requests communication errors that may have occurred.

        Returns ASCII character string containing an error number and a brief description.

        If more than one error has occurred, repeated error queries are required until
        the response is “0, No error”.
        The list of communication error numbers is available in the IPS documentation.
        """
        errors = self.serial.query("System:Error?").strip()
        return errors

    def tec_setpoint(self, temperature: float):
        """Sets the setpoint target for the TEC temperature.

        Parameters : <temperature> (float) : The set point temperature in oC degrees for the
        laserTEC.

        Acceptable values range from 10.0 to 45.0. Optimal setting is between 30°C - 35°C
        for most system configurations.

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("TEC:SETpoint " + str(temperature))
        return err_code, err_message

    def get_tec_setpoint(self, default: int = 0):
        """Reports the setpoint target for the TEC temperature.

        Parameter : <default> (int) : None or 0: Report current laser TEC temperature setting,
        1: Report factory default TEC temperature setting

        Returns: <setpoint> : setpoint target for the TEC temperature
        <err_code> : communication error code
        <err_message> : communication error message
        """
        setpoint, err_code, err_message = self.write_read(
            "TEC:SETpoint? " + str(default)
        )
        return setpoint, err_code, err_message

    def apc_enable(self, enable: int):
        """Controls whether the APC is enabled or disabled.

        Parameter : <enable> (int): 1 = Enables the Laser, 0 = Disables the laser

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("APC:Enable " + str(enable))
        return err_code, err_message

    def get_apc_enable_state(self):
        """Reports APC enable state.

        Returns: <state> : APC enable state
        <err_code> : communication error code
        <err_message> : communication error message
        """
        state, err_code, err_message = self.write_read("APC:Enable?")
        return state, err_code, err_message

    def apc_pwr_setpoint(self, power: float):
        """Sets the required power for APC control.

        Parameter : <power> (float) : Power in mW from 10 – max Power(~3000 mW)

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("APC:PWRSETPoint " + str(power))
        return err_code, err_message

    def get_apc_pwr_setpoint(self):
        """Reports Power set point in mW for APC control.

        Returns: <pwr> : Power set point in mW
        <err_code> : communication error code
        <err_message> : communication error message
        """
        pwr, err_code, err_message = self.write_read("APC:PWRSETPoint?")
        return pwr, err_code, err_message

    def set_apc_delay(self, delay: float):
        """Sets the APC Delay time.

        Parameter : <delay> (float) : time in ms. Delay in between each control loop of
        APC algorithm. Range – 100 to 5000 ms.

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("APC:DELAY " + str(delay))
        return err_code, err_message

    def get_apc_delay(self):
        """Reports the APC set delay time. Output will be in ms.

        Returns: <delay> : APC set delay time in ms
        <err_code> : communication error code
        <err_message> : communication error message
        """
        delay, err_code, err_message = self.write_read("APC:DELAY?")
        return delay, err_code, err_message

    def set_apc_spec(self, percent: float):
        """Sets the APC control Percentage.

        Parameter : <percent> (float) : Control % ranging from 0.1 to 1 %

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        err_code, err_message = self.write("APC:SPEC " + str(percent))
        return err_code, err_message

    def get_apc_spec(self):
        """Reports the APC control Percentage.

        Returns: <percent> : APC control Percentage
        <err_code> : communication error code
        <err_message> : communication error message
        """
        percent, err_code, err_message = self.write_read("APC:SPEC?")
        return percent, err_code, err_message

    def pulse(self, duration: float):
        """Creates a laser pulse by turning ON and OFF the laser.

        Parameter : <duration> (float) : duration of the pulse in mS
        """
        if self.get_enable_state()[0] == 0:
            self.enable(1)
            time.sleep(duration / 1000)
            self.enable(0)
            operation = "Success"
        else:
            operation = "Already ON"
        return operation

    def get_info(self) -> dict:
        """Returns informations about the laser as a dictionnary.
        The informations are it's status, the COM port, the laser current , power and temperature.

        Returns: <dict> : Dictionnary containing the infos.
        """
        info_dict = {}
        if self.isconnected:
            self.get_enable_state()  # update self.status
            info_dict["status"] = self.status
            info_dict["comport"] = self.comport
            info_dict["current"] = str(self.get_laser_current()[0])
            info_dict["power"] = str(self.get_laser_power()[0])
            info_dict["temperature"] = str(round(self.get_laser_temperature()[0], 1))
            info_dict["error"] = self.error()

        else:
            info_dict["status"] = self.status
            info_dict["comport"] = "None"
            info_dict["current"] = "None"
            info_dict["power"] = "None"
            info_dict["temperature"] = "None"
            info_dict["error"] = "None"

        return info_dict

    def write(self, message):
        """Sends a serial message to the laser and verifies if any communication error occured.

        Parameter : <message> (string) : Message send to the laser by serial.
        The command syntax for those messages is explained in the documentation provided by IPS.  %

        Returns:
        <err_code> : communication error code
        <err_message> : communication error message
        """
        self.serial.write(message)
        err_code, err_message = self.serial.query("System:Error?").strip().split(",")
        # TODO:
        """while self.serial.query("System:Error:Count?") != "0":
            message = self.serial.query("System:Error?").split(',')
            err_code += " & " + message[0]
            err_message += " & " + message[1]"""
        return int(err_code), err_message

    def write_read(self, x):
        """Sends a serial message to the laser, reads the answer and
        verifies if any communication error occured.

        Parameter : <message> (string) : Message send to the laser by serial.
        The command syntax for those messages is explained in the documentation provided by IPS.  %

        Returns:
        <value> (string) : Answer provided by the laser to the serial COM.
        <err_code> : communication error code
        <err_message> : communication error message
        """
        value = self.serial.query(x).strip()
        err_code, err_message = self.serial.query("System:Error?").strip().split(",")
        return value, int(err_code), err_message

    def __repr__(self) -> str:
        reprstr = f"IPSLaser(idn = '{self.idn}', \
            comport = '{self.comport}', connected = {self.isconnected})"

        return reprstr


if __name__ == "__main__":

    ips = IpsLaser()

    print("... Looking for connected lasers ...\n")
    connected_lasers = ips.find_ips_laser()

    print("Connected lasers:")
    if connected_lasers:
        for i, laser in enumerate(connected_lasers):
            print(f"\t{i}) ", laser)
        selected_laser = int(
            input(
                "\nSelect a laser (default : 0) :",
            )
            or 0
        )
        ips.comport = list(ips.find_ips_laser())[selected_laser]
    else:
        print("\tNo laser found")
        exit()

    print(f"Connecting to laser {ips.comport}")
    ips.connect()

    print(ips.identification())
    command = input("Command :")

    while command != "exit":
        if command == "enable":
            print(ips.enable(1))
            print(LASER_STATE[ips.status])
        elif command == "disable":
            print(ips.enable(0))
            print(LASER_STATE[ips.status])
        elif command == "state":
            print(ips.get_enable_state())
        elif command == "current":
            curr = float(input("value(mA) :"))
            print(ips.set_laser_current(curr))
        elif command == "current?":
            print(ips.get_laser_current())
        elif command == "pulse":
            dur = int(input("duration(ms) :"))
            print(ips.pulse(dur))
        elif command == "error":
            print(ips.error())
        elif command == "repr":
            print(repr(ips))
        command = input("Enter command :")

    ips.disconnect()
