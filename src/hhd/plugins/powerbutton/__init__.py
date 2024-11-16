from functools import partial
import logging
from typing import TYPE_CHECKING, Any, Sequence

from hhd.plugins import Config, Context, HHDPlugin, load_relative_yaml
from . import longpress

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .const import PowerButtonConfig

from threading import Event, Thread


def run(**config: Any):
    from .base import power_button_run

    power_button_run(**config)


class PowerbuttondPlugin(HHDPlugin):
    def __init__(self, cfg: "PowerButtonConfig") -> None:
        self.name = f"powerbuttond@'{cfg.device}'"
        self.priority = 90
        self.log = "pbtn"
        self.cfg = cfg
        self.t = None
        self.stop_event = None
        self.long_press = None

    def open(
        self,
        emit,
        context: Context,
    ):
        self.started = False
        self.context = context

    def settings(self):
        d = {"hhd": load_relative_yaml("settings.yml")}
        if self.cfg.unsupported:
            d["hhd"]["settings"]["children"]["powerbuttond"]["default"] = False
        return d

    def update(self, conf: Config):
        if conf["hhd.settings.pb_longpress_hack"].to(bool):
            from .base import run_steam_longpress
            self.long_press = longpress.event
            longpress.callback = partial(run_steam_longpress, self.context)
        else:
            self.long_press = None
            longpress.callback = None

        if conf["hhd.settings.powerbuttond"].to(bool) and not self.started:
            self.start()
        elif not conf["hhd.settings.powerbuttond"].to(bool) and self.started:
            self.stop()
            logger.info('Stopping Steam Powerbutton Handler.')

    def start(self):
        from .base import power_button_run

        self.stop_event = Event()
        self.t = Thread(
            target=power_button_run, args=(self.cfg, self.context, self.stop_event, self.long_press)
        )
        self.t.start()
        self.started = True

    def stop(self):
        if not self.stop_event or not self.t:
            return
        self.stop_event.set()
        self.t.join()
        self.stop_event = None
        self.t = None
        self.started = False

    def close(self):
        self.stop()


def autodetect(existing: Sequence[HHDPlugin]) -> Sequence[HHDPlugin]:
    if len(existing):
        return existing

    from .const import get_config

    return [PowerbuttondPlugin(get_config())]
