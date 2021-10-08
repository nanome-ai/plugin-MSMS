import sys
sys.path.insert(0, "D:/Dev/nanome-lib-fork/")

import nanome
import os, math
from nanome.util import Logs, ComplexUtils
from nanome.api import shapes
from sys import platform
from ._MSMSProcess import MSMSProcess
import numpy as np


class MSMS(nanome.PluginInstance):

    def start(self):
        self._process = MSMSProcess(self)
        Logs.debug("Start MSMS Plugin")

    def on_run(self):
        self.request_workspace(self.on_workspace_received)

    def stop_msms(self):
        self._process.stop_process()

    def set_run_status(self, running):
        if running:
            self.set_plugin_list_button(nanome.util.enums.PluginListButtonType.run, "Stop")
        else:
            self.set_plugin_list_button(nanome.util.enums.PluginListButtonType.run, "Run")

    def make_mesh(self, v, n, t, complexIdex, colors = []):
        #Create nanome shape
        mesh = shapes.Mesh()
        mesh.vertices = np.asarray(v).flatten()
        mesh.normals = np.asarray(n).flatten()
        mesh.triangles = np.asarray(t).flatten()
        if len(colors) == 0:
            mesh.colors = np.repeat([1.0, 1.0, 1.0, 1.0], len(mesh.vertices) / 3)
        else:
            mesh.colors = np.asarray(colors)
        mesh.anchors[0].anchor_type = nanome.util.enums.ShapeAnchorType.Complex
        mesh.anchors[0].position = nanome.util.Vector3(0, 0, 0)
        mesh.anchors[0].target = complexIdex
        mesh.color = nanome.util.Color(255, 255, 255, 255)
        mesh.uv = np.repeat([0.0, 0.0], len(mesh.vertices) / 3)

        self.send_notification(nanome.util.enums.NotificationTypes.message, "Receiving mesh (" + str(len(mesh.vertices)/3) + " vertices)")
        mesh.upload()

    def on_workspace_received(self, workspace):
        self._process.start_process(workspace, do_ao = True, probe_radius = 1.4)

def main():
    nanome.Plugin.setup("MSMS", "Run MSMS and load the molecular surface in Nanome.", "Computation", False, MSMS)


if __name__ == "__main__":
    main()
