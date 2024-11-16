import logging
import os
import select
import subprocess
from threading import Event
from time import perf_counter, sleep
from typing import cast

import evdev

from hhd.utils import Context, is_steam_gamepad_running, run_steam_command

from .const import PowerButtonConfig

logger = logging.getLogger(__name__)

STEAM_WAIT_DELAY = 0.5
LONG_PRESS_DELAY = 2.0
DEBOUNCE_DELAY = 1


def B(b: str):
    return cast(int, getattr(evdev.ecodes, b))


def register_power_buttons(b: PowerButtonConfig) -> list[evdev.InputDevice]:
    out = []
    for device in [evdev.InputDevice(path) for path in evdev.list_devices()]:
        capture = False
        for phys in b.phys:
            if str(device.phys).startswith(phys):
                capture = True
        if capture:
            device.grab()
            logger.info(f"Captured power button '{device.name}': '{device.phys}'")
            out.append(device)
    return out


def pick_closest_button(btns: list[evdev.InputDevice], cfg: PowerButtonConfig):
    for phys in cfg.phys:
        for b in btns:
            if str(b.phys).startswith(phys):
                return b

    if btns:
        return btns[0]
    return None


def register_hold_button(b: PowerButtonConfig) -> evdev.InputDevice | None:
    if not b.hold_phys or not b.hold_code:
        logger.error(
            f"Device configuration tuple does not contain required parameters:\n{b}"
        )
        return None

    for device in [evdev.InputDevice(path) for path in evdev.list_devices()]:
        for phys in b.hold_phys:
            if str(device.phys).startswith(phys):
                if b.hold_grab:
                    device.grab()
                logger.info(f"Captured hold keyboard '{device.name}': '{device.phys}'")
                return device
    return None


def run_steam_shortpress(perms: Context):
    return run_steam_command("steam://shortpowerpress", perms)


def run_steam_longpress(perms: Context):
    return run_steam_command("steam://longpowerpress", perms)


def power_button_run(cfg: PowerButtonConfig, ctx: Context, should_exit: Event, long_press: Event | None):
    match cfg.type:
        case "only_press":
            logger.info(
                f"Starting multi-device powerbutton handler for device '{cfg.device}'."
            )
            power_button_multidev(cfg, ctx, should_exit)
        case "hold_emitted":
            logger.info(
                f"Starting timer based powerbutton handler for device '{cfg.device}'."
            )
            power_button_timer(cfg, ctx, should_exit, long_press)
        case "hold_isa":
            logger.info(
                f"Starting isa keyboard powerbutton handler for device '{cfg.device}'."
            )
            power_button_isa(cfg, ctx, should_exit, long_press)
        case _:
            logger.error(f"Invalid type in config '{cfg.type}'. Exiting.")


def power_button_isa(cfg: PowerButtonConfig, perms: Context, should_exit: Event, long_press: Event | None):
    press_dev = None
    press_devs = []
    hold_dev = None
    try:
        while not should_exit.is_set():
            # Initial check for steam
            if not is_steam_gamepad_running(perms):
                # Close devices
                if press_devs:
                    for d in press_devs:
                        d.close()
                    press_devs = []
                if press_dev:
                    press_dev.close()
                    press_dev = None
                if hold_dev:
                    hold_dev.close()
                    hold_dev = None
                logger.info(f"Waiting for steam to launch.")
                while not is_steam_gamepad_running(perms):
                    if should_exit.is_set():
                        return
                    sleep(STEAM_WAIT_DELAY)

            if not press_dev or not hold_dev:
                logger.info(f"Steam is running, hooking power button.")
                press_devs = register_power_buttons(cfg)
                press_dev = press_devs[0] if press_devs else None
                hold_dev = register_hold_button(cfg)
            if not press_dev:
                logger.error(f"Power button interfaces not found, disabling plugin.")
                return

            # Add timeout to release the button if steam exits.
            r = select.select(
                [press_dev.fd, hold_dev.fd] if hold_dev else [press_dev.fd],
                [],
                [],
                STEAM_WAIT_DELAY,
            )[0]

            if not r:
                continue
            fd = r[0]  # handle one button at a time

            # Handle button event
            issue_systemctl = False
            if fd == press_dev.fd:
                ev = press_dev.read_one()
                if ev.type == B("EV_KEY") and ev.code == B("KEY_POWER") and ev.value:
                    if long_press is not None and long_press.is_set():
                        long_press.clear()
                        logger.info("Long press executed, stop suspend.")
                    else:
                        logger.info("Executing short press.")
                        issue_systemctl = not run_steam_shortpress(perms)
            elif hold_dev and fd == hold_dev.fd:
                ev = hold_dev.read_one()
                if ev.type == B("EV_KEY") and ev.code == cfg.hold_code and ev.value:
                    logger.info("Executing long press.")
                    issue_systemctl = not run_steam_longpress(perms)

            if issue_systemctl:
                logger.error(
                    "Power button action did not work. Calling `systemctl suspend`"
                )
                os.system("systemctl suspend")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Received exception, exitting:\n{e}")


def power_button_timer(cfg: PowerButtonConfig, perms: Context, should_exit: Event, long_press: Event | None):
    dev = None
    devs = []
    try:
        pressed_time = None
        while not should_exit.is_set():
            # Initial check for steam
            if not is_steam_gamepad_running(perms):
                # Close devices
                if devs:
                    for d in devs:
                        d.close()
                        devs = []
                    if dev:
                        dev.close()
                        dev = None
                logger.info(f"Waiting for steam to launch.")
                while not is_steam_gamepad_running(perms):
                    if should_exit.is_set():
                        return
                    sleep(STEAM_WAIT_DELAY)

            if not dev:
                logger.info(f"Steam is running, hooking power button.")
                devs = register_power_buttons(cfg)
                dev = pick_closest_button(devs, cfg)
            if not dev:
                logger.error(f"Power button not found, disabling plugin.")
                return

            # Add timeout to release the button if steam exits.
            delay = LONG_PRESS_DELAY if pressed_time else STEAM_WAIT_DELAY
            r = select.select([dev.fd], [], [], delay)[0]

            # Handle press logic
            if r:
                # Handle button event
                ev = dev.read_one()
                if ev.type == B("EV_KEY") and ev.code == B("KEY_POWER"):
                    curr_time = perf_counter()
                    if ev.value:
                        pressed_time = curr_time
                        press_type = "initial_press"
                    elif pressed_time:
                        if curr_time - pressed_time > LONG_PRESS_DELAY:
                            press_type = "long_press"
                        else:
                            press_type = "short_press"
                        pressed_time = None
                    else:
                        press_type = "release_without_press"
                else:
                    press_type = "no_press"
            elif pressed_time:
                # Button was pressed but we hit a timeout, that means
                # it is a long press
                press_type = "long_press"
                pressed_time = None
            else:
                # Otherwise, no press
                press_type = "no_press"

            issue_systemctl = False
            match press_type:
                case "long_press":
                    logger.info("Executing long press.")
                    issue_systemctl = not run_steam_longpress(perms)
                case "short_press":
                    if long_press is not None and long_press.is_set():
                        long_press.clear()
                        logger.info("Long press executed, stop suspend.")
                    else:
                        logger.info("Executing short press.")
                        issue_systemctl = not run_steam_shortpress(perms)
                case "initial_press":
                    logger.info("Power button pressed down.")
                case "release_without_press":
                    logger.error("Button released without being pressed.")

            if issue_systemctl:
                logger.error(
                    "Power button action did not work. Calling `systemctl suspend`"
                )
                os.system("systemctl suspend")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Received exception, exitting:\n{e}")
    finally:
        if dev:
            dev.close()
        if devs:
            for d in devs:
                d.close()


def power_button_multidev(cfg: PowerButtonConfig, perms: Context, should_exit: Event):
    devs = []
    fds = []
    last_pressed = None
    try:
        while not should_exit.is_set():
            # Initial check for steam
            if not is_steam_gamepad_running(perms):
                for d in devs:
                    d.close()
                devs = []
                fds = []
                logger.info(f"Waiting for steam to launch.")
                while not is_steam_gamepad_running(perms):
                    if should_exit.is_set():
                        return
                    sleep(STEAM_WAIT_DELAY)

            if not devs:
                logger.info(f"Steam is running, hooking power button.")
                devs = register_power_buttons(cfg)
                fds = {d.fd: d for d in devs}
            if not devs:
                logger.error(f"Power button(s) not found, disabling plugin.")
                return

            # Add timeout to release the button if steam exits.
            r = select.select(list(fds), [], [], STEAM_WAIT_DELAY)[0]

            # Handle press logic
            issue_power = False
            issue_systemctl = False
            for fd in r:
                # Handle button event
                ev = fds[fd].read_one()
                if (
                    ev.type == B("EV_KEY")
                    and ev.code == B("KEY_POWER")
                    and ev.value == 1
                ):
                    curr_time = perf_counter()
                    if not last_pressed or curr_time - last_pressed > DEBOUNCE_DELAY:
                        last_pressed = curr_time
                        issue_power = True

            if issue_power:
                logger.info("Executing short press.")
                issue_systemctl = not run_steam_shortpress(perms)

            if issue_systemctl:
                logger.error(
                    "Power button action did not work. Calling `systemctl suspend`"
                )
                os.system("systemctl suspend")
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Received exception, exitting:\n{e}")
    finally:
        if devs:
            for d in devs:
                d.close()
