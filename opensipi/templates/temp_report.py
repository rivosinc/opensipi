# SPDX-FileCopyrightText: Copyright (c) Meta Platforms, Inc. and affiliates.
# SPDX-FileCopyrightText: © 2024 Rivos Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Author: yanshengw@
Created on Nov. 3, 2022
Last updated on Nov. 3, 2022

Description:
    This is a template to create a pdf for PDN report.

    The module now holds a template per report type. Each one is a pdf_reports
document skeleton: page style, running header and footer, and three sections,
being the summary, the result tables, and the figures. ``Platform`` fills them
in at report time by appending rows to the section 1 tables and figure blocks
to section 2, so the templates supply the layout and the headings while the run
supplies the data.

    The section 1 blocks are addressed positionally, by the rank a
post-processing key is given in ``POST_PROCESS_KEY_ORDER_PDN`` or
``POST_PROCESS_KEY_ORDER_IO``. Reordering the blocks, or adding one out of
order, silently sends results to the wrong table.

Attributes:
    pdn_report (dict): Template for a PDN report. Section 1 holds two table
        blocks, matching the PDN keys ``ZOPEN`` and ``ZSHORT``.
    io_report (dict): Template for an HSIO or LSIO report. Section 1 holds six
        table blocks, matching the IO keys ``IL``, ``RL``, ``TDR``, ``IL_MM``,
        ``RL_MM``, and ``TDR_MM`` in that rank order.

Note:
    The headings of the two mixed-mode blocks of ``io_report`` do not match the
    keys that index them. Block 3, filled from ``IL_MM``, is headed
    ``"RL@f0 (dB)"``, and block 4, filled from ``RL_MM``, is headed
    ``"IL@f0 (dB)"``. Only the headings are affected; the rows still land in
    distinct blocks.
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
                    "table": [["Title", "DCR (mOhm)", "L@100MHz (pH)", "C@10kHz (nF)", "Figure"]],
                },
                {
                    "widths": [3, 1, 1, 1, 1],
                    "style": {"s": 9, "border_width": 0, "margin_left": 30, "margin_right": 30},
                    "fills": [{"pos": "1::2;:", "color": 0.7}],
                    "borders": [{"pos": "h0,1,-1;:", "width": 0.5}],
                    "table": [["Title", "DCR (mOhm)", "L@100MHz (pH)", "C@10kHz (nF)", "Figure"]],
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
                {
                    "widths": [3, 1, 1],
                    "style": {"s": 9, "border_width": 0, "margin_left": 30, "margin_right": 30},
                    "fills": [{"pos": "1::2;:", "color": 0.7}],
                    "borders": [{"pos": "h0,1,-1;:", "width": 0.5}],
                    "table": [["Title", "Zc (Ohm)", "TDR Figure"]],
                },
                {
                    "widths": [3, 1, 1],
                    "style": {"s": 9, "border_width": 0, "margin_left": 30, "margin_right": 30},
                    "fills": [{"pos": "1::2;:", "color": 0.7}],
                    "borders": [{"pos": "h0,1,-1;:", "width": 0.5}],
                    "table": [["Title", "RL@f0 (dB)", "RL Figure"]],
                },
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
                    "table": [["Title", "Zc (Ohm)", "TDR Figure"]],
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
