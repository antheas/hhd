from hhd.controller import Axis, Button, Configuration
from hhd.controller.physical.evdev import B, to_map
from hhd.plugins import gen_gyro_state
from hhd.controller.physical.hidraw import AM, BM, CM

DEFAULT_MAPPINGS: dict[str, tuple[Axis, str | None, float, float | None]] = {
    "accel_x": ("accel_z", "accel", 1, None),
    "accel_y": ("accel_x", "accel", -1, None),
    "accel_z": ("accel_y", "accel", -1, None),
    "anglvel_x": ("gyro_z", "anglvel", 1, None),
    "anglvel_y": ("gyro_x", "anglvel", -1, None),
    "anglvel_z": ("gyro_y", "anglvel", -1, None),
    "timestamp": ("imu_ts", None, 1, None),
}

BTN_MAPPINGS: dict[int, Button] = {
    # Volume buttons come from the same keyboard
    B("KEY_VOLUMEUP"): "key_volumeup",
    B("KEY_VOLUMEDOWN"): "key_volumedown",
    #
    # Loki
    #
    B("KEY_T"): "share",  # T + LCTRL + LSHFT + LALT
}

AMBERNIC_MAPPINGS: dict[int, str] = {
    B("KEY_LEFTMETA"): "share",
    B("KEY_G"): "mode",
}

MSI_CLAW_MAPPINGS = {
    B("KEY_VOLUMEUP"): "key_volumeup",
    B("KEY_VOLUMEDOWN"): "key_volumedown",
    B("KEY_F15"): "mode",
    B("KEY_F16"): "share",
}


TECNO_BTN_MAPPINGS = {
    B("KEY_VOLUMEUP"): "key_volumeup",
    B("KEY_VOLUMEDOWN"): "key_volumedown",
    B("KEY_F1"): "share",  # Center button (shift+alt+ctrl+f1)
}

TECNO_RAW_INTERFACE_BTN_MAP: dict[int | None, dict[Button, BM]] = {
    0x74: {
        # Misc
        "mode": BM((5 << 3) + 7), # 1: Bottom left
        "keyboard": BM((5 << 3) + 6), # 2: Bottom right
        "extra_l1": BM((7 << 3) + 2), # 3: Keyboard switch button
    }
}


AYANEO_DEFAULT_MAPPINGS: dict[str, tuple[Axis, str | None, float, float | None]] = {
    "accel_x": ("accel_z", "accel", 1, None),
    "accel_y": ("accel_x", "accel", -1, None),
    "accel_z": ("accel_y", "accel", -1, None),
    "anglvel_x": ("gyro_z", "anglvel", 1, None),
    "anglvel_y": ("gyro_x", "anglvel", -1, None),
    "anglvel_z": ("gyro_y", "anglvel", -1, None),
    "timestamp": ("imu_ts", None, 1, None),
}

AYANEO_AIR_PLUS_MAPPINGS: dict[str, tuple[Axis, str | None, float, float | None]] = {
    "accel_x": ("accel_z", "accel", -1, None),
    "accel_y": ("accel_x", "accel", -1, None),
    "accel_z": ("accel_y", "accel", 1, None),
    "anglvel_x": ("gyro_z", "anglvel", -1, None),
    "anglvel_y": ("gyro_x", "anglvel", -1, None),
    "anglvel_z": ("gyro_y", "anglvel", 1, None),
    "timestamp": ("imu_ts", None, 1, None),
}

AYANEO_DEFAULT_BTN_MAPPINGS: dict[int, str] = {
    # Volume buttons come from the same keyboard
    B("KEY_VOLUMEUP"): "key_volumeup",
    B("KEY_VOLUMEDOWN"): "key_volumedown",
    # Air Plus mappings
    B("KEY_F17"): "mode",  # Big Button
    B("KEY_D"): "share",  # Small Button
    B("KEY_F15"): "extra_l1",  # LC Button
    B("KEY_F16"): "extra_r1",  # RC Button
    # NEXT mappings
    B(
        "KEY_F12"
    ): "mode",  # Big Button NEXT:[[96, 105, 133], [88, 97, 125]] ; Air [88, 97, 125]
    # B("KEY_D"): "share", # Small Button [[40, 133], [32, 125]]
    # 2021 Mappings
    B("KEY_DELETE"): "share",  # TM Button [97,100,111]
    B("KEY_ESC"): "extra_l1",  # ESC Button [1]
    B("KEY_O"): "extra_r1",  # KB Button [97, 24, 125]
    # B("KEY_LEFTMETA"): "extra_r1", # Win Button [125], Conflict with KB Button
}


AYANEO_AIR_BTN_MAPPINGS: dict[int, str] = {
    # Volume buttons come from the same keyboard
    B("KEY_VOLUMEUP"): "key_volumeup",
    B("KEY_VOLUMEDOWN"): "key_volumedown",
    B("KEY_D"): "share",  # Small Button [125, 32]
    B("KEY_F12"): "mode",  # Big Button Air [88, 97, 125]
    B("KEY_F11"): "extra_l1",  # LC Button [87, 97, 125] F11 + LCTRL + LMETA
    B("KEY_F10"): "extra_r1",  # Rc Button [68, 97, 125] F10 + LCTRL + LMETA
    B("KEY_F16"): "pb_long", # Power Button Long Press [125, 186]
}

AYA_DEFAULT_CONF = {
    "hrtimer": True,
    "btn_mapping": AYANEO_DEFAULT_BTN_MAPPINGS,
    "mapping": AYANEO_DEFAULT_MAPPINGS,
}
ONEX_DEFAULT_CONF = {
    "hrtimer": True,
}

CONFS = {
    # Ayn
    "Loki MiniPro": {
        "name": "Loki MiniPro",
        "hrtimer": True,
        "mapping": gen_gyro_state("x", False, "z", False, "y", True),
        "extra_buttons": "none",
    },
    "Loki Max": {
        "name": "Loki Max",
        "hrtimer": True,
        "mapping": gen_gyro_state("x", False, "z", False, "y", True),
        "extra_buttons": "none",
    },
    "Loki Zero": {
        "name": "Loki Zero",
        "hrtimer": True,
        "mapping": gen_gyro_state("x", False, "z", False, "y", True),
        "extra_buttons": "none",
    },
    # Ayaneo
    "AIR Plus": {
        "name": "AYANEO AIR Plus",
        **AYA_DEFAULT_CONF,
        "mapping": AYANEO_AIR_PLUS_MAPPINGS,
    },
    "AIR 1S": {"name": "AIR 1S", **AYA_DEFAULT_CONF},
    "AIR 1S Limited": {"name": "AIR 1S Limited", **AYA_DEFAULT_CONF},
    "AYANEO 2": {"name": "AYANEO 2", **AYA_DEFAULT_CONF},
    "AYANEO 2S": {"name": "AYANEO S2", **AYA_DEFAULT_CONF},
    "GEEK": {"name": "AYANEO GEEK", **AYA_DEFAULT_CONF},
    "GEEK 1S": {"name": "AYANEO GEEK 1S", **AYA_DEFAULT_CONF},
    "AIR": {"name": "AYANEO AIR",
        **AYA_DEFAULT_CONF,
        "btn_mapping": AYANEO_AIR_BTN_MAPPINGS
    },
    "AIR Pro": {"name": "AYANEO AIR Pro", **AYA_DEFAULT_CONF},
    "NEXT Advance": {"name": "AYANEO NEXT Advance", **AYA_DEFAULT_CONF},
    "NEXT Lite": {"name": "AYANEO NEXT Lite", **AYA_DEFAULT_CONF},
    "NEXT Pro": {"name": "AYANEO NEXT Pro", **AYA_DEFAULT_CONF},
    "NEXT": {"name": "AYANEO NEXT", **AYA_DEFAULT_CONF},
    "SLIDE": {
        "name": "AYANEO SLIDE",
        **AYA_DEFAULT_CONF,
        "mapping": gen_gyro_state("z", False, "x", False, "y", False),
    },
    "AYA NEO FOUNDER": {"name": "AYA NEO FOUNDER", **AYA_DEFAULT_CONF},
    "AYA NEO 2021": {"name": "AYA NEO 2021", **AYA_DEFAULT_CONF},
    "AYANEO 2021": {"name": "AYANEO 2021", **AYA_DEFAULT_CONF},
    "AYANEO 2021 Pro": {"name": "AYANEO 2021 Pro", **AYA_DEFAULT_CONF},
    "AYANEO 2021 Pro Retro Power": {
        "name": "AYANEO 2021 Pro Retro Power",
        **AYA_DEFAULT_CONF,
    },
    # Ambernic
    "Win600": {
        "name": "Ambernic Win600",
        "btn_mapping": AMBERNIC_MAPPINGS,
        "extra_buttons": "none",
    },
    # MSI Claw
    "Claw A1M": {
        "name": "MSI Claw (1st gen)",
        # "hrtimer": True, Uses sensor fusion garbage? From intel? Will need custom work
        "extra_buttons": "none",
        "btn_mapping": MSI_CLAW_MAPPINGS,
        "claw": True,
        "type": "claw",
        "display_gyro": False,
    },
    # TECNO
    "Pocket Go": {
        "name": "TECNO (Displayless)",
        "extra_buttons": "none",
        "btn_mapping": TECNO_BTN_MAPPINGS,
        "type": "tecno",
        "display_gyro": False,
    },
}


def get_default_config(product_name: str, manufacturer: str):
    out = {
        "name": product_name,
        "manufacturer": manufacturer,
        "hrtimer": True,
        "untested": True,
    }

    if manufacturer == "AYA":
        out["btn_mapping"] = AYANEO_DEFAULT_BTN_MAPPINGS
        out["mapping"] = AYANEO_DEFAULT_MAPPINGS

    return out
