import nanome
import os, math
from nanome.util import Logs, ComplexUtils
from nanome.api import shapes
from sys import platform
from ._MSMSProcess import MSMSProcess
import numpy as np
from functools import partial

class MSMS(nanome.PluginInstance):

    def start(self):
        self._workspace_received = False
        self.create_menu()
        self._process = MSMSProcess(self)

    def create_menu(self):
        self.menu = nanome.ui.Menu()
        menu = self.menu
        menu.title = 'MSMS plugin'
        menu.width = 0.6
        menu.height = 0.7

        ln_lst = menu.root.create_child_node()
        ln_lst.forward_dist = 0.001
        self.lst_obj = ln_lst.add_new_list()

    def show_menu(self):
        self.menu.enabled = True
        self.update_menu(self.menu)

    def populate_objs(self):
        self.lst_obj.items.clear()
        if self._workspace_received:
            for c in self._current_workspace.complexes:
                complex_name = c.name
                item = nanome.ui.LayoutNode()
                item.layout_orientation = nanome.ui.LayoutNode.LayoutTypes.horizontal
                btn_ln = item.create_child_node()
                btn_ln.set_padding(right=0.0)
                btn = btn_ln.add_new_button(complex_name)
                ln_btn = item.create_child_node()
                # ln_btn.set_padding(left=0.8)
                ln_btn.forward_dist = 0.003
                btn2 = ln_btn.add_new_toggle_switch("AO")
                btn2.text.auto_size = False
                btn2.text.size = 0.25
                btn2.selected = True
                btn.register_pressed_callback(partial(self.call_msms_complex, c, btn2, 1.4))
                self.lst_obj.items.append(item)
                c.register_selection_changed_callback(self.ask_updated_worspace)
        self.update_content(self.lst_obj)

    def ask_updated_worspace(self, compl):
        self.on_run()

    def call_msms_complex(self, cur_complex, ao_button, probe_radius, button):
        self._process.start_process(cur_complex, do_ao = ao_button.selected, probe_radius = probe_radius)

    def update(self):
        if self._workspace_received and len(self.lst_obj.items) == 0:
            self.update_menu(self.menu)
            self.populate_objs()

    def on_run(self):
        self.request_workspace(self.on_workspace_received)
        self.show_menu()

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
        self.lst_obj.items.clear()
        self._workspace_received = True
        self._current_workspace = workspace

def main():
    nanome.Plugin.setup("MSMS", "Run MSMS and load the molecular surface in Nanome.", "Computation", False, MSMS)


if __name__ == "__main__":
    main()
