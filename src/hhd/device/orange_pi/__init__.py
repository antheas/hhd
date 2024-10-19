from threading import Event, Thread
from typing import Any, Sequence

from hhd.controller.physical.rgb import is_led_supported
from hhd.plugins import (
    Config,
    Context,
    Emitter,
    HHDPlugin,
    get_gyro_config,
    get_outputs_config,
    load_relative_yaml,
)
from hhd.plugins.inputs import get_touchpad_config
from hhd.plugins.settings import HHDSettings

from .const import CONFS, DEFAULT_MAPPINGS, get_default_config


class GenericControllersPlugin(HHDPlugin):
    name = "orange_pi_controllers"
    priority = 18
    log = "orpi"

    def __init__(self, dmi: str, dconf: dict) -> None:
        self.t = None
        self.should_exit = None
        self.updated = Event()
        self.started = False
        self.t = None

        self.dmi = dmi
        self.dconf = dconf
        self.name = f"orange_pi_controllers@'{dconf.get('name', 'ukn')}'"

    def open(
        self,
        emit: Emitter,
        context: Context,
    ):
        self.emit = emit
        self.context = context
        self.prev = None

    def settings(self) -> HHDSettings:
        base = {"controllers": {"handheld": load_relative_yaml("controllers.yml")}}
        base["controllers"]["handheld"]["children"]["controller_mode"].update(
            get_outputs_config(
                can_disable=True,
                has_leds=is_led_supported(),
                start_disabled=self.dconf.get("untested", False),
                default_device="uinput",
            )
        )

        if self.dconf.get("touchpad", False):
            base["controllers"]["handheld"]["children"][
                "touchpad"
            ] = get_touchpad_config(dual_touchpad=True)
        else:
            del base["controllers"]["handheld"]["children"]["touchpad"]

        base["controllers"]["handheld"]["children"]["imu_axis"] = get_gyro_config(
            self.dconf.get("mapping", DEFAULT_MAPPINGS)
        )

        return base

    def update(self, conf: Config):
        new_conf = conf["controllers.handheld"]
        if new_conf == self.prev:
            return
        if self.prev is None:
            self.prev = new_conf
        else:
            self.prev.update(new_conf.conf)

        self.updated.set()
        self.start(self.prev)

    def start(self, conf):
        from .base import plugin_run

        if self.started:
            return
        self.started = True

        self.close()
        self.should_exit = Event()
        self.t = Thread(
            target=plugin_run,
            args=(
                conf,
                self.emit,
                self.context,
                self.should_exit,
                self.updated,
                self.dconf,
            ),
        )
        self.t.start()

    def close(self):
        if not self.should_exit or not self.t:
            return
        self.should_exit.set()
        self.t.join()
        self.should_exit = None
        self.t = None


def autodetect(existing: Sequence[HHDPlugin]) -> Sequence[HHDPlugin]:
    if len(existing):
        return existing

    # Match vendor first to avoid issues
    try:
        with open("/sys/class/dmi/id/sys_vendor", "r") as f:
            vendor = f.read().lower().strip()

        if "orangepi" not in vendor:
            return []
    except Exception:
        return []

    with open("/sys/devices/virtual/dmi/id/product_name", "r") as f:
        dmi = f.read().strip()

    return [GenericControllersPlugin(dmi, CONFS.get(dmi, get_default_config(dmi)))]
