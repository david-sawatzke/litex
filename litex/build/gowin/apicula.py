#
# This file is part of LiteX.
#
# Copyright (c) 2024 Mai Lapyst
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build import tools
from litex.build.gowin.gowin import _build_cst
from litex.build.yosys_nextpnr_toolchain import YosysNextPNRToolchain

class GowinApiculaToolchain(YosysNextPNRToolchain):
    family     = "gowin"
    synth_fmt  = "json"
    pnr_fmt    = "report"
    packer_cmd = "gowin_pack"

    def __init__(self):
        super().__init__()
        self.options = {}
        self.additional_cst_commands = []

    def build_io_constraints(self):
        _build_cst(self.named_sc, self.named_pc, self.additional_cst_commands, self._build_name)
        return (self._build_name + ".cst", "CST")

    def finalize(self):
        devicename = self.platform.devicename
        # Non-exhaustive list of family aliases that Gowin IDE supports but don't have a unique database
        if devicename == "GW1NR-9C":
            devicename = "GW1N-9C"
        elif devicename == "GW1NR-9":
            devicename = "GW1N-9"
        elif devicename == "GW1NSR-4C" or devicename == "GW1NSR-4":
            devicename = "GW1NS-4"
        elif devicename == "GW1NR-4C" or devicename == "GW1NR-4":
            devicename = "GW1N-4"
        elif devicename == "GW2AR-18C":
            devicename = "GW2A-18C"
        elif devicename == "GW2AR-18":
            devicename = "GW2A-18"

        # yosys doesn't know that some variant doesn't have lutram so we tell it
        if devicename in ["GW1NS-4"]:
            self._synth_opts += " -nolutram"

        pnr_opts = "--write {top}_routed.json --top {top} --device {device}" + \
            " --vopt family={devicename} --vopt cst={top}.cst"
        self._pnr_opts += pnr_opts.format(
            top        = self._build_name,
            device     = self.platform.device,
            devicename = devicename
        )

        self._packer_opts += "-d {devicename} -o {top}.fs {top}_routed.json".format(
            devicename = devicename,
            top        = self._build_name
        )

        # use_mspi_as_gpio and friends
        for option, value in self.options.items():
            if option.startswith("use_") and value:
                # Not all options are supported and may be just Gowin's software check
                if option not in ["use_mode_as_gpio"]:
                    self._packer_opts += " --" + option[4:]

        YosysNextPNRToolchain.finalize(self)
        self.apply_hyperram_integration_hack(self._build_name + ".v")

    def build(self, platform, fragment, **kwargs):
        self.platform = platform

        return YosysNextPNRToolchain.build(self, platform, fragment, **kwargs)

    def apply_hyperram_integration_hack(self, v_file):
        # FIXME: Gowin EDA expects a very specific HypeRAM integration pattern, modify generated verilog to match it.

        # Convert to vectors.
        tools.replace_in_file(v_file, "O_hpram_reset_n", "O_hpram_reset_n[0]")
        tools.replace_in_file(v_file, "O_hpram_cs_n",    "O_hpram_cs_n[0]")
        tools.replace_in_file(v_file, "O_hpram_rwds",    "O_hpram_rwds[0]")
        tools.replace_in_file(v_file, "O_hpram_ck ",     "O_hpram_ck[0] ")
        tools.replace_in_file(v_file, "O_hpram_ck_n ",   "O_hpram_ck_n[0] ")
        tools.replace_in_file(v_file, "O_hpram_ck,",     "O_hpram_ck[0],")
        tools.replace_in_file(v_file, "O_hpram_ck_n,",   "O_hpram_ck_n[0],")
        tools.replace_in_file(v_file, "wire          O_hpram_reset_n[0]", "wire [0:0] O_hpram_reset_n")
        tools.replace_in_file(v_file, "wire          O_hpram_cs_n[0]",    "wire [0:0] O_hpram_cs_n")
        tools.replace_in_file(v_file, "wire          IO_hpram_rwds[0]",   "wire [0:0] IO_hpram_rwds")
        tools.replace_in_file(v_file, "wire          O_hpram_ck[0]",      "wire [0:0] O_hpram_ck")
        tools.replace_in_file(v_file, "wire          O_hpram_ck_n[0]",    "wire [0:0] O_hpram_ck_n")

        # Apply Synthesis directives.
        tools.replace_in_file(v_file, "wire [0:0] IO_hpram_rwds,", "wire [0:0] IO_hpram_rwds, /* synthesis syn_tristate = 1 */")
        tools.replace_in_file(v_file, "wire    [7:0] IO_hpram_dq,",    "wire [7:0] IO_hpram_dq,  /* synthesis syn_tristate = 1 */")
        tools.replace_in_file(v_file, "[1:0] IO_psram_rwds,", "[1:0] IO_psram_rwds, /* synthesis syn_tristate = 1 */")
        tools.replace_in_file(v_file, "[15:0] IO_psram_dq,",    "[15:0] IO_psram_dq,  /* synthesis syn_tristate = 1 */")
