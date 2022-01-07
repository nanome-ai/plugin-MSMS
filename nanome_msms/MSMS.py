import nanome
import asyncio
from nanome.api import shapes
from nanome.util import async_callback
from nanome.api.ui import Dropdown, DropdownItem
from ._MSMSProcess import MSMSInstance
from functools import partial
import os

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
IMG_CHECKBOX_ON_PATH = os.path.join(BASE_PATH, 'icons', 'CheckBoxChecked.png')
IMG_CHECKBOX_OFF_PATH = os.path.join(BASE_PATH, 'icons', 'CheckBoxOutline.png')
IMG_EYE_ON_PATH = os.path.join(BASE_PATH, 'icons', 'EntityEye.png')
IMG_EYE_OFF_PATH = os.path.join(BASE_PATH, 'icons', 'InvisibleEye.png')
IMG_COLOR_PATH = os.path.join(BASE_PATH, 'icons', 'ColorMenu.png')

class MSMS(nanome.AsyncPluginInstance):
        
    def start(self):
        self._probe_radius = 1.4
        self._list_complexes_received = False
        self._msms_instances = {}
        self._msms_tasks = {}
        self.create_menu()

    def create_menu(self):
        menu = nanome.ui.Menu.io.from_json(os.path.join(os.path.dirname(__file__), "_NewMSMSMenu.json"))
        self.menu = menu
        eye = menu.root.find_node("Eye").get_content()
        eye.icon.value.set_all(IMG_EYE_ON_PATH)
        color_btn = menu.root.find_node("Color").get_content()
        color_btn.icon.value.set_all(IMG_COLOR_PATH)

        sel_only = self.menu.root.find_node("Selection").get_content()
        sel_only.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
        by_chain = self.menu.root.find_node("ByChain").get_content()
        by_chain.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
        ao_btn = self.menu.root.find_node("AO").get_content()
        ao_btn.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
        
    def show_menu(self):
        self.menu.enabled = True
        self.update_menu(self.menu)

    def populate_objs(self):
        struct_dropdown = self.menu.root.find_node("structures").get_content()

        struct_names = []
        if self._list_complexes_received:
            for c in self._list_complexes:
                item = DropdownItem(c.name)
                item.complex = c
                struct_names.append(item)
                c.register_selection_changed_callback(self.selection_changed)

        struct_dropdown.items = struct_names
        struct_dropdown.register_item_clicked_callback(self.structure_clicked)
        self.update_content(struct_dropdown)

    @async_callback
    async def structure_clicked(self, dropdown, item):
        #Update buttons/sliders based on choice
        complex_id = item.complex.index

        eye = self.menu.root.find_node("Eye").get_content()
        color_btn = self.menu.root.find_node("Color").get_content()
        sel_only = self.menu.root.find_node("Selection").get_content()
        by_chain = self.menu.root.find_node("ByChain").get_content()
        ao_btn = self.menu.root.find_node("AO").get_content()
        opacity_slider = self.menu.root.find_node("Opacity").get_content()
        probe_slider = self.menu.root.find_node("ProbeRadius").get_content()

        eye.unusable = False
        color_btn.unusable = False
        sel_only.unusable = False
        by_chain.unusable = False
        ao_btn.unusable = False
        self.update_content(eye)
        self.update_content(color_btn)
        self.update_content(sel_only)
        self.update_content(by_chain)
        self.update_content(ao_btn)

        # eye.register_pressed_callback(partial(self.get_complex_call_msms, complex_id))
        ao_btn.register_pressed_callback(partial(self.set_ao, complex_id))
        sel_only.register_pressed_callback(partial(self.set_selected_only, complex_id))
        by_chain.register_pressed_callback(partial(self.set_by_chain, complex_id))

        opacity_slider.register_released_callback(partial(self.set_opacity, complex_id))
        probe_slider.register_released_callback(partial(self.set_probe_radius, complex_id))

        if not complex_id in self._msms_instances:
            #Compute new mesh
            await self.get_complex_call_msms(complex_id, ao_btn, None)
        else:
            msms = self._msms_instances[complex_id]
            if msms.selected_only:
                sel_only.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
            else:
                sel_only.icon.value.set_all(IMG_CHECKBOX_OFF_PATH)
            if msms._by_chain:
                by_chain.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
            else:
                by_chain.icon.value.set_all(IMG_CHECKBOX_OFF_PATH)
            if msms.ao:
                ao_btn.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
            else:
                ao_btn.icon.value.set_all(IMG_CHECKBOX_OFF_PATH)
            
            opacity_slider.current_value = msms._alpha
            self.update_content(opacity_slider)

            probe_slider.current_value = msms._probe_radius
            self.update_content(probe_slider)

    @async_callback
    async def selection_changed(self, complex):
        complex_id = complex.index
        deep = await self.request_complexes([complex_id])

        if complex_id in self._msms_instances:
            msms = self._msms_instances[complex_id]
            msms._complex = deep[0]
            t = self._msms_tasks[complex_id]
            #Mesh needs update => selection changed
            if msms.selected_only:
                if not t.done():
                    t.cancel()
                    await t
                    msms.destroy_mesh()
                new_task = asyncio.create_task(msms.compute_mesh())
                self._msms_tasks[complex_id] = new_task
                await new_task

    @async_callback
    async def get_complex_call_msms(self, complex_id, ao_button, button):
        deep = await self.request_complexes([complex_id])
        n_atoms, selected_atoms = count_selected_atoms(deep[0])

        if not complex_id in self._msms_instances:
            #Compute new mesh
            msms = MSMSInstance(self, deep[0])
            t = asyncio.create_task(msms.compute_mesh())
            self._msms_instances[complex_id] = msms
            self._msms_tasks[complex_id] = t
            await t
            if ao_button.selected:
                await msms.set_ao(True)
            return

        msms = self._msms_instances[complex_id]
        if msms.nanome_mesh: #already computed
            t = self._msms_tasks[complex_id]
            #Mesh needs update => selection changed
            if msms.selected_only and msms.atoms_to_process != selected_atoms:
                if not t.done():
                    t.cancel()
                    await t
                new_task = asyncio.create_task(msms.compute_mesh())
                self._msms_tasks[complex_id] = new_task
                await new_task
            #Mesh needs update => number of atoms changed
            elif not msms.selected_only and msms.atoms_to_process != n_atoms:
                if not t.done():
                    t.cancel()
                    await t
                new_task = asyncio.create_task(msms.compute_mesh())
                self._msms_tasks[complex_id] = new_task
                await new_task
            else:
                #Show or hide
                await msms.show(not msms.is_shown)
        else: #Not computed but instance exists
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                await t
            #Compute new mesh with existing instance
            new_task = asyncio.create_task(msms.compute_mesh())
            self._msms_tasks[complex_id] = new_task
            await new_task
            

    @async_callback
    async def set_ao(self, complex_id, button):
        button.selected = not button.selected

        if button.selected:
            button.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
        else:
            button.icon.value.set_all(IMG_CHECKBOX_OFF_PATH)
        self.update_content(button)

        if not complex_id in self._msms_instances:
            deep = await self.request_complexes([complex_id])
            msms = MSMSInstance(self, deep[0])
            self._msms_instances[complex_id] = msms
            t = asyncio.create_task(msms.set_ao(button.selected))
            self._msms_tasks[complex_id] = t
            await t
            return
        
        msms = self._msms_instances[complex_id]
        await msms.set_ao(button.selected)

    @async_callback
    async def set_by_chain(self, complex_id, button):

        button.selected = not button.selected

        if button.selected:
            button.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
        else:
            button.icon.value.set_all(IMG_CHECKBOX_OFF_PATH)
        self.update_content(button)


        if not complex_id in self._msms_instances:
            deep = await self.request_complexes([complex_id])
            msms = MSMSInstance(self, deep[0])
            self._msms_instances[complex_id] = msms
            t = asyncio.create_task(msms.set_compute_by_chain(button.selected, recompute=False))
            self._msms_tasks[complex_id] = t
            await t
            return

        msms = self._msms_instances[complex_id]
        if msms.nanome_mesh: #already computed
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                await t
            t = asyncio.create_task(msms.set_compute_by_chain(button.selected))
            self._msms_tasks[complex_id] = t
            await t

        else: #Not computed but instance exists
            await msms.set_compute_by_chain(button.selected, recompute=False)


    @async_callback
    async def set_selected_only(self, complex_id, button):

        button.selected = not button.selected

        if button.selected:
            button.icon.value.set_all(IMG_CHECKBOX_ON_PATH)
        else:
            button.icon.value.set_all(IMG_CHECKBOX_OFF_PATH)
        self.update_content(button)

        if not complex_id in self._msms_instances:
            deep = await self.request_complexes([complex_id])
            msms = MSMSInstance(self, deep[0])
            self._msms_instances[complex_id] = msms
            t = asyncio.create_task(msms.set_selected_only(button.selected, recompute=False))
            self._msms_tasks[complex_id] = t
            await t
            return

        msms = self._msms_instances[complex_id]
        if msms.nanome_mesh: #already computed
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                await t
            t = asyncio.create_task(msms.set_selected_only(button.selected))
            self._msms_tasks[complex_id] = t
            await t
        else: #Not computed but instance exists
            await msms.set_selected_only(button.selected, recompute=False)

        
    @async_callback
    async def set_msms_quality(self, complex_id, slider):
        if not complex_id in self._msms_instances:
            deep = await self.request_complexes([complex_id])
            msms = MSMSInstance(self, deep[0])
            self._msms_instances[complex_id] = msms
            t = asyncio.create_task(msms.set_MSMS_quality(slider.current_value, msms._msms_hdensity, recompute=False))
            self._msms_tasks[complex_id] = t
            await t
            return

        msms = self._msms_instances[complex_id]
        if msms.nanome_mesh: #already computed
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                await t
            t = asyncio.create_task(msms.set_MSMS_quality(slider.current_value, msms._msms_hdensity))
            self._msms_tasks[complex_id] = t
            await t
        else: #Not computed but instance exists
            await msms.set_MSMS_quality(slider.current_value, msms._msms_hdensity, recompute=False)


    @async_callback
    async def set_probe_radius(self, complex_id, slider):
        if not complex_id in self._msms_instances:
            deep = await self.request_complexes([complex_id])
            msms = MSMSInstance(self, deep[0])
            self._msms_instances[complex_id] = msms
            t = asyncio.create_task(msms.set_probe_radius(round(slider.current_value, 3), recompute=False))
            self._msms_tasks[complex_id] = t
            await t
            return
        
        msms = self._msms_instances[complex_id]
        if msms.nanome_mesh: #already computed
            t = self._msms_tasks[complex_id]
            if not t.done():
                t.cancel()
                await t
            t = asyncio.create_task(msms.set_probe_radius(round(slider.current_value, 3)))
            self._msms_tasks[complex_id] = t
            await t
        else: #Not computed but instance exists
            await msms.set_probe_radius(round(slider.current_value, 3), recompute=False)


    @async_callback
    async def set_opacity(self, complex_id, slider):
        if complex_id in self._msms_instances and self._msms_instances[complex_id].nanome_mesh: #already computed
            msms = self._msms_instances[complex_id]
            await msms.set_alpha(slider.current_value)

    @async_callback
    async def on_run(self):
        shallow = await self.request_complex_list()
        self._list_complexes_received = True
        self._list_complexes = shallow
        self.show_menu()
        self.update_menu(self.menu)
        self.populate_objs()

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
