from typing import cast, Literal

from hhd.controller import Axis

from .conf import Config
from .utils import load_relative_yaml


def get_product():
    try:
        with open("/sys/devices/virtual/dmi/id/product_name", "r") as f:
            return f.read().strip()
    except Exception:
        return "Uknown"


def get_vendor():
    try:
        with open("/sys/devices/virtual/dmi/id/board_vendor", "r") as f:
            return f.read().strip()
    except Exception:
        return "Uknown"


def get_touchpad_config(dual_touchpad: bool = False):
    conf = load_relative_yaml("touchpad.yml")
    if dual_touchpad:
        del conf["modes"]['controller']["children"]["correction"]
    return conf

def get_gyro_config(
    mapping: dict[str, tuple[Axis, str | None, float, float | None]] | None
):
    g = load_relative_yaml("gyro.yml")
    g["modes"]["remapped"]["children"]["manufacturer"]["default"] = f'"{get_vendor()}"'
    g["modes"]["remapped"]["children"]["product"]["default"] = f'"{get_product()}"'
    if mapping:
        for key, (ax, _, scale, _) in mapping.items():
            match key:
                case "anglvel_x":
                    setting = "x"
                case "anglvel_y":
                    setting = "y"
                case "anglvel_z":
                    setting = "z"
                case _:
                    setting = None
            match ax:
                case "gyro_x":
                    default = "x"
                case "gyro_y":
                    default = "y"
                case "gyro_z":
                    default = "z"
                case _:
                    default = None
            invert = scale < 0

            if setting and default:
                g["modes"]["remapped"]["children"][f"{setting}_axis"][
                    "default"
                ] = default
                g["modes"]["remapped"]["children"][f"{setting}_invert"][
                    "default"
                ] = invert
    return g


def get_gyro_state(
    conf: Config,
    default: dict[str, tuple[Axis, str | None, float, float | None]],
) -> dict[str, tuple[Axis, str | None, float, float | None]]:
    if conf["mode"].to(str) == "default":
        return default

    rem = conf.get("remapped", {})
    return {
        "timestamp": ("imu_ts", None, 1, None),
        "accel_x": (
            cast(Axis, f"accel_{rem.get('x_axis', 'x')}"),
            "accel",
            -1 if rem.get("x_invert", False) else 1,
            3,
        ),
        "accel_y": (
            cast(Axis, f"accel_{rem.get('y_axis', 'y')}"),
            "accel",
            -1 if rem.get("y_invert", False) else 1,
            3,
        ),
        "accel_z": (
            cast(Axis, f"accel_{rem.get('z_axis', 'z')}"),
            "accel",
            -1 if rem.get("z_invert", False) else 1,
            3,
        ),
        "anglvel_x": (
            cast(Axis, f"gyro_{rem.get('x_axis', 'x')}"),
            "anglvel",
            -1 if rem.get("x_invert", False) else 1,
            None,
        ),
        "anglvel_y": (
            cast(Axis, f"gyro_{rem.get('y_axis', 'y')}"),
            "anglvel",
            -1 if rem.get("y_invert", False) else 1,
            None,
        ),
        "anglvel_z": (
            cast(Axis, f"gyro_{rem.get('z_axis', 'z')}"),
            "anglvel",
            -1 if rem.get("z_invert", False) else 1,
            None,
        ),
    }


AxChoice = Literal["x", "y", "z"]


def gen_gyro_state(
    x: AxChoice, inv_x: bool, y: AxChoice, inv_y: bool, z: AxChoice, inv_z: bool
):
    return {
        "timestamp": ("imu_ts", None, 1, None),
        "accel_x": (
            cast(Axis, f"accel_{x}"),
            "accel",
            -1 if inv_x else 1,
            None,
        ),
        "accel_y": (
            cast(Axis, f"accel_{y}"),
            "accel",
            -1 if inv_y else 1,
            None,
        ),
        "accel_z": (
            cast(Axis, f"accel_{z}"),
            "accel",
            -1 if inv_z else 1,
            None,
        ),
        "anglvel_x": (
            cast(Axis, f"gyro_{x}"),
            "anglvel",
            -1 if inv_x else 1,
            None,
        ),
        "anglvel_y": (
            cast(Axis, f"gyro_{y}"),
            "anglvel",
            -1 if inv_y else 1,
            None,
        ),
        "anglvel_z": (
            cast(Axis, f"gyro_{z}"),
            "anglvel",
            -1 if inv_z else 1,
            None,
        ),
    }
