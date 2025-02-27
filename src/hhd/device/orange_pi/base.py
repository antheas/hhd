import logging
import os
import re
import select
import time
from threading import Event as TEvent

import evdev

from hhd.controller import Multiplexer, DEBUG_MODE
from hhd.controller.base import TouchpadAction
from hhd.controller.lib.hide import unhide_all
from hhd.controller.physical.evdev import B as EC
from hhd.controller.physical.evdev import GenericGamepadEvdev
from hhd.controller.physical.imu import CombinedImu, HrtimerTrigger
from hhd.controller.physical.rgb import LedDevice
from hhd.plugins import Config, Context, Emitter, get_gyro_state, get_outputs

from .const import (
    AT_BTN_MAPPINGS,
    GAMEPAD_BTN_MAPPINGS,
    DEFAULT_MAPPINGS,
    OPI_TOUCHPAD_AXIS_MAP,
    OPI_TOUCHPAD_BUTTON_MAP,
    LEFT_TOUCHPAD_AXIS_MAP,
    LEFT_TOUCHPAD_BUTTON_MAP,
)

ERROR_DELAY = 1
SELECT_TIMEOUT = 1

logger = logging.getLogger(__name__)

GAMEPAD_VIDS = [0x045E, 0x0079]
GAMEPAD_PIDS = [0x028E, 0x181C]

KBD_VID = 0x0001
KBD_PID = 0x0001

TOUCHPAD_VID = 0x0911
TOUCHPAD_PID = 0x5288

BACK_BUTTON_DELAY = 0.1


def plugin_run(
    conf: Config,
    emit: Emitter,
    context: Context,
    should_exit: TEvent,
    updated: TEvent,
    dconf: dict,
):
    first = True
    first_disabled = True
    while not should_exit.is_set():
        if conf["controller_mode.mode"].to(str) == "disabled":
            time.sleep(ERROR_DELAY)
            if first_disabled:
                unhide_all()
            first_disabled = False
            continue
        else:
            first_disabled = True

        found_gamepad = False
        try:
            for d in evdev.list_devices():
                dev = evdev.InputDevice(d)
                if dev.info.vendor in GAMEPAD_VIDS and dev.info.product in GAMEPAD_PIDS:
                    found_gamepad = True
                    break
        except Exception:
            logger.warning("Failed finding device, skipping check.")
            found_gamepad = True

        if not found_gamepad:
            if first:
                logger.info("Controller not found. Waiting...")
            time.sleep(ERROR_DELAY)
            first = False
            continue

        try:
            logger.info("Launching emulated controller.")
            updated.clear()
            controller_loop(conf.copy(), should_exit, updated, dconf, emit)
        except Exception as e:
            logger.error(f"Received the following error:\n{type(e)}: {e}")
            logger.error(
                f"Assuming controllers disconnected, restarting after {ERROR_DELAY}s."
            )
            first = True
            # Raise exception
            if DEBUG_MODE:
                raise e
            time.sleep(ERROR_DELAY)

    # Unhide all devices before exiting
    unhide_all()

def controller_loop(
    conf: Config, should_exit: TEvent, updated: TEvent, dconf: dict, emit: Emitter
):
    debug = DEBUG_MODE
    has_touchpad = dconf.get("touchpad", False)

    # Output
    d_producers, d_outs, d_params = get_outputs(
        conf["controller_mode"],
        conf["touchpad"] if has_touchpad else None,
        conf["imu"].to(bool),
        emit=emit,
        dual_touchpad=True
    )
    motion = d_params.get("uses_motion", True) and conf.get("imu", True)

    # Imu
    d_imu = CombinedImu(
        conf["imu_hz"].to(int),
        get_gyro_state(conf["imu_axis"], dconf.get("mapping", DEFAULT_MAPPINGS)),
    )
    d_timer = HrtimerTrigger(conf["imu_hz"].to(int), [HrtimerTrigger.IMU_NAMES])

    # Inputs
    d_xinput = GenericGamepadEvdev(
        vid=GAMEPAD_VIDS,
        pid=GAMEPAD_PIDS,
        # name=["Generic X-Box pad"],
        capabilities={EC("EV_KEY"): [EC("BTN_A")]},
        required=True,
        # axis_map=DINPUT_AXIS_MAP,
        hide=True,
        # postprocess=DINPUT_AXIS_POSTPROCESS,
    )

    d_kbd_1 = GenericGamepadEvdev(
        vid=[KBD_VID],
        pid=[KBD_PID],
        required=False,
        grab=False,
        btn_map=dconf.get("at_mapping", AT_BTN_MAPPINGS),
    )

    d_kbd_2 = GenericGamepadEvdev(
        vid=GAMEPAD_VIDS,
        pid=GAMEPAD_PIDS,
        required=False,
        grab=False,
        capabilities={EC("EV_KEY"): [EC("KEY_F16")]},
        btn_map=dconf.get("gamepad_mapping", GAMEPAD_BTN_MAPPINGS),
    )

    d_touch = GenericGamepadEvdev(
        vid=[TOUCHPAD_VID],
        pid=[TOUCHPAD_PID],
        name=[re.compile("OPI0002.+Touchpad")],
        capabilities={EC("EV_KEY"): [EC("BTN_MOUSE")]},
        btn_map=OPI_TOUCHPAD_BUTTON_MAP,
        axis_map=OPI_TOUCHPAD_AXIS_MAP,
        aspect_ratio=1,
        required=True,
    )

    d_touch_left = GenericGamepadEvdev(
        vid=[TOUCHPAD_VID],
        pid=[TOUCHPAD_PID],
        name=[re.compile("OPI0001.+Touchpad")],
        capabilities={EC("EV_KEY"): [EC("BTN_MOUSE")]},
        btn_map=LEFT_TOUCHPAD_BUTTON_MAP,
        axis_map=LEFT_TOUCHPAD_AXIS_MAP,
        aspect_ratio=1,
        required=True,
    )

    # d_volume_btn = UInputDevice(
    #     name="Handheld Daemon Volume Keyboard",
    #     phys="phys-hhd-vbtn",
    #     capabilities={EC("EV_KEY"): [EC("KEY_VOLUMEUP"), EC("KEY_VOLUMEDOWN")]},
    #     btn_map={
    #         "key_volumeup": EC("KEY_VOLUMEUP"),
    #         "key_volumedown": EC("KEY_VOLUMEDOWN"),
    #     },
    #     pid=KBD_PID,
    #     vid=KBD_VID,
    #     output_timestamps=True,
    # )

    d_rgb = LedDevice()
    if d_rgb.supported:
        logger.info(f"RGB Support activated through kernel driver.")

    
    if has_touchpad:
        touch_actions = (
            conf["touchpad.controller"]
            if conf["touchpad.mode"].to(TouchpadAction) == "controller"
            else conf["touchpad.emulation"]
        )

        multiplexer = Multiplexer(
            trigger="analog_to_discrete",
            dpad="analog_to_discrete",
            share_to_qam=True,
            touchpad_short=touch_actions["short"].to(TouchpadAction),
            touchpad_hold=touch_actions["hold"].to(TouchpadAction),
            nintendo_mode=conf["nintendo_mode"].to(bool),
            emit=emit,
            params=d_params,
            qam_multi_tap=False,
        )
    else:
        multiplexer = Multiplexer(
            trigger="analog_to_discrete",
            dpad="analog_to_discrete",
            share_to_qam=True,
            nintendo_mode=conf["nintendo_mode"].to(bool),
            emit=emit,
            params=d_params,
            qam_multi_tap=False,
        )

    REPORT_FREQ_MIN = 25
    REPORT_FREQ_MAX = 400

    if motion:
        REPORT_FREQ_MAX = max(REPORT_FREQ_MAX, conf["imu_hz"].to(float))

    REPORT_DELAY_MAX = 1 / REPORT_FREQ_MIN
    REPORT_DELAY_MIN = 1 / REPORT_FREQ_MAX

    fds = []
    devs = []
    fd_to_dev = {}

    def prepare(m):
        devs.append(m)
        fs = m.open()
        fds.extend(fs)
        for f in fs:
            fd_to_dev[f] = m

    try:
        # d_vend.open()
        prepare(d_xinput)
        if motion:
            start_imu = True
            if dconf.get("hrtimer", False):
                start_imu = d_timer.open()
            if start_imu:
                prepare(d_imu)
        if has_touchpad and d_params["uses_touch"]:
            prepare(d_touch)
            prepare(d_touch_left)
        prepare(d_kbd_1)
        prepare(d_kbd_2)
        for d in d_producers:
            prepare(d)

        logger.info("Emulated controller launched, have fun!")
        while not should_exit.is_set() and not updated.is_set():
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

            evs = multiplexer.process(evs)
            if evs:
                if debug:
                    logger.info(evs)

                # d_volume_btn.consume(evs)
                d_xinput.consume(evs)

            d_rgb.consume(evs)
            for d in d_outs:
                d.consume(evs)

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
        # d_vend.close(not updated.is_set())
        try:
            d_timer.close()
        except Exception as e:
            logger.error(f"Error while closing device '{d}' with exception:\n{e}")
            if debug:
                raise e
        for d in reversed(devs):
            try:
                d.close(not updated.is_set())
            except Exception as e:
                logger.error(f"Error while closing device '{d}' with exception:\n{e}")
                if debug:
                    raise e
