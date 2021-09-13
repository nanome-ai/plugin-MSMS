import sys

sys.path.insert(0, "/Users/martinez/Dev/nanome-lib-xavier/")

import nanome
import math
import tempfile, subprocess, os
from nanome.util import Logs, ComplexUtils
import nanome.api.shapes as shapes
import numpy as np
from sys import platform
from ._MSMSProcess import MSMSProcess


class MSMS(nanome.PluginInstance):

    def start(self):
        self._process = MSMSProcess(self)
        Logs.debug("Start MSMS Plugin")

    def on_run(self):
        self.request_workspace(self.on_workspace_received)

    def update(self):
        self._process.update()

    def stop_msms(self):
        self._process.stop_process()

    def set_run_status(self, running):
        if running:
            self.set_plugin_list_button(nanome.util.enums.PluginListButtonType.run, "Stop")
        else:
            self.set_plugin_list_button(nanome.util.enums.PluginListButtonType.run, "Run")
    
    def on_workspace_received(self, workspace):
        self._process.start_process(workspace)

def main():
    plugin = nanome.Plugin("MSMS", "Run MSMS and load the molecular surface in Nanome.", "Computation", False)
    plugin.set_plugin_class(MSMS)
    plugin.run()


if __name__ == "__main__":
    main()
