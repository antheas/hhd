import logging
from typing import Any, Literal, Mapping, Sequence

import os
from ..controller.base import Consumer, Producer, RgbMode, RgbSettings, RgbZones
from ..controller.virtual.dualsense import Dualsense, TouchpadCorrectionType
from ..controller.virtual.uinput import (
    CONTROLLER_THEMES,
    GAMEPAD_BUTTON_MAP,
    HHD_PID_TOUCHPAD,
    HORIPAD_STEAM_BUTTON_MAP,
    MOTION_AXIS_MAP,
    MOTION_AXIS_MAP_FLIP_Z,
    MOTION_CAPABILITIES,
    MOTION_INPUT_PROPS,
    TOUCHPAD_AXIS_MAP,
    TOUCHPAD_BUTTON_MAP,
    TOUCHPAD_CAPABILITIES,
    XBOX_ELITE_BUTTON_MAP,
    LEFT_TOUCHPAD_BUTTON_MAP,
    LEFT_TOUCHPAD_AXIS_MAP,
    UInputDevice,
)
from .plugin import is_steam_gamepad_running, open_steam_kbd
from .utils import load_relative_yaml

logger = logging.getLogger(__name__)

HORI_ENABLED = os.environ.get("HHD_HORI_STEAM", "0") == "1"


def get_outputs(
    conf,
    touch_conf,
    motion: bool = False,
    *,
    controller_id: int = 0,
    emit=None,
    dual_motion: bool = False,
    rgb_modes: Mapping[RgbMode, Sequence[RgbSettings]] | None = None,
    rgb_zones: RgbZones = "mono",
    controller_disabled: bool = False,
    dual_touchpad: bool = False,
) -> tuple[Sequence[Producer], Sequence[Consumer], Mapping[str, Any]]:
    producers = []
    consumers = []
    nintendo_qam = False

    controller = conf["mode"].to(str)
    desktop_disable = False
    if touch_conf is not None:
        touchpad = touch_conf["mode"].to(str)
        if dual_touchpad:
            correction = "right"
        else:
            correction = touch_conf["controller.correction"].to(TouchpadCorrectionType)
        if touchpad in ("emulation", "controller"):
            desktop_disable = touch_conf[touchpad]["desktop_disable"].to(bool)
    else:
        touchpad = "controller"
        correction = "stretch"

    # Run steam check for touchpad
    steam_check = (
        is_steam_gamepad_running(emit.ctx) if emit and desktop_disable else None
    )
    match steam_check:
        case True:
            logger.info("Gamepadui active. Activating touchpad emulation.")
        case False:
            logger.info("Gamepadui closed. Disabling touchpad emulation.")

    has_qam = False
    uses_touch = False
    uses_leds = False
    noob_mode = False
    flip_z = False

    if controller_disabled:
        controller = "hidden"

    match controller:
        case "hidden":
            # NOOP
            UInputDevice.close_cached()
            Dualsense.close_cached()
            motion = False
            noob_mode = conf.get("hidden.noob_mode", False)
        case "dualsense":
            UInputDevice.close_cached()
            flip_z = conf["dualsense.flip_z"].to(bool)
            uses_touch = touchpad == "controller" and steam_check is not False
            uses_leds = conf.get("dualsense.led_support", False)
            paddles_as = conf.get("dualsense.paddles_as", "noob")
            noob_mode = paddles_as in ("noob", "both")
            edge_mode = False

            if paddles_as == "both":
                paddles_to_clicks = "bottom"
            elif paddles_as == "touchpad":
                paddles_to_clicks = "top"
            elif paddles_as == "steam_input":
                edge_mode = True
                paddles_to_clicks = "disabled"
            else:
                paddles_to_clicks = "disabled"

            d = Dualsense(
                touchpad_method=correction,
                edge_mode=edge_mode,
                use_bluetooth=conf["dualsense.bluetooth_mode"].to(bool),
                enable_touchpad=uses_touch,
                enable_rgb=uses_leds,
                fake_timestamps=not motion,
                sync_gyro=conf["dualsense.sync_gyro"].to(bool) and motion,
                paddles_to_clicks=paddles_to_clicks,
                flip_z=flip_z,
                controller_id=controller_id | (0xF0 if edge_mode else 0),
                cache=True,
            )
            producers.append(d)
            consumers.append(d)
        case "uinput" | "xbox_elite" | "joycon_pair" | "hori_steam":
            Dualsense.close_cached()
            version = 1
            paddles_as = conf.get("uinput.paddles_as", "noob")
            if controller == "joycon_pair":
                theme = "joycon_pair"
                nintendo_qam = conf["joycon_pair.nintendo_qam"].to(bool)
                button_map = GAMEPAD_BUTTON_MAP
                bus = 0x06
                version = 0
            elif controller == "hori_steam":
                theme = "hori_steam"
                noob_mode = conf.get("hori_steam.noob_mode", False)
                flip_z = conf["hori_steam.flip_z"].to(bool)
                button_map = HORIPAD_STEAM_BUTTON_MAP
                bus = 0x06
                version = 0
                has_qam = True
            elif controller == "xbox_elite" or (
                controller == "uinput" and paddles_as == "steam_input"
            ):
                theme = "xbox_one_elite"
                button_map = XBOX_ELITE_BUTTON_MAP
                bus = 0x03
            else:
                noob_mode = paddles_as == "noob"
                # theme = conf.get("uinput.theme", "hhd")
                theme = "hhd"
                nintendo_qam = conf["uinput.nintendo_qam"].to(bool)
                # flip_z = conf["uinput.flip_z"].to(bool)
                flip_z = False
                button_map = GAMEPAD_BUTTON_MAP
                bus = 0x03 if theme == "hhd" else 0x06
            vid, pid, name = CONTROLLER_THEMES[theme]
            addr = "phys-hhd-main"
            if controller_id:
                addr = f"phys-hhd-{controller_id:02d}"
            d = UInputDevice(
                name=name,
                vid=vid,
                pid=pid,
                phys=addr,
                uniq=addr,
                btn_map=button_map,
                bus=bus,
                version=version,
                cache=True,
            )
            producers.append(d)
            consumers.append(d)
            # Deactivate motion if using an xbox theme
            motion = (theme != "hhd" and "xbox" not in theme) and motion
            if motion:
                d = UInputDevice(
                    name=f"{name} Motion Sensors",
                    vid=vid,
                    pid=pid,
                    phys=addr,
                    uniq=addr,
                    bus=bus,
                    version=version,
                    capabilities=MOTION_CAPABILITIES,
                    btn_map={},
                    axis_map=(MOTION_AXIS_MAP_FLIP_Z if flip_z else MOTION_AXIS_MAP),
                    output_imu_timestamps=True,
                    input_props=MOTION_INPUT_PROPS,
                    ignore_cmds=True,
                    cache=True,
                    motions_device=True,
                )
                producers.append(d)
                consumers.append(d)
        case _:
            raise RuntimeError(f"Invalid controller type: '{controller}'.")

    dual_motion = motion and dual_motion
    if dual_motion:
        d = Dualsense(
            edge_mode=False,
            use_bluetooth=True,
            enable_touchpad=False,
            enable_rgb=False,
            fake_timestamps=False,
            sync_gyro=True,
            paddles_to_clicks="disabled",
            flip_z=flip_z,
            controller_id=5,
            cache=True,
            left_motion=True,
        )
        producers.append(d)
        consumers.append(d)

    if touchpad == "emulation" and steam_check is not False and not controller_disabled:
        d = UInputDevice(
            name="Handheld Daemon Touchpad",
            phys="phys-hhd-main",
            capabilities=TOUCHPAD_CAPABILITIES,
            pid=HHD_PID_TOUCHPAD,
            btn_map=TOUCHPAD_BUTTON_MAP,
            axis_map=TOUCHPAD_AXIS_MAP,
            output_timestamps=True,
            ignore_cmds=True,
        )
        producers.append(d)
        consumers.append(d)
        if dual_touchpad:
            d = UInputDevice(
                name="Handheld Daemon Left Touchpad",
                phys="phys-hhd-left",
                capabilities=TOUCHPAD_CAPABILITIES,
                pid=HHD_PID_TOUCHPAD,
                btn_map=LEFT_TOUCHPAD_BUTTON_MAP,
                axis_map=LEFT_TOUCHPAD_AXIS_MAP,
                output_timestamps=True,
                ignore_cmds=True,
            )
            producers.append(d)
            consumers.append(d)
        uses_touch = True

    return (
        producers,
        consumers,
        {
            "uses_touch": uses_touch,
            "rgb_used": uses_leds,
            "rgb_modes": rgb_modes,
            "rgb_zones": rgb_zones,
            "is_dual": False,
            "steam_check": steam_check,
            "steam_check_fn": lambda: emit and is_steam_gamepad_running(emit.ctx),
            "steam_kbd": lambda open: open_steam_kbd(emit, open),
            "nintendo_qam": nintendo_qam,
            "uses_motion": motion,
            "uses_dual_motion": dual_motion,
            "noob_mode": noob_mode,
            "has_qam": has_qam,
            "supports_qam": not controller_disabled and controller != "hidden",
        },
    )


def get_outputs_config(
    can_disable: bool = False,
    has_leds: bool = True,
    start_disabled: bool = False,
    default_device: str | None = None,
    extra_buttons: Literal["none", "dual", "quad"] = "dual",
):
    s = load_relative_yaml("outputs.yml")
    try:
        if not can_disable:
            del s["modes"]["disabled"]
        if not has_leds:
            del s["modes"]["dualsense"]["children"]["led_support"]

        if extra_buttons == "none":
            del s["modes"]["dualsense"]["children"]["paddles_as"]
            del s["modes"]["uinput"]["children"]["paddles_as"]
            del s["modes"]["hidden"]["children"]["noob_mode"]
            del s["modes"]["xbox_elite"]
        elif extra_buttons == "dual":
            del s["modes"]["dualsense"]["children"]["paddles_as"]["options"]["both"]

        if HORI_ENABLED:
            # Replace xbox elite with hori
            try:
                del s["modes"]["xbox_elite"]
            except Exception:
                pass
        else:
            del s["modes"]["hori_steam"]

        # Set xbox as default for now
        s["default"] = "uinput"

        # if default_device:
        #     s["default"] = default_device
        if start_disabled:
            s["default"] = "disabled"
    except Exception as e:
        logger.exception(f"Error fixing outputs:\n{e}")
    return s


def get_limits_config(defaults: dict[str, int] = {}):
    s = load_relative_yaml("limits.yml")
    lims = s["modes"]["manual"]["children"]

    lims["ls_min"]["default"] = defaults.get("s_min", 0)
    lims["ls_max"]["default"] = defaults.get("s_max", 95)
    lims["rs_min"]["default"] = defaults.get("s_min", 0)
    lims["rs_max"]["default"] = defaults.get("s_max", 95)

    lims["rt_min"]["default"] = defaults.get("t_min", 0)
    lims["rt_max"]["default"] = defaults.get("t_max", 95)
    lims["lt_min"]["default"] = defaults.get("t_min", 0)
    lims["lt_max"]["default"] = defaults.get("t_max", 95)

    return s


def get_limits(conf, defaults={}):
    if conf["mode"].to(str) != "manual":
        return defaults

    kconf = conf["manual"]
    for set in ("ls", "rs", "lt", "rt"):
        if kconf[f"{set}_min"].to(int) > kconf[f"{set}_max"].to(int):
            kconf[f"{set}_min"] = kconf[f"{set}_max"].to(int)
    return kconf.to(dict)


def fix_limits(conf, prefix: str, defaults: dict[str, int] = {}):
    if conf[f"{prefix}.mode"].to(str) != "manual":
        return {}

    # Make sure min < max
    for set in ("ls", "rs", "lt", "rt"):
        if conf[f"{prefix}.manual.{set}_min"].to(int) > conf[
            f"{prefix}.manual.{set}_max"
        ].to(int):
            conf[f"{prefix}.manual.{set}_min"] = conf[f"{prefix}.manual.{set}_max"].to(
                int
            )

    # Allow reseting limits
    if conf[f"{prefix}.manual.reset"].to(bool):
        for set in ("l", "r"):
            for comp in ("t", "s"):
                conf[f"{prefix}.manual.{set}{comp}_min"] = defaults.get(
                    f"{comp}_min", 0
                )
                conf[f"{prefix}.manual.{set}{comp}_max"] = defaults.get(
                    f"{comp}_max", 95
                )
        conf[f"{prefix}.manual.reset"] = False
