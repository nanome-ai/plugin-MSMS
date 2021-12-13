import nanome
from nanome.util import Logs
from nanome.api.shapes import Shape, Mesh
from nanome.api import shapes
import tempfile, sys, subprocess, os
import numpy as np

class MSMSInstance():
    def __init__(self, plugin):
        self.__plugin = plugin

        self._complex = None
        self.nanome_mesh = None
        #Compute Ambient Occlusion using AOEmbree
        self._ao = True
        #Compute a mesh per chain
        self._by_chain = True
        self._probe_radius = 1.4
        #MSMS meshing quality settings
        self._msms_density = 10.0
        self._msms_hdensity = 3
        self._alpha = 255
    
    def set_complex(self, complex):
        self._complex = complex
    
    def set_ao(self, new_ao):
        if new_ao != self._ao:
            self._ao = new_ao
            if self.nanome_mesh:
                if new_ao:
                    self.compute_AO(self._temp_mesh)
                    self.nanome_mesh.colors = np.asarray(self._temp_mesh["colors"])
                else:
                    #Just clear current vertex colors
                    self.nanome_mesh.colors = np.repeat([1.0, 1.0, 1.0, 1.0], len(self.nanome_mesh.vertices) / 3)
                self.nanome_mesh.upload()

    def set_probe_radius(self, new_radius):
        if self._probe_radius != new_radius:
            self._probe_radius = new_radius
            self.compute_mesh()
    
    def set_alpha(self, new_alpha):
        if self._alpha != new_alpha:
            self._alpha = new_alpha
            if self.nanome_mesh:
                self.nanome_mesh.color = nanome.util.Color(255, 255, 255, self._alpha)
                self.nanome_mesh.upload()

    def set_compute_by_chain(self, new_by_chain):
        if self._by_chain != new_by_chain:
            self._by_chain = new_by_chain
            self.compute_mesh()
    
    def set_MSMS_quality(self, density, hdensity):
        if self._msms_density != density or self._msms_hdensity != hdensity:
            self._msms_density = density
            self._msms_hdensity = hdensity
            self.compute_mesh()

    def compute_mesh(self):
        if self.nanome_mesh:
            self.nanome_mesh.destroy()
            self.nanome_mesh = None

        molecule = self._complex._molecules[self._complex.current_frame]

        if self._by_chain and len(list(molecule.chains)) > 0:
            self._temp_mesh = self.compute_mesh_by_chain(molecule)
        else:
            self._temp_mesh = self.compute_whole_mesh(molecule)

        if len(self._temp_mesh["vertices"]) > 0 and self._ao:
            self.compute_AO()

        if len(self._temp_mesh["vertices"]) > 0:
            self.create_nanome_mesh()
        else:
            Logs.error("Failed to compute MSMS")
            self.send_notification(nanome.util.enums.NotificationTypes.message, "MSMS failed")
            return
        
        self.send_notification(nanome.util.enums.NotificationTypes.message, "Receiving mesh (" + str(len(self.nanome_mesh.vertices)/3) + " vertices)")
        self.nanome_mesh.upload()

    def compute_mesh_by_chain(self, molecule):
        result = {}
        result["vertices"] = []
        result["normals"] = []
        result["triangles"] = []

        count_atoms = 0
        for chain in molecule.chains:
            positions = []
            radii = []
            for atom in chain.atoms:
                if not self._selected_only or atom.selected:
                    positions.append(atom.position)
                    radii.append(atom.vdw_radius)
                    count_atoms+=1
            if len(positions) != 0:
                v, n, t = compute_MSMS(positions, radii, self._probe_radius, self._msms_density, self._msms_hdensity)
                self.add_to_temp_mesh(result, v, n, t)
        if count_atoms == 0 and self._selected_only:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.message, "Nothing is selected")
        return result

    def add_to_temp_mesh(self, temp_mesh, v, n, t):
        id_v = int(len(temp_mesh["vertices"]) / 3)
        temp_mesh["vertices"] += v
        temp_mesh["normals"] += n
        for i in t:
            temp_mesh["triangles"].append(i + id_v)

    def compute_whole_mesh(self, molecule):
        result = {}
        result["vertices"] = []
        result["normals"] = []
        result["triangles"] = []

        positions = []
        radii = []

        for atom in molecule.atoms:
            if not self._selected_only or atom.selected:
                positions.append(atom.position)
                radii.append(atom.vdw_radius)

        if len(positions) == 0 and self._selected_only:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.message, "Nothing is selected")
            return

        verts, norms, tri = compute_MSMS(positions, radii, self._probe_radius, self._msms_density, self._msms_hdensity)
        result["vertices"] = verts
        result["normals"] = norms
        result["triangles"] = tri
        return result

    def compute_AO(self):
        cols = []
        aoExePath = get_AOEmbree_Executable()
        if aoExePath != "":
            cols = run_AOEmbree(aoExePath, self._temp_mesh)
        self._temp_mesh["colors"] = cols
    
    def create_nanome_mesh(self):
        self.nanome_mesh = shapes.Mesh()
        self.nanome_mesh.vertices = np.asarray(self._temp_mesh["vertices"]).flatten()
        self.nanome_mesh.normals = np.asarray(self._temp_mesh["normals"]).flatten()
        self.nanome_mesh.triangles = np.asarray(self._temp_mesh["triangles"]).flatten()
        if len(self._temp_mesh["colors"]) == 0:
            self.nanome_mesh.colors = np.repeat([1.0, 1.0, 1.0, 1.0], len(self.nanome_mesh.vertices) / 3)
        else:
            self.nanome_mesh.colors = np.asarray(self._temp_mesh["colors"])
        self.nanome_mesh.anchors[0].anchor_type = nanome.util.enums.ShapeAnchorType.Complex
        self.nanome_mesh.anchors[0].position = nanome.util.Vector3(0, 0, 0)
        self.nanome_mesh.anchors[0].target = self._complex.index
        self.nanome_mesh.color = nanome.util.Color(255, 255, 255, self._alpha)
        self.nanome_mesh.uv = np.repeat([0.0, 0.0], len(self.nanome_mesh.vertices) / 3)
    
def compute_MSMS(positions, radii, probe_radius, density, hdensity):
    verts = []
    norms = []
    faces = []

    msms_input = tempfile.NamedTemporaryFile(delete=False, suffix='.xyzr')
    msms_output = tempfile.NamedTemporaryFile(delete=False, suffix='.out')
    with open(msms_input.name, 'w') as msms_file:
        for i in range(len(positions)):
            msms_file.write("{0:.5f} {1:.5f} {2:.5f} {3:.5f}\n".format(positions[i].x, positions[i].y, positions[i].z, radii[i]))
    exePath = get_MSMS_Executable()

    subprocess.run(args=[exePath, "-if ", msms_input.name, "-of ", msms_output.name, "-probe_radius", str(probe_radius), "-density", str(density), "-hdensity", str(hdensity), "-no_area", "-no_rest", "-no_header"])
    if os.path.isfile(msms_output.name + ".vert") and os.path.isfile(msms_output.name + ".face"):
        verts, norms, indices = parse_MSMS_verts_norms(msms_output.name + ".vert")
        faces = parse_MSMS_Faces(msms_output.name + ".face")
    else:
        Logs.error("Failed to run MSMS")
    return (verts, norms, faces)

def get_MSMS_Executable():
    if sys.platform == "linux" or sys.platform == "linux2":
        return "nanome_msms/MSMS_binaries/Linux/msms"
    elif sys.platform == "darwin":
        return "nanome_msms/MSMS_binaries/OSX/msms"
    elif sys.platform == "win32":
        return "nanome_msms/MSMS_binaries/Windows/msms.exe"

def get_AOEmbree_Executable():
    if sys.platform == "win32":
        return "nanome_msms/AO_binaries/Windows/AOEmbree.exe"
    elif sys.platform == "linux" or sys.platform == "linux2":
        return "nanome_msms/AO_binaries/Linux64/AOEmbree"
    return ""

def parse_MSMS_verts_norms(path):
    verts = []
    norms = []
    indices = []
    with open(path) as f:
        lines = f.readlines()
        for l in lines:
            if l.startswith("#"):
                continue
            s = l.split()
            v = [float(s[0]), float(s[1]), float(s[2])]
            n = [float(s[3]), float(s[4]), float(s[5])]
            idx = int(s[7]) - 1
            verts += v
            norms += n
            indices.append(idx)
    return (verts, norms, indices)

def parse_MSMS_Faces(path):
    tris = []
    with open(path) as f:
        lines = f.readlines()
        for l in lines:
            if l.startswith("#"):
                continue
            s = l.split()
            # 0 base index instead of 1 based
            t = [int(s[0]) - 1, int(s[1]) - 1, int(s[2]) - 1]
            tris += t
    return tris


def run_AOEmbree(exePath, verts, norms, faces, AO_steps = 512, AO_max_dist = 50.0):
    Logs.debug("Run AOEmbree on ", len(verts)/3," vertices")
    #Write mesh to OBJ file
    ao_input = tempfile.NamedTemporaryFile(delete=False, suffix='.obj')
    with open(ao_input.name, "w") as f:
        for v in range(int(len(verts) / 3)):
            f.write("v {0:.6f} {1:.6f} {2:.6f}\n".format(verts[v * 3], verts[v * 3 + 1], verts[v * 3 + 2]))
            f.write("vn {0:.6f} {1:.6f} {2:.6f}\n".format(norms[v * 3], norms[v * 3 + 1], norms[v * 3 + 2]))
        for t in range(int(len(faces) / 3)):
            f.write("f {} {} {}\n".format(faces[t * 3] + 1, faces[t * 3 + 1] + 1, faces[t * 3 + 2] + 1))

    envi = dict(os.environ)
    if sys.platform == "linux" or sys.platform == "linux2":
        envi['LD_LIBRARY_PATH'] = os.path.dirname(os.path.abspath(exePath))

    #Run AOEmbree
    AOvalues = subprocess.run(env=envi, args=[os.path.abspath(exePath), "-n", "-i", ao_input.name, "-a", "-s", str(AO_steps), "-d", str(AO_max_dist)], capture_output=True, text=True)
    vertCol = []
    sAOValues = AOvalues.stdout.split()
    try:
        for i in range(int(len(verts) / 3)):
            ao = float(sAOValues[i])
            vertCol += [ao, ao, ao, 1.0]
    except Exception as e:
        Logs.warning("AO computation failed")
        return []
    return vertCol

def run_AOEmbree(exePath, temp_mesh, AO_steps = 512, AO_max_dist = 50.0):
    verts = temp_mesh["vertices"]
    norms = temp_mesh["normals"]
    faces = temp_mesh["triangles"]
    return run_AOEmbree(exePath, verts, norms, faces, AO_steps, AO_max_dist)