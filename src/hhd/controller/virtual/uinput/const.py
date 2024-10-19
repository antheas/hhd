import logging
from typing import cast, Sequence, NamedTuple

import evdev
from evdev import AbsInfo

from hhd.controller.const import Axis, Button


HHD_VID = 0x5335
HHD_PID_GAMEPAD = 0x01
HHD_PID_KEYBOARD = 0x02
HHD_PID_MOUSE = 0x03
HHD_PID_TOUCHPAD = 0x04
HHD_PID_MOTION = 0x11
HHD_PID_VENDOR = 0x7000

CONTROLLER_THEMES: dict[str, tuple[int, int, str]] = {
    "hhd": (0x5335, 0x0001, "Handheld Daemon Controller"),
    # Sony
    "ps3": (0x054C, 0x0268, "DualShock 3"),
    "ps4": (0x054C, 0x05C4, "DualShock 4"),
    "ps5": (0x054C, 0x0CE6, "DualSense"),
    "ps5e": (0x054C, 0x0DF2, "DualSense Edge"),
    # Microsoft
    "xbox_360": (0x045E, 0x028F, "Xbox 360"),
    "xbox_one": (0x045E, 0x02D1, "Xbox One"),
    "xbox_one_elite": (0x045E, 0x02E3, "Xbox Elite"),
    "xbox_sx": (0x045E, 0x0B12, "Xbox Series X"),
    # Nintendo
    "joycon_left": (0x057E, 0x2006, "JoyCon Left"),
    "joycon_right": (0x057E, 0x2007, "JoyCon Right"),
    "joycon_pair": (0x057E, 0x2008, "Nintendo Switch Combined Joy-Cons"),
    "joycon_grip": (0x057E, 0x200E, "JoyCon Grip"),
    "switch_pro": (0x057E, 0x2009, "Switch Pro"),
    # Valve
    "steam_deck": (0x28DE, 0x1205, "Steam Deck"),
    "steam_controller": (0x28DE, 0x1202, "Steam Controller"),
    "steam_input": (0x28DE, 0x11FF, "Steam Input"),
    "hori_steam": (0x0f0d, 0x0196, "Steam Controller (HHD)")
}


def B(b: str | Sequence[str], num: int | None = None):
    if num is not None:
        return num
    assert b, f"No value provided."
    if not isinstance(b, str):
        b = b[0]
    return cast(int, getattr(evdev.ecodes, b))


class AX(NamedTuple):
    id: int
    scale: float = 1
    offset: float = 0
    bounds: tuple[int, int] | None = None


logger = logging.getLogger(__name__)

GAMEPAD_CAPABILITIES = {
    # B("EV_SYN", 0): [
    #     B("SYN_REPORT", 0),
    #     B("SYN_CONFIG", 1),
    #     B("SYN_DROPPED", 3),
    #     B("?", 21),
    # ],
    B("EV_KEY", 1): [
        B(["BTN_A", "BTN_GAMEPAD", "BTN_SOUTH"], 304),
        B(["BTN_B", "BTN_EAST"], 305),
        B(["BTN_NORTH", "BTN_X"], 307),
        B(["BTN_WEST", "BTN_Y"], 308),
        B("BTN_TL", 310),
        B("BTN_TR", 311),
        B("BTN_SELECT", 314),
        B("BTN_START", 315),
        B("BTN_MODE", 316),
        B("BTN_THUMBL", 317),
        B("BTN_THUMBR", 318),
        B("BTN_TRIGGER_HAPPY1"),
        B("BTN_TRIGGER_HAPPY2"),
        B("BTN_TRIGGER_HAPPY3"),
        B("BTN_TRIGGER_HAPPY4"),
        B("BTN_TRIGGER_HAPPY5"),
        B("BTN_TRIGGER_HAPPY6"),
        B("BTN_TRIGGER_HAPPY7"),
        B("BTN_TRIGGER_HAPPY8"),
        B("BTN_TRIGGER_HAPPY9"),
        B("BTN_TRIGGER_HAPPY10"),
        B("BTN_TRIGGER_HAPPY11"),
        B("BTN_TRIGGER_HAPPY12"),
        B("BTN_TRIGGER_HAPPY13"),
        B("BTN_TRIGGER_HAPPY14"),
        B("BTN_TRIGGER_HAPPY15"),
        B("BTN_TRIGGER_HAPPY16"),
        B("BTN_TRIGGER_HAPPY17"),
        B("BTN_TRIGGER_HAPPY18"),
        B("BTN_TRIGGER_HAPPY19"),
        B("BTN_TRIGGER_HAPPY20"),
    ],
    B("EV_ABS", 3): [
        (
            B("ABS_X", 0),
            AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0),
        ),
        (
            B("ABS_Y", 1),
            AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0),
        ),
        (B("ABS_Z", 2), AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
        (
            B("ABS_RX", 3),
            AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0),
        ),
        (
            B("ABS_RY", 4),
            AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0),
        ),
        (
            B("ABS_RZ", 5),
            AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0),
        ),
        (
            B("ABS_HAT0X", 16),
            AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0),
        ),
        (
            B("ABS_HAT0Y", 17),
            AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0),
        ),
    ],
    B("EV_FF", 21): [
        B(["FF_EFFECT_MIN", "FF_RUMBLE"], 80),
        B("FF_PERIODIC", 81),
        B(["FF_SQUARE", "FF_WAVEFORM_MIN"], 88),
        B("FF_TRIANGLE", 89),
        B("FF_SINE", 90),
        B(["FF_GAIN", "FF_MAX_EFFECTS"], 96),
    ],
}

MOTION_CAPABILITIES = {
    # B("EV_SYN", 0): [B("SYN_REPORT", 0), B("SYN_DROPPED", 3), B("?", 4)],
    B("EV_ABS", 3): [
        (
            B("ABS_X", 0),
            AbsInfo(value=0, min=-32768, max=32768, fuzz=16, flat=0, resolution=8192),
        ),
        (
            B("ABS_Y", 1),
            AbsInfo(value=0, min=-32768, max=32768, fuzz=16, flat=0, resolution=8192),
        ),
        (
            B("ABS_Z", 2),
            AbsInfo(value=0, min=-32768, max=32768, fuzz=16, flat=0, resolution=8192),
        ),
        (
            B("ABS_RX", 3),
            AbsInfo(
                value=0, min=-2097152, max=2097152, fuzz=16, flat=0, resolution=1024
            ),
        ),
        (
            B("ABS_RY", 4),
            AbsInfo(
                value=0, min=-2097152, max=2097152, fuzz=16, flat=0, resolution=1024
            ),
        ),
        (
            B("ABS_RZ", 5),
            AbsInfo(
                value=0, min=-2097152, max=2097152, fuzz=16, flat=0, resolution=1024
            ),
        ),
    ],
    B("EV_MSC", 4): [B("MSC_TIMESTAMP", 5)],
}

KEYBOARD_CAPABILITIES = {
    # B("EV_SYN", 0): [
    #     B("SYN_REPORT", 0),
    #     B("SYN_CONFIG", 1),
    #     B("?", 4),
    #     B("?", 17),
    #     B("?", 20),
    # ],
    B("EV_KEY", 1): [
        B("KEY_ESC", 1),
        B("KEY_1", 2),
        B("KEY_2", 3),
        B("KEY_3", 4),
        B("KEY_4", 5),
        B("KEY_5", 6),
        B("KEY_6", 7),
        B("KEY_7", 8),
        B("KEY_8", 9),
        B("KEY_9", 10),
        B("KEY_0", 11),
        B("KEY_MINUS", 12),
        B("KEY_EQUAL", 13),
        B("KEY_BACKSPACE", 14),
        B("KEY_TAB", 15),
        B("KEY_Q", 16),
        B("KEY_W", 17),
        B("KEY_E", 18),
        B("KEY_R", 19),
        B("KEY_T", 20),
        B("KEY_Y", 21),
        B("KEY_U", 22),
        B("KEY_I", 23),
        B("KEY_O", 24),
        B("KEY_P", 25),
        B("KEY_LEFTBRACE", 26),
        B("KEY_RIGHTBRACE", 27),
        B("KEY_ENTER", 28),
        B("KEY_LEFTCTRL", 29),
        B("KEY_A", 30),
        B("KEY_S", 31),
        B("KEY_D", 32),
        B("KEY_F", 33),
        B("KEY_G", 34),
        B("KEY_H", 35),
        B("KEY_J", 36),
        B("KEY_K", 37),
        B("KEY_L", 38),
        B("KEY_SEMICOLON", 39),
        B("KEY_APOSTROPHE", 40),
        B("KEY_GRAVE", 41),
        B("KEY_LEFTSHIFT", 42),
        B("KEY_BACKSLASH", 43),
        B("KEY_Z", 44),
        B("KEY_X", 45),
        B("KEY_C", 46),
        B("KEY_V", 47),
        B("KEY_B", 48),
        B("KEY_N", 49),
        B("KEY_M", 50),
        B("KEY_COMMA", 51),
        B("KEY_DOT", 52),
        B("KEY_SLASH", 53),
        B("KEY_RIGHTSHIFT", 54),
        B("KEY_KPASTERISK", 55),
        B("KEY_LEFTALT", 56),
        B("KEY_SPACE", 57),
        B("KEY_CAPSLOCK", 58),
        B("KEY_F1", 59),
        B("KEY_F2", 60),
        B("KEY_F3", 61),
        B("KEY_F4", 62),
        B("KEY_F5", 63),
        B("KEY_F6", 64),
        B("KEY_F7", 65),
        B("KEY_F8", 66),
        B("KEY_F9", 67),
        B("KEY_F10", 68),
        B("KEY_NUMLOCK", 69),
        B("KEY_SCROLLLOCK", 70),
        B("KEY_KP7", 71),
        B("KEY_KP8", 72),
        B("KEY_KP9", 73),
        B("KEY_KPMINUS", 74),
        B("KEY_KP4", 75),
        B("KEY_KP5", 76),
        B("KEY_KP6", 77),
        B("KEY_KPPLUS", 78),
        B("KEY_KP1", 79),
        B("KEY_KP2", 80),
        B("KEY_KP3", 81),
        B("KEY_KP0", 82),
        B("KEY_KPDOT", 83),
        B("KEY_ZENKAKUHANKAKU", 85),
        B("KEY_102ND", 86),
        B("KEY_F11", 87),
        B("KEY_F12", 88),
        B("KEY_RO", 89),
        B("KEY_KATAKANA", 90),
        B("KEY_HIRAGANA", 91),
        B("KEY_HENKAN", 92),
        B("KEY_KATAKANAHIRAGANA", 93),
        B("KEY_MUHENKAN", 94),
        B("KEY_KPJPCOMMA", 95),
        B("KEY_KPENTER", 96),
        B("KEY_RIGHTCTRL", 97),
        B("KEY_KPSLASH", 98),
        B("KEY_SYSRQ", 99),
        B("KEY_RIGHTALT", 100),
        B("KEY_HOME", 102),
        B("KEY_UP", 103),
        B("KEY_PAGEUP", 104),
        B("KEY_LEFT", 105),
        B("KEY_RIGHT", 106),
        B("KEY_END", 107),
        B("KEY_DOWN", 108),
        B("KEY_PAGEDOWN", 109),
        B("KEY_INSERT", 110),
        B("KEY_DELETE", 111),
        B(["KEY_MIN_INTERESTING", "KEY_MUTE"], 113),
        B("KEY_VOLUMEDOWN", 114),
        B("KEY_VOLUMEUP", 115),
        B("KEY_POWER", 116),
        B("KEY_KPEQUAL", 117),
        B("KEY_PAUSE", 119),
        B("KEY_KPCOMMA", 121),
        B(["KEY_HANGEUL", "KEY_HANGUEL"], 122),
        B("KEY_HANJA", 123),
        B("KEY_YEN", 124),
        B("KEY_LEFTMETA", 125),
        B("KEY_RIGHTMETA", 126),
        B("KEY_COMPOSE", 127),
        B("KEY_STOP", 128),
        B("KEY_AGAIN", 129),
        B("KEY_PROPS", 130),
        B("KEY_UNDO", 131),
        B("KEY_FRONT", 132),
        B("KEY_COPY", 133),
        B("KEY_OPEN", 134),
        B("KEY_PASTE", 135),
        B("KEY_FIND", 136),
        B("KEY_CUT", 137),
        B("KEY_HELP", 138),
        B("KEY_CALC", 140),
        B("KEY_SLEEP", 142),
        B("KEY_WWW", 150),
        B(["KEY_COFFEE", "KEY_SCREENLOCK"], 152),
        B("KEY_BACK", 158),
        B("KEY_FORWARD", 159),
        B("KEY_EJECTCD", 161),
        B("KEY_NEXTSONG", 163),
        B("KEY_PLAYPAUSE", 164),
        B("KEY_PREVIOUSSONG", 165),
        B("KEY_STOPCD", 166),
        B("KEY_REFRESH", 173),
        B("KEY_EDIT", 176),
        B("KEY_SCROLLUP", 177),
        B("KEY_SCROLLDOWN", 178),
        B("KEY_KPLEFTPAREN", 179),
        B("KEY_KPRIGHTPAREN", 180),
        B("KEY_F13", 183),
        B("KEY_F14", 184),
        B("KEY_F15", 185),
        B("KEY_F16", 186),
        B("KEY_F17", 187),
        B("KEY_F18", 188),
        B("KEY_F19", 189),
        B("KEY_F20", 190),
        B("KEY_F21", 191),
        B("KEY_F22", 192),
        B("KEY_F23", 193),
        B("KEY_F24", 194),
        B("KEY_UNKNOWN", 240),
    ],
    B("EV_MSC", 4): [B("MSC_SCAN", 4)],
    B("EV_LED", 17): [B("LED_NUML", 0), B("LED_CAPSL", 1), B("LED_SCROLLL", 2)],
}

MOUSE_CAPABILITIES = {
    # B("EV_SYN", 0): [
    #     B("SYN_REPORT", 0),
    #     B("SYN_CONFIG", 1),
    #     B("SYN_MT_REPORT", 2),
    #     B("?", 4),
    # ],
    B("EV_KEY", 1): [
        B(["BTN_LEFT", "BTN_MOUSE"], 272),
        B("BTN_RIGHT", 273),
        B("BTN_MIDDLE", 274),
        B("BTN_SIDE", 275),
        B("BTN_EXTRA", 276),
    ],
    B("EV_REL", 2): [
        B("REL_X", 0),
        B("REL_Y", 1),
        B("REL_WHEEL", 8),
        B("REL_WHEEL_HI_RES", 11),
    ],
    B("EV_MSC", 4): [B("MSC_SCAN", 4)],
}

TOUCHPAD_CAPABILITIES = {
    B("EV_KEY", 1): [
        B(["BTN_LEFT", "BTN_MOUSE"], 272),
        B("BTN_RIGHT"),
        B("BTN_TOOL_FINGER", 325),
        B("BTN_TOUCH", 330),
        B("BTN_TOOL_DOUBLETAP", 333),
        B("BTN_TOOL_TRIPLETAP", 334),
    ],
    B("EV_ABS", 3): [
        (
            B("ABS_X", 0),
            AbsInfo(value=172, min=0, max=2048, fuzz=0, flat=0, resolution=36),
        ),
        (
            B("ABS_Y", 1),
            AbsInfo(value=472, min=0, max=2048, fuzz=0, flat=0, resolution=36),
        ),
        (
            B("ABS_MT_SLOT", 47),
            AbsInfo(value=0, min=0, max=2, fuzz=0, flat=0, resolution=0),
        ),
        (
            B("ABS_MT_POSITION_X", 53),
            AbsInfo(value=0, min=0, max=2048, fuzz=0, flat=0, resolution=36),
        ),
        (
            B("ABS_MT_POSITION_Y", 54),
            AbsInfo(value=0, min=0, max=2048, fuzz=0, flat=0, resolution=36),
        ),
        (
            B("ABS_MT_TOOL_TYPE", 55),
            AbsInfo(value=0, min=0, max=2, fuzz=0, flat=0, resolution=0),
        ),
        (
            B("ABS_MT_TRACKING_ID", 57),
            AbsInfo(value=0, min=0, max=65535, fuzz=0, flat=0, resolution=0),
        ),
    ],
    B("EV_MSC", 4): [B("MSC_TIMESTAMP", 5)],
}
GAMEPAD_BASE_BUTTON_MAP: dict[Button, int] = {
    # Gamepad
    "a": B("BTN_A"),
    "b": B("BTN_B"),
    "x": B("BTN_X"),
    "y": B("BTN_Y"),
    # Sticks
    "ls": B("BTN_THUMBL"),
    "rs": B("BTN_THUMBR"),
    # Bumpers
    "lb": B("BTN_TL"),
    "rb": B("BTN_TR"),
    # Select
    "start": B("BTN_START"),
    "select": B("BTN_SELECT"),
    # Misc
    "mode": B("BTN_MODE"),
    "share": B("BTN_TRIGGER_HAPPY20"),
}

GAMEPAD_BUTTON_MAP: dict[Button, int] = {
    **GAMEPAD_BASE_BUTTON_MAP,
    # Back buttons
    "extra_l1": B("BTN_TRIGGER_HAPPY1"),
    "extra_r1": B("BTN_TRIGGER_HAPPY2"),
    "extra_l2": B("BTN_TRIGGER_HAPPY3"),
    "extra_r2": B("BTN_TRIGGER_HAPPY4"),
    "extra_l3": B("BTN_TRIGGER_HAPPY5"),
    "extra_r3": B("BTN_TRIGGER_HAPPY6"),
}

XBOX_ELITE_BUTTON_MAP: dict[Button, int] = {
    **GAMEPAD_BASE_BUTTON_MAP,
    # Back buttons
    "extra_l1": B("BTN_TRIGGER_HAPPY7"),
    "extra_r1": B("BTN_TRIGGER_HAPPY5"),
    "extra_l2": B("BTN_TRIGGER_HAPPY8"),
    "extra_r2": B("BTN_TRIGGER_HAPPY6"),
}

HORIPAD_STEAM_BUTTON_MAP: dict[Button, int] = {
    **GAMEPAD_BASE_BUTTON_MAP,
    # a:b0,b:b1,back:b4,dpdown:h0.4,dpleft:h0.8,dpright:h0.2,dpup:h0.1,guide:b5,
    # leftshoulder:b9,leftstick:b7,lefttrigger:a4,leftx:a0,lefty:a1,
    # rightshoulder:b10,rightstick:b8,righttrigger:a5,rightx:a2,righty:a3,start:b6,x:b2,y:b3,
    # From SDL: The Wireless HORIPad for Steam has QAM, Steam, Capsense L/R Sticks, 2 rear buttons, and 2 misc buttons
    # paddle1:b13,paddle2:b12,paddle3:b15,paddle4:b14,misc2:b11,misc3:b16,misc4:b17
    # Try to use the same mapping
    "share": B("BTN_TRIGGER_HAPPY1"),
    "extra_l1": B("BTN_TRIGGER_HAPPY2"),
    "extra_r1": B("BTN_TRIGGER_HAPPY3"),
    "extra_l2": B("BTN_TRIGGER_HAPPY4"),
    "extra_r2": B("BTN_TRIGGER_HAPPY5"),
    "extra_l3": B("BTN_TRIGGER_HAPPY6"),
    "extra_r3": B("BTN_TRIGGER_HAPPY7"),
    # No Capsense :/
}

GAMEPAD_AXIS_MAP: dict[Axis, AX] = {
    "ls_x": AX(B("ABS_X"), 2**15 - 1),
    "ls_y": AX(B("ABS_Y"), 2**15 - 1),
    "rs_x": AX(B("ABS_RX"), 2**15 - 1),
    "rs_y": AX(B("ABS_RY"), 2**15 - 1),
    "rt": AX(B("ABS_Z"), 2**8 - 1),
    "lt": AX(B("ABS_RZ"), 2**8 - 1),
    "hat_x": AX(B("ABS_HAT0X")),
    "hat_y": AX(B("ABS_HAT0Y")),
}

MOTION_AXIS_MAP: dict[Axis, AX] = {
    "accel_x": AX(B("ABS_X"), 8192 / 9.8, bounds=(-32768, 32768)),
    "accel_y": AX(B("ABS_Y"), 8192 / 9.8, bounds=(-32768, 32768)),
    "accel_z": AX(B("ABS_Z"), 8192 / 9.8, bounds=(-32768, 32768)),
    "gyro_x": AX(B("ABS_RX"), 1024 * 180 / 3.14, bounds=(-2097152, 2097152)),
    "gyro_y": AX(B("ABS_RY"), 1024 * 180 / 3.14, bounds=(-2097152, 2097152)),
    "gyro_z": AX(B("ABS_RZ"), 1024 * 180 / 3.14, bounds=(-2097152, 2097152)),
}

MOTION_AXIS_MAP_FLIP_Z: dict[Axis, AX] = {
    "accel_x": AX(B("ABS_X"), 8192 / 9.8, bounds=(-32768, 32768)),
    "accel_y": AX(B("ABS_Y"), 8192 / 9.8, bounds=(-32768, 32768)),
    "accel_z": AX(B("ABS_Z"), 8192 / 9.8, bounds=(-32768, 32768)),
    "gyro_x": AX(B("ABS_RX"), 1024 * 180 / 3.14, bounds=(-2097152, 2097152)),
    "gyro_y": AX(B("ABS_RY"), 1024 * 180 / 3.14, bounds=(-2097152, 2097152)),
    "gyro_z": AX(B("ABS_RZ"), -1024 * 180 / 3.14, bounds=(-2097152, 2097152)),
}

MOTION_LEFT_AXIS_MAP: dict[Axis, AX] = {
    "left_" + k: v for k, v in MOTION_AXIS_MAP.items()  # type: ignore
}
MOTION_LEFT_AXIS_MAP_FLIP_Z: dict[Axis, AX] = {
    "left_" + k: v for k, v in MOTION_AXIS_MAP_FLIP_Z.items()  # type: ignore
}

MOTION_RIGHT_AXIS_MAP: dict[Axis, AX] = {
    "right_" + k: v for k, v in MOTION_AXIS_MAP.items()  # type: ignore
}

MOTION_INPUT_PROPS = [B("INPUT_PROP_ACCELEROMETER")]

TOUCHPAD_AXIS_MAP: dict[Axis, AX] = {
    "touchpad_x": AX(B("ABS_X"), 1023, bounds=(0, 2048)),
    "touchpad_y": AX(B("ABS_Y"), 1023, bounds=(0, 2048)),
}

TOUCHPAD_BUTTON_MAP: dict[Button, int] = {
    "touchpad_touch": B("BTN_TOUCH"),
    "touchpad_right": B("BTN_RIGHT"),
    "touchpad_left": B("BTN_LEFT"),
}

LEFT_TOUCHPAD_AXIS_MAP: dict[Axis, AX] = {
    "left_touchpad_x": AX(B("ABS_X"), 1023, bounds=(0, 2048)),
    "left_touchpad_y": AX(B("ABS_Y"), 1023, bounds=(0, 2048)),
}

LEFT_TOUCHPAD_BUTTON_MAP: dict[Button, int] = {
    "left_touchpad_touch": B("BTN_TOUCH"),
    "left_touchpad_right": B("BTN_RIGHT"),
    "left_touchpad_left": B("BTN_LEFT"),
}
