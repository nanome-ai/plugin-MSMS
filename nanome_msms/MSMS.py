import nanome
import asyncio
from nanome.api import shapes
from nanome.util import async_callback
from ._MSMSProcess import MSMSInstance
from functools import partial

class MSMS(nanome.AsyncPluginInstance):

    def start(self):
        self._probe_radius = 1.4
        self._list_complexes_received = False
        self._msms_instances = {}
        self._msms_tasks = {}
        self.create_menu()

    def create_menu(self):
        self.menu = nanome.ui.Menu()
        menu = self.menu
        menu.title = 'MSMS plugin'
        menu.width = 0.9
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

                btn.register_pressed_callback(partial(self.get_complex_call_msms, c.index, btn2))
                btn2.register_pressed_callback(partial(self.set_ao, c.index))
                self.lst_obj.items.append(item)
        self.update_content(self.lst_obj)

    @async_callback
    async def get_complex_call_msms(self, complex_id, ao_button, button):
        deep = await self.request_complexes([complex_id])
        n_atoms, selected_atoms = count_selected_atoms(deep[0])

        if complex_id in self._msms_instances: #already computed
            msms = self._msms_instances[complex_id]
            t = self._msms_tasks[complex_id]
            #Mesh needs update => selection changed
            if msms.selected_only and msms.atoms_to_process != selected_atoms:
                if not t.done():
                    t.cancel()
                    msms.destroy_mesh()
                new_task = asyncio.create_task(msms.compute_mesh())
                self._msms_tasks[complex_id] = new_task
                await new_task
            #Mesh needs update => number of atoms changed
            elif not msms.selected_only and msms.atoms_to_process != n_atoms:
                if not t.done():
                    t.cancel()
                    msms.destroy_mesh()
                new_task = asyncio.create_task(msms.compute_mesh())
                self._msms_tasks[complex_id] = new_task
                await new_task
            else:
                #Show or hide
                msms.show(not msms.is_shown)
        else:
            #Compute new mesh
            msms = MSMSInstance(self, deep[0])
            t = asyncio.create_task(msms.compute_mesh())
            self._msms_instances[complex_id] = msms
            self._msms_tasks[complex_id] = t
            await t
            await msms.set_ao(ao_button.selected)
            

    @async_callback
    async def set_ao(self, complex_id, button):
        if complex_id in self._msms_instances: #already computed
            msms = self._msms_instances[complex_id]
            await msms.set_ao(button.selected)

    @async_callback
    async def set_by_chain(self, complex_id, button):
        if complex_id in self._msms_instances: #already computed
            msms = self._msms_instances[complex_id]
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                msms.destroy_mesh()
            t = asyncio.create_task(msms.set_compute_by_chain(button.selected))
            self._msms_tasks[complex_id] = t
            await t

    @async_callback
    async def set_selected_only(self, complex_id, button):
        if complex_id in self._msms_instances: #already computed
            msms = self._msms_instances[complex_id]
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                msms.destroy_mesh()
            t = asyncio.create_task(msms.set_selected_only(button.selected))
            self._msms_tasks[complex_id] = t
            await t
        
    @async_callback
    async def set_msms_quality(self, complex_id, slider):
        if complex_id in self._msms_instances: #already computed
            msms = self._msms_instances[complex_id]
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                msms.destroy_mesh()
            t = asyncio.create_task(msms.set_MSMS_quality(slider.current_value, msms._msms_hdensity))
            self._msms_tasks[complex_id] = t
            await t

    @async_callback
    async def on_run(self):
        shallow = await self.request_complex_list()
        self.lst_obj.items.clear()
        self._list_complexes_received = True
        self._list_complexes = shallow
        self.show_menu()
        self.update_menu(self.menu)
        self.populate_objs()

    @async_callback
    async def set_opacity(self, complex_id, slider):
        if complex_id in self._msms_instances: #already computed
            msms = self._msms_instances[complex_id]
            await msms.set_alpha(slider.current_value)
    
    @async_callback
    async def set_probe_radius(self, complex_id, slider):
        if complex_id in self._msms_instances: #already computed
            msms = self._msms_instances[complex_id]
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                msms.destroy_mesh()
            t = asyncio.create_task(msms.set_probe_radius(slider.current_value))
            self._msms_tasks[complex_id] = t
            await t

    def set_run_status(self, running):
        if running:
            self.set_plugin_list_button(nanome.util.enums.PluginListButtonType.run, "Stop")
        else:
            self.set_plugin_list_button(nanome.util.enums.PluginListButtonType.run, "Run")

def count_selected_atoms(complex):
    molecule = complex._molecules[complex.current_frame]
    count = 0
    count_selected = 0
    for a in molecule.atoms:
        count += 1
        if a.selected:
            count_selected += 1
    return count, count_selected

def main():
    nanome.Plugin.setup("MSMS", "Run MSMS and load the molecular surface in Nanome.", "Computation", False, MSMS)

if __name__ == "__main__":
    main()
