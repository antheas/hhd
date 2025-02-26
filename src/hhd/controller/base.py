import logging
import os
import random
import select
import time
from threading import RLock
from typing import Any, Callable, Literal, Mapping, NamedTuple, Sequence, TypedDict

try:
    # Try to maintain compat with python 3.10
    from typing import NotRequired  # type: ignore
except ImportError:
    from typing import Optional as NotRequired

from .const import Axis, Button, Configuration

logger = logging.getLogger(__name__)

DEBUG_MODE = bool(os.environ.get("HHD_DEBUG", False))


class SpecialEvent(TypedDict):
    type: Literal["special"]
    event: Literal[
        "guide",
        # Builtin Controller
        "qam_single",
        "qam_predouble",
        "qam_double",
        "qam_triple",
        "qam_hold",
        "overlay",
        # Shortcuts
        "xbox_b",
        "xbox_y",
        "kbd_meta_press",
        "kbd_meta_hold",
        "swipe_left_top",
        "swipe_left_bottom",
        "swipe_right_top",
        "swipe_right_bottom",
        "swipe_bottom",
        # TDP Cycle animation
        "tdp_cycle_quiet",
        "tdp_cycle_balanced",
        "tdp_cycle_performance",
        "tdp_cycle_custom",
        # Sleep information
        "wakeup",
        # Powerbutton presses
        "pbtn_short",
        "pbtn_long",
        "pbtn_double",  # todo
        # Debug
        "restart_dev",
        "shutdown_dev",
        "refresh",
    ]
    data: "NotRequired[Any]"


class RumbleEvent(TypedDict):
    """In case ev effects is too complicated. If both magnitudes are 0, disable rumble."""

    type: Literal["rumble"]
    code: Literal["main", "left", "right"]
    strong_magnitude: float
    weak_magnitude: float


RgbMode = Literal["disabled", "solid", "pulse", "rainbow", "spiral", "duality", "oxp"]
RgbSettings = Literal[
    "color", "brightness", "speed", "brightnessd", "speedd", "direction", "dual", "oxp"
]

# Mono is a single zone (main only)
# Dual has per side RGB
# Quad has two zones per stick (Ally)
# TODO: This code needs to be refactored
RgbZones = Literal["mono", "dual", "quad"]
OxpModes = Literal[
    "monster_woke",
    "flowing",
    "sunset",
    "neon",
    "dreamy",
    "cyberpunk",
    "colorful",
    "aurora",
    "sun",
    "classic",
]


class RgbLedEvent(TypedDict):
    """Inspired by new controllers with RGB leds, especially below the buttons.

    Instead of code, this event type exposes multiple properties, including mode."""

    type: Literal["led"]
    initialize: bool

    # Controls the LED zone. Main sets all zones.
    # Left all left zones, right all right zones.
    # One and Two are used for quad zone control and three is used for per side 3 zones.
    # The third zone would be on the bumpers, such as on the Ayn Loki, if it
    # supported per zone RGB.
    code: Literal[
        "main",
        "left",
        "right",
        "left_left",
        "left_right",
        "right_left",
        "right_right",
    ]

    # Various lighting modes supported by the led.
    mode: RgbMode

    # Brightness range is from 0 to 1
    # If the response device does not support brightness control, it shall
    # devide the rgb values by the brightness and round.
    brightness: float

    # The speed the led should blink if supported by the led
    speed: float

    # For the Ally, has three brightness levels
    # (and a forth off, use disabled mode for that)
    brightnessd: Literal["low", "medium", "high"]
    speedd: Literal["low", "medium", "high"]
    direction: Literal["left", "right"]

    # Color values for the led, may be ommited depending on the mode, by being
    # set to 0
    red: int
    green: int
    blue: int

    red2: int
    green2: int
    blue2: int

    oxp: None | OxpModes


class ButtonEvent(TypedDict):
    type: Literal["button"]
    code: Button
    value: bool


class AxisEvent(TypedDict):
    type: Literal["axis"]
    code: Axis
    value: float


class ConfigurationEvent(TypedDict):
    type: Literal["configuration"]
    code: Configuration
    value: Any


class RgbCapabilities(TypedDict):
    modes: dict[RgbMode, Sequence[RgbSettings]] | None
    controller: bool
    zones: RgbZones


class ControllerCapabilities(TypedDict):
    buttons: dict  # TODO
    supports_qam: bool
    rgb: RgbCapabilities | None


Event = ButtonEvent | AxisEvent | ConfigurationEvent | RgbLedEvent | RumbleEvent

GRAB_TIMEOUT = 5

QueueEvent = tuple[Any, Sequence[Event]]


class ControllerEmitter:

    def __init__(self, ctx=None) -> None:
        self.intercept_lock = RLock()
        self._intercept = None
        self._controller_cb = None
        self._qam_cb = None
        self.ctx = ctx
        self._simple_qam = False
        self._cap = None
        self.cid = ""
        self._evs = []

    def send_qam(self, expanded: bool = False):
        with self.intercept_lock:
            if self._qam_cb:
                return self._qam_cb(expanded)
            return False

    def open_steam(self, expanded: bool = False):
        if not self.send_qam(expanded):
            return self.inject(
                {"type": "configuration", "code": "steam", "value": expanded}
            )
        return True

    def set_simple_qam(self, val: bool):
        with self.intercept_lock:
            self._simple_qam = val

    def simple_qam(self):
        with self.intercept_lock:
            return self._simple_qam

    def register_qam(self, cb: Callable[..., bool]):
        with self.intercept_lock:
            self._qam_cb = cb

    def grab(self, enable: bool):
        with self.intercept_lock:
            if enable:
                self._intercept = time.perf_counter()
            else:
                self._intercept = None

    def register_intercept(self, cb: Callable[[Any, Sequence[Event]], None]):
        with self.intercept_lock:
            self._controller_cb = cb

    def should_intercept(self):
        with self.intercept_lock:
            return self._intercept is not None

    def intercept(self, cid: Any, evs: Sequence[Event]):
        with self.intercept_lock:
            if self._intercept:
                if self._intercept + GRAB_TIMEOUT < time.perf_counter():
                    logger.error(
                        f"Intercept timeout triggered, deactivating controller grab."
                    )
                    self.grab(False)
                    return False
                elif evs and self._controller_cb:
                    self._controller_cb(cid, evs)
                    return True
                else:
                    return False
            else:
                return False

    def inject(self, ev: Sequence[Event] | Event):
        if not isinstance(ev, Sequence):
            ev = [ev]
        with self.intercept_lock:
            if not self.cid or (self._cap and not self._cap.get("supports_qam", True)):
                # Avoid writing events if no controller is connected
                return False
            for e in ev:
                self._evs.append((e, 0))
        return True

    def inject_timed(self, evs: Sequence[tuple[Event, float]]):
        # Unfortunately here we have to clear the previous events to avoid conflicts
        # TODO: Clean this up. It is only used by the RGB module.
        with self.intercept_lock:
            self._evs = list(evs)

    def inject_recv(self):
        with self.intercept_lock:
            if not self.cid:
                # Avoid writing events if no controller is connected
                return []

            if not self._evs:
                return []

            curr = time.time()
            removed = []
            tmp = []
            for i, (ev, t) in enumerate(self._evs):
                if curr >= t:
                    tmp.append(ev)
                    removed.insert(0, i)  # prepend to remove in opposite order

            for i in removed:
                self._evs.pop(i)
            return tmp

    def set_capabilities(self, cid, cap: ControllerCapabilities | None):
        with self.intercept_lock:
            self._cap = cap
            self.cid = cid

    def get_capabilities(self) -> dict[str, ControllerCapabilities]:
        with self.intercept_lock:
            if self._cap:
                return {self.cid: self._cap}
            return {}

    def __call__(self, event: SpecialEvent | Sequence[SpecialEvent]) -> None:
        pass


class TouchpadCorrection(NamedTuple):
    x_mult: float = 1
    x_ofs: float = 0
    x_clamp: tuple[float, float] = (0, 1)
    y_mult: float = 1
    y_ofs: float = 0
    y_clamp: tuple[float, float] = (0, 1)


TouchpadCorrectionType = Literal[
    "stretch",
    "crop_center",
    "crop_start",
    "crop_end",
    "contain_start",
    "contain_end",
    "contain_center",
    "left",
    "right",
    "center",
    "disabled",
]


def correct_touchpad(
    width: int, height: int, aspect: float, method: TouchpadCorrectionType
):
    dst = width / height
    src = aspect
    ratio = dst / src

    match method:
        case "left":
            if ratio > 2:
                new_width = width / ratio
                return TouchpadCorrection(
                    x_mult=new_width,
                    x_ofs=0,
                    y_mult=height,
                    y_ofs=0,
                )
            else:
                new_height = height * ratio / 2
                return TouchpadCorrection(
                    x_mult=width / 2,
                    x_ofs=0,
                    y_mult=new_height,
                    y_ofs=(height - new_height),
                )
        case "right":
            if ratio > 2:
                new_width = width / ratio
                return TouchpadCorrection(
                    x_mult=new_width,
                    x_ofs=(width - new_width),
                    y_mult=height,
                    y_ofs=0,
                )
            else:
                new_height = height * ratio / 2
                return TouchpadCorrection(
                    x_mult=width / 2,
                    x_ofs=width / 2,
                    y_mult=new_height,
                    y_ofs=(height - new_height),
                )
        case "center":
            if ratio > 1:
                new_width = width / ratio
                return TouchpadCorrection(
                    x_mult=new_width,
                    x_ofs=(width - new_width) / 2,
                    y_mult=height,
                    y_ofs=0,
                )
            else:
                new_height = height * ratio
                return TouchpadCorrection(
                    x_mult=width,
                    x_ofs=0,
                    y_mult=new_height,
                    y_ofs=(height - new_height) / 2,
                )
        case "crop_center":
            if ratio > 1:
                new_width = width / ratio
                return TouchpadCorrection(
                    x_mult=new_width,
                    x_ofs=(width - new_width) / 2,
                    y_mult=height,
                    y_ofs=0,
                )
            else:
                new_height = height * ratio
                return TouchpadCorrection(
                    x_mult=width,
                    x_ofs=0,
                    y_mult=new_height,
                    y_ofs=(height - new_height) / 2,
                )
        case "crop_start":
            if ratio > 1:
                new_width = width / ratio
                return TouchpadCorrection(
                    x_mult=new_width,
                    x_ofs=0,
                    y_mult=height,
                    y_ofs=0,
                )
            else:
                new_height = height * ratio
                return TouchpadCorrection(
                    x_mult=width,
                    x_ofs=0,
                    y_mult=new_height,
                    y_ofs=0,
                )
        case "crop_end":
            if ratio > 1:
                new_width = width / ratio
                return TouchpadCorrection(
                    x_mult=new_width,
                    x_ofs=(width - new_width),
                    y_mult=height,
                    y_ofs=0,
                )
            else:
                new_height = height * ratio
                return TouchpadCorrection(
                    x_mult=width,
                    x_ofs=0,
                    y_mult=new_height,
                    y_ofs=(height - new_height),
                )
        case "contain_center":
            if ratio > 1:
                bound = (ratio - 1) / ratio / 2
                return TouchpadCorrection(
                    x_mult=width, y_mult=height, y_clamp=(bound, 1 - bound)
                )
            else:
                bound = (1 - ratio) / 2
                return TouchpadCorrection(
                    x_mult=width, y_mult=height, x_clamp=(bound, 1 - bound)
                )
        case "contain_start":
            if ratio > 1:
                bound = (ratio - 1) / ratio
                return TouchpadCorrection(
                    x_mult=width, y_mult=height, y_clamp=(0, 1 - bound)
                )
            else:
                bound = (1 - ratio) / 2
                return TouchpadCorrection(
                    x_mult=width, y_mult=height, x_clamp=(0, 1 - bound)
                )
        case "contain_end":
            if ratio > 1:
                bound = (ratio - 1) / ratio
                return TouchpadCorrection(
                    x_mult=width, y_mult=height, y_clamp=(bound, 1)
                )
            else:
                bound = (1 - ratio) / 2
                return TouchpadCorrection(
                    x_mult=width, y_mult=height, x_clamp=(bound, 1)
                )
        case "stretch" | "disabled":
            return TouchpadCorrection(x_mult=width, y_mult=height)

    logger.error(f"Touchpad correction method '{method}' not found.")
    return TouchpadCorrection(x_mult=width, y_mult=height)


class Producer:
    def open(self) -> Sequence[int]:
        """Opens and returns a list of file descriptors that should be listened to."""
        raise NotImplementedError()

    def close(self, exit: bool) -> bool:
        """Called to close the device.

        If `exit` is true, the program is about to
        close. If it is false, the controller may be performing a configuration
        change.

        In the first versions of Handheld Daemon, this API was meant to be used
        for the controller to enter power saving mode. However, it turns out
        that steam and the kernel do not let the controller disconnect,
        so it was repurposed to skip controller hiding."""
        return False

    def produce(self, fds: Sequence[int]) -> Sequence[Event]:
        """Called with the file descriptors that are ready to read."""
        return []


class Consumer:
    available: bool
    """Hint that states if the consumer can receive events. If it is false,
    consumer will not be called. If all consumers are false, producers will
    be closed to save CPU utilisation."""

    def initialize(self):
        """Optional method for initialization."""
        pass

    def consume(self, events: Sequence[Event]):
        pass


TouchpadAction = Literal["disabled", "left_click", "right_click"]


class Multiplexer:
    QAM_HOLD_TIME = 0.4
    QAM_MULTI_PRESS_DELAY = 0.2
    QAM_TAP_TIME = 0.04
    QAM_DELAY = 0.15
    REBOOT_HOLD_SELECT = 9
    REBOOT_HOLD_TURBO = 4
    REBOOT_VIBRATION_STRENGTH = 1
    REBOOT_VIBRATION_ON = 0.4
    REBOOT_VIBRATION_OFF = 1.2
    REBOOT_VIBRATION_NUM = 3
    STEAM_CHECK_INTERVAL = 3
    STARTSELECT_TRIGGER_THRESHOLD = 0.6

    def __init__(
        self,
        swap_guide: (
            None
            | Literal[
                "guide_is_start",
                "guide_is_select",
                "select_is_guide",
                "start_is_keyboard",
            ]
        ) = None,
        trigger: None | Literal["analog_to_discrete", "discrete_to_analogue"] = None,
        dpad: (
            None
            | Literal["analog_to_discrete"]
            | Literal["discrete_to_analog"]
            | Literal["both"]
        ) = None,
        led: None | Literal["left_to_main", "right_to_main", "main_to_sides"] = None,
        touchpad: (
            None | Literal["left_to_main", "right_to_main", "main_to_sides"]
        ) = None,
        status: None | Literal["both_to_main"] = None,
        share_to_qam: bool = False,
        trigger_discrete_lvl: float = 0.99,
        touchpad_short: TouchpadAction = "disabled",
        touchpad_right: TouchpadAction = "left_click",
        touchpad_hold: TouchpadAction = "disabled",
        r3_to_share: bool = False,
        select_reboots: bool = False,
        share_reboots: bool = False,
        nintendo_mode: bool = False,
        qam_button: str | None = None,
        emit: ControllerEmitter | None = None,
        imu: None | Literal["left_to_main", "right_to_main", "main_to_sides"] = None,
        params: Mapping[str, Any] = {},
        qam_multi_tap: bool = True,
        qam_no_release: bool = False,
        qam_hhd: bool = False,
        qam_hold: Literal["hhd", "mode"] = "hhd",
        keyboard_is: Literal["steam_qam", "qam", "keyboard"] = "keyboard",
        keyboard_no_release: bool = False,
        startselect_chord: str = "disabled",
    ) -> None:
        self.swap_guide = swap_guide
        self.guide_to_paddles = os.environ.get('HHD_GUIDE_TO_PADDLES', False)
        self.trigger = trigger
        self.dpad = dpad
        self.led = led
        self.touchpad = touchpad
        self.status = status
        self.trigger_discrete_lvl = trigger_discrete_lvl
        self.touchpad_short = touchpad_short
        self.touchpad_hold = touchpad_hold
        self.touchpad_right = touchpad_right
        self.reboot_button = None
        if select_reboots:
            self.reboot_button = "select"
            self.reboot_time = self.REBOOT_HOLD_SELECT
        if share_reboots:
            self.reboot_button = "share"
            self.reboot_time = self.REBOOT_HOLD_TURBO
        self.r3_to_share = r3_to_share
        self.nintendo_mode = nintendo_mode
        self.emit = emit
        self.send_xbox_b = None
        self.imu = imu
        self.qam_hhd = qam_hhd
        self.qam_hold = qam_hold
        self.keyboard_is = keyboard_is
        self.keyboard_no_release = keyboard_no_release
        self.startselect_chord = startselect_chord
        self.startselect_pressed = None

        self.state = {}
        self.touchpad_x = 0
        self.touchpad_y = 0
        self.touchpad_down = None
        self.queue: list[tuple[Event | Literal["reboot"], float]] = []
        self.reboot_pressed = None
        self.select_is_held = False
        self.reboot_is_held = False
        self.qam_kbd = False
        self.qam_button = qam_button
        if share_to_qam:
            self.qam_button = "share"
        self.has_qam = params.get("has_qam", False)

        self.noob_mode = params.get("noob_mode", False)
        self.qam_pressed = None
        self.qam_pre_sent = False
        self.qam_released = None
        self.qam_times = 0
        self.qam_multi_tap = qam_multi_tap
        self.qam_no_release = qam_no_release
        self.qam_simple = os.environ.get("HHD_QAM_MULTI_DISABLE", None) or (
            self.emit and self.emit.simple_qam()
        )
        self.guide_pressed = False
        self.steam_check = params.get("steam_check", None)
        self.steam_check_last = time.perf_counter()
        self.steam_check_fn = params.get("steam_check_fn", None)
        self.nintendo_qam = params.get("nintendo_qam", False)
        self.open_steam_kbd = params.get("steam_kbd", lambda open: False)

        self.unique = str(time.perf_counter_ns())
        assert touchpad is None, "touchpad rewiring not supported yet"

        uses_rgb: bool = params.get("rgb_used", False)
        rgb_modes: dict[RgbMode, Sequence[RgbSettings]] | None = params.get(
            "rgb_modes", None
        )
        rgb_zones: RgbZones = params.get("rgb_zones", "mono")
        if self.emit:
            rgb = None
            if rgb_modes:
                rgb: RgbCapabilities | None = {
                    "modes": rgb_modes,
                    "controller": uses_rgb,
                    "zones": rgb_zones,
                }
            self.emit.set_capabilities(
                self.unique,
                {
                    "buttons": {},
                    "rgb": rgb,
                    "supports_qam": params.get("supports_qam", True),
                },
            )

    def process(self, events: Sequence[Event]) -> Sequence[Event]:
        out: list[Event] = []
        status_events = set()
        touched = False
        send_steam_qam = False
        send_steam_expand = False

        curr = time.perf_counter()

        # Send old events
        while len(self.queue) and self.queue[0][1] < curr:
            ev = self.queue.pop(0)[0]
            if ev == "reboot":
                if self.reboot_is_held:
                    try:
                        import os

                        os.system("systemctl reboot")
                        logger.info("rebooting")
                    except Exception as e:
                        logger.error(f"Rebooting failed with error:\n{type(e)}:{e}")
            elif self.reboot_is_held or not ev.get("from_reboot", False):
                out.append({**ev, "from_queue": True})  # type: ignore

        # Check for steam for touchpad emulation
        if (
            self.steam_check_fn
            and self.steam_check is not None
            and self.steam_check_last + Multiplexer.STEAM_CHECK_INTERVAL < curr
        ):
            self.steam_check_last = curr
            if self.steam_check:
                msg = "Gamepadui closed. Restarting controller to disable touchpad emulation."
            else:
                msg = "Gamepadui launched. Restarting controller to enable touchpad emulation."

            assert self.steam_check_fn() == self.steam_check, msg

        if self.reboot_pressed and self.reboot_pressed + self.reboot_time < curr:
            self.reboot_pressed = None
            for i in range(self.REBOOT_VIBRATION_NUM):
                self.queue.append(
                    (
                        {
                            "type": "rumble",
                            "code": "main",
                            "strong_magnitude": self.REBOOT_VIBRATION_STRENGTH,
                            "weak_magnitude": self.REBOOT_VIBRATION_STRENGTH,
                            "from_reboot": True,
                        },  # type: ignore
                        curr
                        + i * (self.REBOOT_VIBRATION_ON + self.REBOOT_VIBRATION_OFF),
                    )
                )
                self.queue.append(
                    (
                        {
                            "type": "rumble",
                            "code": "main",
                            "strong_magnitude": 0,
                            "weak_magnitude": 0,
                            "from_reboot": True,
                        },  # type: ignore
                        curr
                        + i * (self.REBOOT_VIBRATION_ON + self.REBOOT_VIBRATION_OFF)
                        + self.REBOOT_VIBRATION_ON,
                    )
                )
            self.queue.append(("reboot", curr))

        if (
            self.touchpad_hold != "disabled"
            and self.touchpad_down
            and self.touchpad_down[3]
            and curr - self.touchpad_down[0] > 0.8
        ):
            action = (
                "touchpad_left"
                if self.touchpad_hold == "left_click"
                else "touchpad_right"
            )
            self.queue.append(
                (
                    {
                        "type": "button",
                        "code": action,
                        "value": True,
                    },
                    curr,
                )
            )
            self.queue.append(
                (
                    {
                        "type": "button",
                        "code": action,
                        "value": False,
                    },
                    curr + self.QAM_DELAY,
                )
            )
            self.touchpad_down = None
        elif self.touchpad_down and (
            abs(self.touchpad_down[1] - self.touchpad_x) > 0.13
            or abs(self.touchpad_down[2] - self.touchpad_y) > 0.13
        ):
            self.touchpad_down[3] = False

        for ev in events:
            match ev["type"]:
                case "axis":
                    match self.imu:
                        case "left_to_main":
                            match ev["code"]:
                                case "left_accel_x":
                                    ev["code"] = "accel_x"
                                case "left_accel_y":
                                    ev["code"] = "accel_y"
                                case "left_accel_z":
                                    ev["code"] = "accel_z"
                                case "left_gyro_x":
                                    ev["code"] = "gyro_x"
                                case "left_gyro_y":
                                    ev["code"] = "gyro_y"
                                case "left_gyro_z":
                                    ev["code"] = "gyro_z"
                                case "left_imu_ts":
                                    ev["code"] = "imu_ts"
                        case "right_to_main":
                            match ev["code"]:
                                case "right_accel_x":
                                    ev["code"] = "accel_x"
                                case "right_accel_y":
                                    ev["code"] = "accel_y"
                                case "right_accel_z":
                                    ev["code"] = "accel_z"
                                case "right_gyro_x":
                                    ev["code"] = "gyro_x"
                                case "right_gyro_y":
                                    ev["code"] = "gyro_y"
                                case "right_gyro_z":
                                    ev["code"] = "gyro_z"
                                case "right_imu_ts":
                                    ev["code"] = "imu_ts"
                        case "main_to_sides":
                            match ev["code"]:
                                case "accel_x":
                                    ev["code"] = "right_accel_x"
                                    ev["code"] = "left_accel_x"
                                case "accel_y":
                                    ev["code"] = "right_accel_y"
                                    ev["code"] = "left_accel_y"
                                case "accel_z":
                                    ev["code"] = "right_accel_z"
                                    ev["code"] = "left_accel_z"
                                case "gyro_x":
                                    ev["code"] = "right_gyro_x"
                                    ev["code"] = "left_gyro_x"
                                case "gyro_y":
                                    ev["code"] = "right_gyro_y"
                                    ev["code"] = "left_gyro_y"
                                case "gyro_z":
                                    ev["code"] = "right_gyro_z"
                                    ev["code"] = "left_gyro_z"
                                case "imu_ts":
                                    ev["code"] = "right_imu_ts"
                                    ev["code"] = "left_imu_ts"

                    if (
                        self.startselect_pressed == "wait"
                        and ev["code"]
                        in (
                            "lt",
                            "rt",
                            "hat_x",
                            "hat_y",
                        )
                        and abs(ev["value"]) > self.STARTSELECT_TRIGGER_THRESHOLD
                    ):
                        out.append(
                            {
                                "type": "button",
                                "code": "mode",
                                "value": True,
                            }
                        )
                        self.startselect_pressed = "pressed"
                    if self.startselect_pressed == "pressed":
                        self.queue.append(
                            (
                                {
                                    "type": "axis",
                                    "code": ev["code"],
                                    "value": ev["value"],
                                },
                                curr + self.QAM_DELAY,
                            )
                        )
                        ev["code"] = ""  # type: ignore

                    if self.trigger == "analog_to_discrete" and ev["code"] in (
                        "lt",
                        "rt",
                    ):
                        out.append(
                            {
                                "type": "button",
                                "code": ev["code"],
                                "value": ev["value"] > self.trigger_discrete_lvl,
                            }
                        )

                    if (
                        self.dpad == "analog_to_discrete" or self.dpad == "both"
                    ) and ev["code"] in (
                        "hat_x",
                        "hat_y",
                    ):
                        out.append(
                            {
                                "type": "button",
                                "code": (
                                    "dpad_down"
                                    if ev["code"] == "hat_y"
                                    else "dpad_right"
                                ),
                                "value": ev["value"] > 0.5,
                            }
                        )
                        out.append(
                            {
                                "type": "button",
                                "code": (
                                    "dpad_up" if ev["code"] == "hat_y" else "dpad_left"
                                ),
                                "value": ev["value"] < -0.5,
                            }
                        )
                    if ev["code"] == "touchpad_x":
                        self.touchpad_x = ev["value"]
                    if ev["code"] == "touchpad_y":
                        self.touchpad_y = ev["value"]
                case "button":
                    if self.trigger == "discrete_to_analog" and ev["code"] in (
                        "lt",
                        "rt",
                    ):
                        out.append(
                            {
                                "type": "axis",
                                "code": ev["code"],
                                "value": 1 if ev["value"] else 0,
                            }
                        )

                    if ev["code"] == "select":
                        if ev["value"]:
                            self.select_is_held = True
                        else:
                            self.select_is_held = False

                    if self.reboot_button and ev["code"] == self.reboot_button:
                        if ev["value"]:
                            self.reboot_pressed = curr
                            self.reboot_is_held = True
                        else:
                            self.reboot_pressed = None
                            self.reboot_is_held = False

                    if self.swap_guide and ev["code"] in (
                        "start",
                        "select",
                        "mode",
                        "share",
                        "keyboard",
                    ):
                        match ev["code"]:
                            # TODO: Refactor the logic of this file,
                            # the arguments do not make sense.
                            case "start":
                                match self.swap_guide:
                                    case "start_is_keyboard":
                                        ev["code"] = "keyboard"
                                    case "select_is_guide":
                                        ev["code"] = "share"
                                    case _:
                                        ev["code"] = "mode"
                            case "select":
                                match self.swap_guide:
                                    case "start_is_keyboard":
                                        ev["code"] = "mode"
                                    case "select_is_guide":
                                        ev["code"] = "mode"
                                    case _:
                                        ev["code"] = "share"
                            case "mode":
                                if self.swap_guide == "guide_is_start":
                                    ev["code"] = "start"
                                else:
                                    ev["code"] = "select"
                            case "share":
                                match self.swap_guide:
                                    case "start_is_keyboard":
                                        pass
                                    case "guide_is_start":
                                        ev["code"] = "select"
                                    case _:
                                        ev["code"] = "start"
                            case "keyboard":
                                if self.swap_guide == "start_is_keyboard":
                                    ev["code"] = "start"

                    if self.guide_to_paddles:
                        if ev["code"] == "mode":
                            ev["code"] = "extra_l2"
                        elif ev["code"] == "share":
                            ev["code"] = "extra_r2"
                    
                    if (
                        self.startselect_chord != "disabled" and ev["code"] == "select"
                    ) or (
                        self.startselect_chord == "start_select"
                        and ev["code"] == "start"
                    ):
                        if self.startselect_pressed == "pressed":
                            self.queue.append(
                                (
                                    {
                                        "type": "button",
                                        "code": "mode",
                                        "value": False,
                                    },
                                    curr + self.QAM_DELAY,
                                )
                            )
                            self.startselect_pressed = None

                        if ev["value"]:
                            self.startselect_pressed = "wait"
                        elif self.startselect_pressed == "wait":
                            self.startselect_pressed = None
                            out.append(
                                {
                                    "type": "button",
                                    "code": ev["code"],
                                    "value": True,
                                }
                            )
                            self.queue.append(
                                (
                                    {
                                        "type": "button",
                                        "code": ev["code"],
                                        "value": False,
                                    },
                                    curr + self.QAM_DELAY,
                                )
                            )
                        ev["code"] = ""  # type: ignore

                    if self.emit and ev["code"] == "mode":
                        # Steam might do weirdness, emit an event to prepare
                        # the overlay
                        self.guide_pressed = ev["value"]
                        if ev["value"]:
                            self.emit({"type": "special", "event": "guide"})

                    if (
                        self.dpad == "discrete_to_analog" or self.dpad == "both"
                    ) and ev["code"] in (
                        "dpad_up",
                        "dpad_down",
                        "dpad_left",
                        "dpad_right",
                    ):
                        # FIXME: To be done properly you'd need to save the previous
                        # state so that if going from -1 to 1 in one go it would be
                        # preserved. Since this is only used for the legion go
                        # passthrough that is not an issue.
                        match ev["code"]:
                            case "dpad_up":
                                code = "hat_y"
                                val = -1
                            case "dpad_down":
                                code = "hat_y"
                                val = 1
                            case "dpad_right":
                                code = "hat_x"
                                val = 1
                            case "dpad_left":
                                code = "hat_x"
                                val = -1

                        out.append(
                            {
                                "type": "axis",
                                "code": code,
                                "value": ev["value"] * val,
                            }
                        )

                    if (
                        self.qam_button is not None and ev["code"] == self.qam_button
                    ) or (self.keyboard_is == "qam" and ev["code"] == "keyboard"):
                        self.qam_kbd = ev["code"] == "keyboard"
                        ev["code"] = ""  # type: ignore
                        if not self.qam_simple:
                            if (not self.qam_kbd and self.qam_no_release) or (
                                self.qam_kbd and self.keyboard_no_release
                            ):
                                # Fix for the ally having no hold event
                                if ev["value"]:
                                    self.qam_times += 1
                                    self.qam_released = curr + self.QAM_TAP_TIME
                                    self.qam_pressed = None
                            else:
                                if ev["value"]:
                                    self.qam_times += 1
                                    self.qam_pressed = curr
                                    self.qam_released = None
                                else:
                                    # Only apply if qam_pressed was not yanked
                                    if self.qam_pressed:
                                        self.qam_released = curr
                                    self.qam_pressed = None
                        else:
                            if self.has_qam:
                                out.append(
                                    {
                                        "type": "button",
                                        "code": "share",
                                        "value": ev["value"],
                                    },
                                )
                            else:
                                if ev["value"]:
                                    out.append(
                                        {
                                            "type": "button",
                                            "code": "mode",
                                            "value": True,
                                        },
                                    )
                                    self.queue.append(
                                        (
                                            {
                                                "type": "button",
                                                "code": (
                                                    "b" if self.nintendo_qam else "a"
                                                ),
                                                "value": True,
                                            },
                                            curr + self.QAM_DELAY,
                                        ),
                                    )
                                    self.queue.append(
                                        (
                                            {
                                                "type": "button",
                                                "code": (
                                                    "b" if self.nintendo_qam else "a"
                                                ),
                                                "value": False,
                                            },
                                            curr + 2 * self.QAM_DELAY,
                                        ),
                                    )
                                    self.queue.append(
                                        (
                                            {
                                                "type": "button",
                                                "code": "mode",
                                                "value": False,
                                            },
                                            curr + 2 * self.QAM_DELAY,
                                        ),
                                    )

                    if ev["code"] == "keyboard":
                        if ev["value"]:
                            if self.keyboard_is == "steam_qam":
                                logger.info(f"Keyboard button opens QAM.")
                                send_steam_qam = True
                            elif self.keyboard_is == "keyboard":
                                self.open_steam_kbd(True)
                        ev["code"] = ""

                    if self.noob_mode and ev["code"] == "extra_l1" and ev["value"]:
                        ev["code"] = ""  # type: ignore
                        if self.open_steam_kbd(True):
                            logger.info(f"Opened steam keyboard directly.")
                        else:
                            logger.warning(
                                f"Could not open steam keyboard directly. Sending chord."
                            )
                            out.append(
                                {
                                    "type": "button",
                                    "code": "mode",
                                    "value": True,
                                },
                            )
                            self.queue.append(
                                (
                                    {
                                        "type": "button",
                                        "code": "y" if self.nintendo_qam else "x",
                                        "value": True,
                                    },
                                    curr + self.QAM_DELAY,
                                )
                            )
                            self.queue.append(
                                (
                                    {
                                        "type": "button",
                                        "code": "y" if self.nintendo_qam else "x",
                                        "value": False,
                                    },
                                    curr + 2 * self.QAM_DELAY,
                                ),
                            )
                            self.queue.append(
                                (
                                    {
                                        "type": "button",
                                        "code": "mode",
                                        "value": False,
                                    },
                                    curr + 2 * self.QAM_DELAY,
                                ),
                            )

                    if self.noob_mode and ev["code"] == "extra_r1" and ev["value"]:
                        ev["code"] = ""
                        if self.emit:
                            self.emit({"type": "special", "event": "overlay"})

                    if ev["code"] == "touchpad_right":
                        match self.touchpad_right:
                            case "disabled":
                                # TODO: Cleanup
                                ev["code"] = ""  # type: ignore
                            case "left_click":
                                ev["code"] = "touchpad_left"
                            case "right_click":
                                pass

                    if ev["code"] == "touchpad_touch":
                        if (
                            self.touchpad_short != "disabled"
                            and not ev["value"]
                            and self.touchpad_down
                            and curr - self.touchpad_down[0] < 0.2
                            and abs(self.touchpad_down[1] - self.touchpad_x) < 0.04
                            and abs(self.touchpad_down[2] - self.touchpad_y) < 0.04
                        ):
                            action = (
                                "touchpad_left"
                                if self.touchpad_short == "left_click"
                                else "touchpad_right"
                            )
                            self.queue.append(
                                (
                                    {
                                        "type": "button",
                                        "code": action,
                                        "value": True,
                                    },
                                    curr,
                                )
                            )
                            self.queue.append(
                                (
                                    {
                                        "type": "button",
                                        "code": action,
                                        "value": False,
                                    },
                                    curr + self.QAM_DELAY,
                                )
                            )

                        if ev["value"]:
                            touched = True
                        else:
                            self.touchpad_down = None
                        # append A after QAM_DELAY s

                    if self.r3_to_share and ev["code"] == "extra_r3":
                        ev["code"] = "share"

                    if self.nintendo_mode:
                        match ev["code"]:
                            case "a":
                                ev["code"] = "b"
                            case "b":
                                ev["code"] = "a"
                            case "x":
                                ev["code"] = "y"
                            case "y":
                                ev["code"] = "x"

                    # Assume we own Xbox + Y if the user is not using the recording feature
                    if (
                        (self.guide_pressed or self.select_is_held)
                        and self.emit
                        and ev["code"] == "y"
                        and ev["value"]
                    ):
                        self.emit({"type": "special", "event": "xbox_y"})

                    # Assume we can only use Xbox + B for short presses
                    if (
                        (self.guide_pressed or self.select_is_held)
                        and self.emit
                        and ev["code"] == "b"
                    ):
                        if ev["value"]:
                            self.send_xbox_b = time.time()
                        else:
                            if (
                                self.send_xbox_b
                                and time.time() - self.send_xbox_b < 0.3
                            ):
                                self.emit({"type": "special", "event": "xbox_b"})
                            self.send_xbox_b = None

                    # Apply start/select qam
                    if self.startselect_pressed == "wait" and ev["code"]:
                        out.append(
                            {
                                "type": "button",
                                "code": "mode",
                                "value": True,
                            }
                        )
                        self.startselect_pressed = "pressed"
                    if self.startselect_pressed == "pressed":
                        self.queue.append(
                            (
                                {
                                    "type": "button",
                                    "code": ev["code"],
                                    "value": ev["value"],
                                },
                                curr + self.QAM_DELAY,
                            )
                        )
                        ev["code"] = ""  # type: ignore
                case "led":
                    if self.led == "left_to_main" and ev["code"] == "left":
                        out.append({**ev, "code": "main"})
                    elif self.led == "right_to_main" and ev["code"] == "right":
                        out.append({**ev, "code": "main"})
                    elif self.led == "main_to_both" and ev["code"] == "main":
                        out.append({**ev, "code": "left"})
                        out.append({**ev, "code": "right"})
                case "configuration":
                    if self.status == "both_to_main":
                        self.state[ev["code"]] = ev["value"]
                        match ev["code"]:
                            case "battery_left" | "battery_right":
                                status_events.add("battery")
                            case "is_attached_left" | "is_attached_right":
                                status_events.add("is_attached")
                            case "is_connected_left" | "is_connected_right":
                                status_events.add("is_connected")

        if touched:
            self.touchpad_down = [
                curr,
                self.touchpad_x,
                self.touchpad_y,
                bool(True),
            ]

        for s in status_events:
            match s:
                case "battery":
                    out.append(
                        {
                            "type": "configuration",
                            "code": "battery",
                            "value": min(
                                self.state.get("battery_left", 100),
                                self.state.get("battery_right", 100),
                            ),
                        }
                    )
                case "is_attached":
                    out.append(
                        {
                            "type": "configuration",
                            "code": "is_attached",
                            "value": (
                                self.state.get("is_attached_left", False)
                                and self.state.get("is_attached_right", False)
                            ),
                        }
                    )
                case "is_connected":
                    out.append(
                        {
                            "type": "configuration",
                            "code": "is_connected",
                            "value": (
                                self.state.get("is_connected_left", False)
                                and self.state.get("is_connected_right", False)
                            ),
                        }
                    )

        # Remove empty events
        for ev in events:
            if ev["type"] != "button" or ev["code"]:
                out.append(ev)

        # Handle QAM button
        # Below is the multitap implementation
        # If it was disabled, the code is a NO-OP
        qam_apply = False
        was_held = True
        # Apply hold
        if self.qam_pressed and curr - self.qam_pressed > self.QAM_HOLD_TIME:
            qam_apply = True
        # Apply double tap
        if self.qam_released and (
            curr - self.qam_released > self.QAM_MULTI_PRESS_DELAY
        ):
            qam_apply = True
        # Apply if double tap disabled
        if not self.qam_multi_tap and self.qam_released:
            qam_apply = True

        qam_hhd = self.qam_hhd and not self.qam_kbd
        if (
            self.qam_pressed
            and self.qam_times == (1 if qam_hhd else 2)
            and not self.qam_pre_sent
            and self.emit
        ):
            # Send event instantly after double press to eat delay
            self.emit({"type": "special", "event": "qam_predouble"})
            self.qam_pre_sent = True

        send_steam_qam = send_steam_qam or (
            qam_apply and not qam_hhd and self.qam_released and self.qam_times == 1
        )
        send_steam_expand = (
            qam_apply and self.qam_pressed and was_held and self.qam_hold == "mode"
        )
        if qam_apply and self.emit:
            if qam_hhd:
                match self.qam_times:
                    case 0:
                        pass
                    case 1:
                        self.emit({"type": "special", "event": "qam_double"})
                    case _:
                        self.emit({"type": "special", "event": "qam_triple"})
            else:
                # FIXME: hiding the event based on qam_hold should not happen
                # instead the handler should not open hhd
                if self.qam_pressed and was_held and self.qam_hold == "hhd":
                    self.emit({"type": "special", "event": "qam_hold"})
                else:
                    match self.qam_times:
                        case 0:
                            pass
                        case 1:
                            self.emit({"type": "special", "event": "qam_single"})
                        case 2:
                            self.emit({"type": "special", "event": "qam_double"})
                        case _:
                            self.emit({"type": "special", "event": "qam_triple"})
        if qam_apply:
            held = " then held" if self.qam_pressed else ""
            logger.info(f"QAM Pressed {self.qam_times}{held}.")
            self.qam_pressed = None
            self.qam_released = None
            self.qam_pre_sent = False
            self.qam_times = 0

        if self.emit:
            evs = self.emit.inject_recv()
            # Handle special case for steam
            for ev in evs:
                if ev["type"] == "configuration" and ev["code"] == "steam":
                    if ev["value"]:
                        send_steam_expand = True
                    else:
                        send_steam_qam = True
            out.extend(evs)

        # Grab all events from controller if grab is on
        # Remove queued events such as qam and xbox to avoid leaking them
        # to the overlay
        if self.emit and self.emit.intercept(
            self.unique, [o for o in out if not o.get("from_queue", False)]
        ):
            # Hiding the gyro and sending fake accel values causes
            # issues with emulators and gyro
            # accel = random.random() * 10
            # fake_accel: Sequence[Event] = [
            #     {"type": "axis", "code": "accel_x", "value": accel},
            #     {"type": "axis", "code": "left_accel_x", "value": accel},
            #     {"type": "axis", "code": "right_accel_x", "value": accel},
            # ]
            # return fake_accel + [
            #     o
            #     for o in out
            #     if o["type"] not in ("button", "axis") or "ts" in o.get("code", "")
            # ]
            return [
                o
                for o in out
                if o["type"] not in ("button", "axis")
                or "ts" in o.get("code", "")
                or "accel" in o.get("code", "")
                or "gyro" in o.get("code", "")
            ]
        elif send_steam_qam:
            # Send steam qam only if not intercepting
            if not self.emit or not self.emit.send_qam():
                if self.has_qam:
                    out.append(
                        {
                            "type": "button",
                            "code": "share",
                            "value": True,
                        },
                    )
                    self.queue.append(
                        (
                            {
                                "type": "button",
                                "code": "share",
                                "value": False,
                            },
                            curr + self.QAM_DELAY,
                        )
                    )
                else:
                    # Have a fallback if gamescope is not working
                    out.append(
                        {
                            "type": "button",
                            "code": "mode",
                            "value": True,
                        },
                    )
                    self.queue.append(
                        (
                            {
                                "type": "button",
                                "code": "b" if self.nintendo_qam else "a",
                                "value": True,
                            },
                            curr + self.QAM_DELAY,
                        )
                    )
                    self.queue.append(
                        (
                            {
                                "type": "button",
                                "code": "b" if self.nintendo_qam else "a",
                                "value": False,
                            },
                            curr + 2 * self.QAM_DELAY,
                        ),
                    )
                    self.queue.append(
                        (
                            {
                                "type": "button",
                                "code": "mode",
                                "value": False,
                            },
                            curr + 2 * self.QAM_DELAY,
                        ),
                    )
        elif send_steam_expand:
            out.append(
                {
                    "type": "button",
                    "code": "mode",
                    "value": True,
                },
            )
            self.queue.append(
                (
                    {
                        "type": "button",
                        "code": "mode",
                        "value": False,
                    },
                    curr + self.QAM_DELAY,
                )
            )
        return out


class KeyboardWrapper(Producer, Consumer):
    def __init__(
        self, parent: Producer, button_map: Sequence[tuple[set[Button], Button]]
    ) -> None:
        self.parent = parent
        self.button_map = button_map

        self.active_in: set[Button] = set()
        self.active_out: set[Button] = set()

    def open(self) -> Sequence[int]:
        self.active_in: set[Button] = set()
        self.active_out: set[Button] = set()
        return self.parent.open()

    def close(self, exit: bool) -> bool:
        return self.parent.close(exit)

    def produce(self, fds: Sequence[int]) -> Sequence[Event]:
        evs: Sequence[Event] = self.parent.produce(fds)
        # Update in map
        for ev in evs:
            logger.info(f"Internal kbd event: {ev}")
            if ev["type"] == "button":
                if ev["value"]:
                    self.active_in.add(ev["code"])
                elif ev["code"] in self.active_in:
                    self.active_in.remove(ev["code"])

        # Debounce and output
        out: Sequence[Event] = []
        for bset, action in self.button_map:
            is_sub = bset.issubset(self.active_in)
            is_active = action in self.active_out
            if is_sub and not is_active:
                self.active_out.add(action)
                out.append({"type": "button", "code": action, "value": True})
            elif not is_sub and is_active:
                self.active_out.remove(action)
                out.append({"type": "button", "code": action, "value": False})

        return out

    def consume(self, events: Sequence[Event]):
        if isinstance(self.parent, Consumer):
            return self.parent.consume(events)


def can_read(fd: int):
    return select.select([fd], [], [], 0)[0]
