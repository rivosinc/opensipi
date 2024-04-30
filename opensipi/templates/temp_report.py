# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Created on Nov. 3, 2022
Last updated on Nov. 3, 2022

Description:
    This is a template to create a pdf for PDN report.
"""

pdn_report = {
    "style": {"margin_bottom": 15, "text_align": "j", "page_size": "letter", "margin": [50, 50]},
    "formats": {"url": {"c": "blue", "u": 1}, "title": {"b": 1, "s": 13}},
    "running_sections": {
        "header": {
            "x": "left",
            "y": 20,
            "height": "top",
            "style": {"text_align": "r"},
            "content": [{".b": "This is a header"}],
        },
        "footer": {
            "x": "left",
            "y": 740,
            "height": "bottom",
            "style": {"text_align": "c"},
            "content": [{".": ["Page ", {"var": "$page"}]}],
        },
    },
    "sections": [
        {  # 0, summary
            "style": {"page_numbering_style": "arabic"},
            "running_sections": ["footer"],
            "content": [
                {
                    "widths": [1, 2],
                    "style": {"s": 9, "border_width": 0, "margin_left": 30, "margin_right": 30},
                    "table": [
                        [
                            {"colspan": 2, ".b": "Report", "style": {"s": 18, "text_align": "c"}},
                            None,
                        ],
                        ["", ""],
                    ],
                }
            ],
        },
        {  # 1, table
            "style": {"page_numbering_style": "arabic"},
            "running_sections": ["footer"],
            "content": [
                {
                    "widths": [3, 1, 1, 1, 1],
                    "style": {"s": 9, "border_width": 0, "margin_left": 30, "margin_right": 30},
                    "fills": [{"pos": "1::2;:", "color": 0.7}],
                    "borders": [{"pos": "h0,1,-1;:", "width": 0.5}],
                    "table": [["Title", "DCR (mOhm)", "L@100MHz (pH)", "C@10kHz (uF)", "Figure"]],
                }
            ],
        },
        {  # 2, figures
            "style": {"page_numbering_style": "arabic"},
            "running_sections": ["footer"],
            "content": [],
        },
    ],
}

io_report = {
    "style": {"margin_bottom": 15, "text_align": "j", "page_size": "letter", "margin": [50, 50]},
    "formats": {"url": {"c": "blue", "u": 1}, "title": {"b": 1, "s": 13}},
    "running_sections": {
        "header": {
            "x": "left",
            "y": 20,
            "height": "top",
            "style": {"text_align": "r"},
            "content": [{".b": "This is a header"}],
        },
        "footer": {
            "x": "left",
            "y": 740,
            "height": "bottom",
            "style": {"text_align": "c"},
            "content": [{".": ["Page ", {"var": "$page"}]}],
        },
    },
    "sections": [
        {  # 0, summary
            "style": {"page_numbering_style": "arabic"},
            "running_sections": ["footer"],
            "content": [
                {
                    "widths": [1, 2],
                    "style": {"s": 9, "border_width": 0, "margin_left": 30, "margin_right": 30},
                    "table": [
                        [
                            {"colspan": 2, ".b": "Report", "style": {"s": 18, "text_align": "c"}},
                            None,
                        ],
                        ["", ""],
                    ],
                }
            ],
        },
        {  # 1, table
            "style": {"page_numbering_style": "arabic"},
            "running_sections": ["footer"],
            "content": [
                {
                    "widths": [3, 1, 1],
                    "style": {"s": 9, "border_width": 0, "margin_left": 30, "margin_right": 30},
                    "fills": [{"pos": "1::2;:", "color": 0.7}],
                    "borders": [{"pos": "h0,1,-1;:", "width": 0.5}],
                    "table": [["Title", "IL@f0 (dB)", "IL Figure"]],
                },
                {
                    "widths": [3, 1, 1],
                    "style": {"s": 9, "border_width": 0, "margin_left": 30, "margin_right": 30},
                    "fills": [{"pos": "1::2;:", "color": 0.7}],
                    "borders": [{"pos": "h0,1,-1;:", "width": 0.5}],
                    "table": [["Title", "RL@f0 (dB)", "RL Figure"]],
                },
            ],
        },
        {  # 2, figures
            "style": {"page_numbering_style": "arabic"},
            "running_sections": ["footer"],
            "content": [],
        },
    ],
}
