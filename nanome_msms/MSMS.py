import nanome
import math
from nanome.util import Logs, ComplexUtils
import numpy as np

class MSMS(nanome.PluginInstance):

    def start(self):
        Logs.debug("Start MSMS Plugin")

    def on_run(self):
        self.request_workspace(self.on_workspace_received)

    def on_workspace_received(self, workspace):
        #Run MSMS on every complex
        for c in workspace.complexes:
            positions = []
            radii = []
            molecule = c._molecules[c.current_frame]
            for atom in molecule.atoms:
                positions.append(atom.position)
                radii.append(atom.radius)

def main():
    plugin = nanome.Plugin("MSMS", "Run MSMS and load the molecular surface in Nanome.", "Computation", False)
    plugin.set_plugin_class(MSMS)
    plugin.run()


if __name__ == "__main__":
    main()
