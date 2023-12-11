import argparse
import logging
import select
import sys
import time
from typing import Sequence

from hhd.controller import Button, Consumer, Event, Producer
from hhd.controller.base import Multiplexer
from hhd.controller.lib.hid import enumerate_unique
from hhd.controller.physical.evdev import GenericGamepadEvdev
from hhd.controller.physical.hidraw import GenericGamepadHidraw
from hhd.controller.physical.imu import AccelImu, GyroImu
from hhd.controller.virtual.ds5 import DualSense5Edge

from .const import (
    LGO_RAW_INTERFACE_BTN_ESSENTIALS,
    LGO_RAW_INTERFACE_BTN_MAP,
    LGO_RAW_INTERFACE_CONFIG_MAP,
    LGO_TOUCHPAD_AXIS_MAP,
    LGO_TOUCHPAD_BUTTON_MAP,
)
from .hid import rgb_callback

ERROR_DELAY = 5

logger = logging.getLogger(__name__)

LEN_PID = 0x17EF
LEN_VIDS = {
    0x6182: "xinput",
    0x6183: "dinput",
    0x6184: "ddinput",
    0x6185: "fps",
}


def main(as_plugin=True):
    parser = argparse.ArgumentParser(
        prog="HHD: LegionGo Controller Plugin",
        description="This plugin remaps the legion go controllers to a DS5 controller and restores all functionality.",
    )
    parser.add_argument(
        "-a",
        "--d-accel",
        action="store_false",
        help="Dissable accelerometer (recommended since not used by steam, .5%% core utilisation).",
        dest="accel",
    )
    parser.add_argument(
        "-g",
        "--d-gyro",
        action="store_false",
        help="Disable gyroscope (.5%% core utilisation).",
        dest="gyro",
    )
    parser.add_argument(
        "-l",
        "--swap-legion",
        action="store_true",
        help="Swaps Legion buttons with start, select.",
        dest="swap_legion",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Prints events as they happen.",
        dest="debug",
    )
    if as_plugin:
        args = parser.parse_args(sys.argv[2:])
    else:
        args = parser.parse_args()

    accel = args.accel
    gyro = args.gyro
    swap_legion = args.swap_legion
    debug = args.debug

    while True:
        try:
            controller_mode = None
            while not controller_mode:
                devs = enumerate_unique(LEN_PID)
                if not devs:
                    logger.error(
                        f"Legion go controllers not found, waiting {ERROR_DELAY}s."
                    )
                    time.sleep(ERROR_DELAY)
                    continue

                for d in devs:
                    if d["product_id"] in LEN_VIDS:
                        controller_mode = LEN_VIDS[d["product_id"]]
                        break
                else:
                    logger.error(
                        f"Legion go controllers not found, waiting {ERROR_DELAY}s."
                    )
                    time.sleep(ERROR_DELAY)
                    continue

            match controller_mode:
                case "xinput":
                    logger.info("Launching DS5 controller instance.")
                    controller_loop_xinput(accel, gyro, swap_legion, debug)
                case _:
                    logger.info(
                        f"Controllers in non-supported (yet) mode: {controller_mode}. Waiting {ERROR_DELAY}s..."
                    )
                    time.sleep(ERROR_DELAY)
                    # controller_loop_rest()
        except Exception as e:
            logger.error(f"Received the following error:\n{e}")
            logger.error(
                f"Assuming controllers disconnected, restarting after {ERROR_DELAY}s."
            )
            time.sleep(ERROR_DELAY)
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, exiting...")
            return


if __name__ == "__main__":
    main(False)


def controller_loop_rest():
    pass


def controller_loop_xinput(
    accel: bool = True,
    gyro: bool = True,
    swap_legion: bool = False,
    debug: bool = False,
):
    # Output
    d_ds5 = DualSense5Edge()

    # Imu
    d_accel = AccelImu()
    d_gyro = GyroImu()

    # Inputs
    d_xinput = GenericGamepadEvdev([0x17EF], [0x6182], "Generic X-Box pad")
    d_touch = GenericGamepadEvdev(
        [0x17EF],
        [0x6182],
        ["  Legion Controller for Windows  Touchpad"],
        btn_map=LGO_TOUCHPAD_BUTTON_MAP,
        axis_map=LGO_TOUCHPAD_AXIS_MAP,
        aspect_ratio=1,
    )
    d_raw = SelectivePasshtrough(
        GenericGamepadHidraw(
            vid=[0x17EF],
            pid=[
                0x6182,  # XINPUT
                0x6183,  # DINPUT
                0x6184,  # Dual DINPUT
                0x6185,  # FPS
            ],
            usage_page=[0xFFA0],
            usage=[0x0001],
            report_size=64,
            axis_map={},
            btn_map=LGO_RAW_INTERFACE_BTN_MAP,
            config_map=LGO_RAW_INTERFACE_CONFIG_MAP,
            callback=rgb_callback,
        )
    )
    # Mute keyboard shortcuts, mute
    d_shortcuts = GenericGamepadEvdev(
        vid=[0x17EF],
        pid=[
            0x6182,  # XINPUT
            0x6183,  # DINPUT
            0x6184,  # Dual DINPUT
            0x6185,  # FPS
        ],
        name=["  Legion Controller for Windows  Keyboard"]
        # report_size=64,
    )

    multiplexer = Multiplexer(
        swap_guide="guide_is_select" if swap_legion else None,
        trigger="analog_to_discrete",
        dpad="analog_to_discrete",
        led="main_to_sides",
        status="both_to_main",
    )

    REPORT_FREQ_MIN = 25
    REPORT_FREQ_MAX = 400

    REPORT_DELAY_MAX = 1 / REPORT_FREQ_MIN
    REPORT_DELAY_MIN = 1 / REPORT_FREQ_MAX

    fds = []
    devs = []
    fd_to_dev = {}

    def prepare(m):
        fs = m.open()
        devs.append(m)
        fds.extend(fs)
        for f in fs:
            fd_to_dev[f] = m

    try:
        prepare(d_ds5)
        if accel:
            prepare(d_accel)
        if gyro:
            prepare(d_gyro)
        prepare(d_xinput)
        prepare(d_shortcuts)
        prepare(d_touch)
        prepare(d_raw)

        logger.info("DS5 controller instance launched, have fun!")
        while True:
            start = time.perf_counter()
            # Add timeout to call consumers a minimum amount of times per second
            r, _, _ = select.select(fds, [], [], REPORT_DELAY_MAX)
            evs = []
            to_run = set()
            for f in r:
                to_run.add(id(fd_to_dev[f]))

            for d in devs:
                if id(d) in to_run:
                    evs.extend(d.produce(r))

            if evs:
                evs = multiplexer.process(evs)

                if debug:
                    logger.info(evs)

                d_ds5.consume(evs)
                d_xinput.consume(evs)
                d_raw.consume(evs)

            # If unbounded, the total number of events per second is the sum of all
            # events generated by the producers.
            # For Legion go, that would be 100 + 100 + 500 + 30 = 730
            # Since the controllers of the legion go only update at 500hz, this is
            # wasteful.
            # By setting a target refresh rate for the report and sleeping at the
            # end, we ensure that even if multiple fds become ready close to each other
            # they are combined to the same report, limiting resource use.
            # Ideally, this rate is smaller than the report rate of the hardware controller
            # to ensure there is always a report from that ready during refresh
            t = time.perf_counter()
            elapsed = t - start
            if elapsed < REPORT_DELAY_MIN:
                time.sleep(REPORT_DELAY_MIN - elapsed)

    except KeyboardInterrupt:
        raise
    finally:
        for d in devs:
            d.close(True)


class SelectivePasshtrough(Producer, Consumer):
    def __init__(
        self,
        parent,
        forward_buttons: Sequence[Button] = ("share", "mode"),
        passthrough: Sequence[Button] = list(LGO_RAW_INTERFACE_BTN_ESSENTIALS[0x04]),
    ):
        self.parent = parent
        self.state = False

        self.forward_buttons = forward_buttons
        self.passthrough = passthrough

        self.to_disable = []

    def open(self) -> Sequence[int]:
        return self.parent.open()

    def close(self, exit: bool) -> bool:
        return super().close(exit)

    def produce(self, fds: Sequence[int]) -> Sequence[Event]:
        evs: Sequence[Event] = self.parent.produce(fds)

        out = []
        prev_state = self.state
        for ev in evs:
            if ev["type"] == "button" and ev["code"] in self.forward_buttons:
                self.state = ev.get("value", False)

            if ev["type"] == "configuration":
                out.append(ev)
            elif ev["type"] == "button" and ev["code"] in self.passthrough:
                out.append(ev)
            elif ev["type"] == "button" and ev.get("value", False):
                self.to_disable.append(ev["code"])

        if self.state:
            # If mode is pressed, forward all events
            return evs
        elif prev_state:
            # If prev_state, meaning the user released the mode or share button
            # turn off all buttons that were pressed during it
            for btn in self.to_disable:
                out.append({"type": "button", "code": btn, "value": False})
            self.to_disable = []
            return out
        else:
            # Otherwise, just return the standard buttons
            return out

    def consume(self, events: Sequence[Event]):
        return self.parent.consume(events)
