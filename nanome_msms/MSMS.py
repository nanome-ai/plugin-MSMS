import nanome
from nanome.api import shapes
from nanome.util import async_callback
from ._MSMSProcess import MSMSProcess
import numpy as np
from functools import partial

class MSMS(nanome.AsyncPluginInstance):

    def start(self):
        self._probe_radius = 1.4
        self._list_complexes_received = False
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
        if self._list_complexes_received:
            for c in self._list_complexes:
                complex_name = c.name
                item = nanome.ui.LayoutNode()
                item.layout_orientation = nanome.ui.LayoutNode.LayoutTypes.horizontal
                btn_ln = item.create_child_node()
                btn = btn_ln.add_new_button(complex_name)
                ln_btn = item.create_child_node()
                ln_btn.set_padding(left=0.13)
                ln_btn.forward_dist = 0.001
                btn2 = ln_btn.add_new_toggle_switch("AO")
                btn2.selected = True
                ln_btn.horizontal_align = nanome.util.enums.HorizAlignOptions.Right

                btn.register_pressed_callback(partial(self.get_complex_call_msms, c.index, btn2, self._probe_radius))
                self.lst_obj.items.append(item)
        self.update_content(self.lst_obj)

    @async_callback
    async def get_complex_call_msms(self, complex_id, ao_button, probe_radius, button):
        deep = await self.request_complexes([complex_id])
        self._process.start_process(deep[0], do_ao = ao_button.selected, probe_radius = probe_radius)        

    @async_callback
    async def on_run(self):
        shallow = await self.request_complex_list()
        self.lst_obj.items.clear()
        self._list_complexes_received = True
        self._list_complexes = shallow
        self.show_menu()
        self.update_menu(self.menu)
        self.populate_objs()

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

def main():
    nanome.Plugin.setup("MSMS", "Run MSMS and load the molecular surface in Nanome.", "Computation", False, MSMS)


if __name__ == "__main__":
    main()
