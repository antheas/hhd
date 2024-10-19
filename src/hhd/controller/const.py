from typing import Literal


AbsAxis = Literal[
    # Sticks
    # Values should range from -1 to 1
    "ls_x",
    "ls_y",
    "rs_x",
    "rs_y",
    # Triggers
    # Values should range from 0 to 1
    "lt",
    "rt",
    # Hat, implemented as axis. Either -1, 0, or 1
    "hat_x",
    "hat_y",
    # Accelerometer
    # Values should be in m2/s
    "accel_x",
    "accel_y",
    "accel_z",
    "accel_ts",  # deprecated
    # Gyroscope
    # Values should be in deg/s
    "gyro_x",
    "gyro_y",
    "gyro_z",
    "gyro_ts",  # deprecated
    "imu_ts",
    # Touchpad
    # Both width and height should go from [0, 1]. Aspect ratio is a setting.
    # It is up to the device whether to stretch, crop and how to crop (either
    # crop part of the input or part of itself)
    "touchpad_x",
    "touchpad_y",
    # Sidedness
    # Left
    "left_accel_x",
    "left_accel_y",
    "left_accel_z",
    "left_gyro_x",
    "left_gyro_y",
    "left_gyro_z",
    "left_imu_ts",
    "left_touchpad_x",
    "left_touchpad_y",
    # Right
    "right_accel_x",
    "right_accel_y",
    "right_accel_z",
    "right_gyro_x",
    "right_gyro_y",
    "right_gyro_z",
    "right_imu_ts",
]

RelAxis = Literal["mouse_x", "mouse_y", "mouse_wheel", "mouse_wheel_hires"]

GamepadButton = Literal[
    # Thumbpad
    "a",
    "b",
    "x",
    "y",
    # D-PAD (avail as both axis and buttons)
    "dpad_up",
    "dpad_down",
    "dpad_left",
    "dpad_right",
    # Sticks
    "ls",
    "rs",
    # Bumpers
    "lb",
    "rb",
    # Triggers
    "lt",
    "rt",
    # Back buttons
    "extra_l1",
    "extra_l2",
    "extra_l3",
    "extra_r1",
    "extra_r2",
    "extra_r3",
    # Select
    "start",
    "select",
    # Misc
    "mode",
    "share",
    # Touchpad
    "touchpad_touch",
    "touchpad_left",
    "touchpad_right",
    "left_touchpad_touch",
    "left_touchpad_left",
    "left_touchpad_right",
]

MouseButton = Literal["btn_left", "btn_right", "btn_middle", "btn_side", "btn_extra"]

KeyboardButton = Literal[
    "key_esc",  # 1
    "key_enter",  # 28
    # Modifiers
    "key_leftctrl",  # 29
    "key_leftshift",  # 42
    "key_leftalt",  # 56
    "key_rightctrl",  # 97
    "key_rightshift",  # 54
    "key_rightalt",  # 100
    "key_leftmeta",  # 125
    "key_rightmeta",  # 126
    # Special Keys
    "key_capslock",  # 58
    "key_numlock",  # 69
    "key_scrolllock",  # 70
    "key_sysrq",  # 99
    # Symbols
    "key_minus",  # 12
    "key_equal",  # 13
    "key_backspace",  # 14
    "key_tab",  # 15
    "key_leftbrace",  # 26
    "key_rightbrace",  # 27
    "key_space",  # 57
    "key_up",  # 103
    "key_left",  # 105
    "key_right",  # 106
    "key_down",  # 108
    "key_home",  # 102
    "key_end",  # 107
    "key_pageup",  # 104
    "key_pagedown",  # 109
    "key_insert",  # 110
    "key_delete",  # 111
    "key_semicolon",  # 39
    "key_apostrophe",  # 40
    "key_grave",  # 41
    "key_backslash",  # 43
    "key_comma",  # 51
    "key_dot",  # 52
    "key_slash",  # 53
    "key_102nd",  # 86
    "key_ro",  # 89
    "key_power",  # 116
    "key_compose",  # 127
    "key_stop",  # 128
    "key_again",  # 129
    "key_props",  # 130
    "key_undo",  # 131
    "key_front",  # 132
    "key_copy",  # 133
    "key_open",  # 134
    "key_paste",  # 135
    "key_cut",  # 137
    "key_find",  # 136
    "key_help",  # 138
    "key_calc",  # 140
    "key_sleep",  # 142
    "key_www",  # 150
    "key_screenlock",  # 152
    "key_back",  # 158
    "key_refresh",  # 173
    "key_edit",  # 176
    "key_scrollup",  # 177
    "key_scrolldown",  # 178
    # Numbers
    "key_1",  # 2
    "key_2",  # 3
    "key_3",  # 4
    "key_4",  # 5
    "key_5",  # 6
    "key_6",  # 7
    "key_7",  # 8
    "key_8",  # 9
    "key_9",  # 10
    "key_0",  # 11
    # Letters
    "key_a",  # 30
    "key_b",  # 48
    "key_c",  # 46
    "key_d",  # 32
    "key_e",  # 18
    "key_f",  # 33
    "key_g",  # 34
    "key_h",  # 35
    "key_i",  # 23
    "key_j",  # 36
    "key_k",  # 37
    "key_l",  # 38
    "key_m",  # 50
    "key_n",  # 49
    "key_o",  # 24
    "key_p",  # 25
    "key_q",  # 16
    "key_r",  # 19
    "key_s",  # 31
    "key_t",  # 20
    "key_u",  # 22
    "key_v",  # 47
    "key_w",  # 17
    "key_x",  # 45
    "key_y",  # 21
    "key_z",  # 44
    # Keypad Keys
    "key_kpasterisk",  # 55
    "key_kpminus",  # 74
    "key_kpplus",  # 78
    "key_kpdot",  # 83
    "key_kpjpcomma",  # 95
    "key_kpenter",  # 96
    "key_kpslash",  # 98
    "key_kpequal",  # 117
    "key_kpcomma",  # 121
    "key_kpleftparen",  # 179
    "key_kprightparen",  # 180
    # Keypad Numbers
    "key_kp0",  # 82
    "key_kp1",  # 79
    "key_kp2",  # 80
    "key_kp3",  # 81
    "key_kp4",  # 75
    "key_kp5",  # 76
    "key_kp6",  # 77
    "key_kp7",  # 71
    "key_kp8",  # 72
    "key_kp9",  # 73
    # Function keys
    "key_f1",  # 59
    "key_f2",  # 60
    "key_f3",  # 61
    "key_f4",  # 62
    "key_f5",  # 63
    "key_f6",  # 64
    "key_f7",  # 65
    "key_f8",  # 66
    "key_f9",  # 67
    "key_f11",  # 87
    "key_f12",  # 88
    "key_f10",  # 68
    "key_f13",  # 183
    "key_f14",  # 184
    "key_f15",  # 185
    "key_f16",  # 186
    "key_f17",  # 187
    "key_f18",  # 188
    "key_f19",  # 189
    "key_f20",  # 190
    "key_f21",  # 191
    "key_f22",  # 192
    "key_f23",  # 193
    "key_f24",  # 194
    # Media Keys
    "key_playpause",  # 164
    "key_pause",  # 119
    "key_mute",  # 113
    "key_stopcd",  # 166
    "key_forward",  # 159
    "key_ejectcd",  # 161
    "key_nextsong",  # 163
    "key_previoussong",  # 165
    "key_volumedown",  # 114
    "key_volumeup",  # 115
    # Language specific
    "key_katakana",  # 90
    "key_hiragana",  # 91
    "key_henkan",  # 92
    "key_katakanahiragana",  # 93
    "key_muhenkan",  # 94
    "key_zenkakuhankaku",  # 85
    "key_hanguel",  # 122
    "key_hanja",  # 123
    "key_yen",  # 124
    # ?
    "key_unknown",  # 240,
    # Prog for the ally
    "key_prog1",
    "key_prog2",
]

Axis = AbsAxis | RelAxis
Button = Literal["", "keyboard"] | GamepadButton | KeyboardButton | MouseButton

Configuration = Literal[
    # Misc
    "led_mute",  # binary
    "player",
    # Set the aspect ratio of the touchpad used
    # width / height
    "touchpad_aspect_ratio",
    "battery",
    "is_connected",
    "is_attached",
    "battery_left",
    "battery_right",
    "is_connected_left",
    "is_connected_right",
    "is_attached_left",
    "is_attached_right",
    # Commands
    "steam",
]
