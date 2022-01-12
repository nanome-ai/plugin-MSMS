import nanome
from nanome.util import Logs, enums
from nanome.api import shapes
from nanome.api.shapes import Shape
import tempfile, sys, subprocess, os
import numpy as np
import asyncio
import randomcolor

class MSMSInstance():
    def __init__(self, plugin, complex):
        self.__plugin = plugin
        self._complex = complex

        self.nanome_mesh = None
        self.is_shown = False
        #Compute Ambient Occlusion using AOEmbree
        self.ao = False
        #Only compute for selected atoms
        self.selected_only = True

        self.atoms_to_process = 0

        #Wait to compute a new mesh until mesh is uploaded
        self._is_busy = False

        #Compute a mesh per chain
        self._by_chain = True
        self._probe_radius = 1.4
        #MSMS meshing quality settings
        self._msms_density = 10.0
        self._msms_hdensity = 3

        self._alpha = 255
        self._colorv3 = nanome.util.Vector3(255, 255, 255)
        self._color_scheme = enums.ColorScheme.Monochrome

        self._custom_quality = False

    async def show(self, enabled = True):
        if not self.nanome_mesh:
            return
        if self.is_shown != enabled:
            self.is_shown = enabled
            if self.is_shown:
                self.nanome_mesh.color = nanome.util.Color(self._colorv3.x, self._colorv3.y, self._colorv3.z, self._alpha)
            else:
                self.nanome_mesh.color = nanome.util.Color(self._colorv3.x, self._colorv3.y, self._colorv3.z, 0)
            await self.finished()
            self.upload_mesh()

    async def set_color(self, new_color):
        if type(new_color == nanome.util.Color):
            new_color = [new_color.r, new_color.g, new_color.b]
        if len(new_color) != 3:
            print("Color has to be an array of 3 int")
            return
        if new_color[0] != self._colorv3.x or new_color[1] != self._colorv3.y or new_color[2] != self._colorv3.z:
            self._colorv3 = nanome.util.Vector3(new_color[0], new_color[1], new_color[2])
            if self.nanome_mesh:
                if self.is_shown:
                    self.nanome_mesh.color = nanome.util.Color(self._colorv3.x, self._colorv3.y, self._colorv3.z, self._alpha)
                else:
                    self.nanome_mesh.color = nanome.util.Color(self._colorv3.x, self._colorv3.y, self._colorv3.z, 0)
                await self.finished()
                self.upload_mesh()

    async def set_color_scheme(self, new_scheme):
        if self._color_scheme != new_scheme:
            self._color_scheme = new_scheme
            await self.finished()
            if self.nanome_mesh:
                self.apply_color_scheme()
                self.upload_mesh()
                await self.finished()
        
    def apply_color_scheme(self):
        if self._color_scheme == enums.ColorScheme.Monochrome:
            #Just clear current vertex colors
            self._temp_mesh["colors"] = np.repeat(1.0, 4 * len(self.nanome_mesh.vertices) / 3)
        elif self._color_scheme == enums.ColorScheme.Chain:
            self._temp_mesh["colors"] = self._color_scheme_chain().flatten()
        elif self._color_scheme == enums.ColorScheme.Element:
            self._temp_mesh["colors"] = self._color_scheme_element().flatten()
        elif self._color_scheme == enums.ColorScheme.Residue:
            self._temp_mesh["colors"] = self._color_scheme_residue().flatten()
        elif self._color_scheme == enums.ColorScheme.SecondaryStructure:
            self._temp_mesh["colors"] = self._color_scheme_ss().flatten()
        else:
            Logs.warning("Unsupported color scheme (",self._color_scheme,")")
            self._temp_mesh["colors"] = np.repeat(1.0, 4 * len(self.nanome_mesh.vertices) / 3)
            self._color_scheme = enums.ColorScheme.Monochrome

        #Reconstruct color array and darken it with AO values
        self.nanome_mesh.colors = np.asarray(self.darken_colors()).flatten()
    
    def _color_scheme_chain(self):
        molecule = self._complex._molecules[self._complex.current_frame]
        n_chain = len(list(molecule.chains))

        rdcolor = randomcolor.RandomColor(seed=1234)
        chain_cols = rdcolor.generate(format_="rgb", count=n_chain)

        id_chain = 0
        color_per_atom = []
        for c in molecule.chains:
            col = chain_cols[id_chain]
            col = col.replace("rgb(", "").replace(")","").replace(",","").split()
            chain_color = [int(i)/255.0 for i in col] + [1.0]
            id_chain+=1
            for atom in c.atoms:
                color_per_atom.append(chain_color)

        colors = []
        for idx in self._temp_mesh["indices"]:
            colors.append(color_per_atom[idx])
        return np.array(colors)

    def _color_scheme_residue(self):
        molecule = self._complex._molecules[self._complex.current_frame]
        rdcolor = randomcolor.RandomColor(seed=1234)
        residue_to_color = {}

        color_per_atom = []
        for c in molecule.chains:
            for a in c.atoms:
                if not a.residue.name in residue_to_color:
                    col = rdcolor.generate(format_="rgb")[0]
                    col = col.replace("rgb(", "").replace(")","").replace(",","").split()
                    r_color = [int(i)/255.0 for i in col] + [1.0]
                    residue_to_color[a.residue.name] = r_color
                residue_color = residue_to_color[a.residue.name]
                color_per_atom.append(residue_color)
        
        colors = []
        for idx in self._temp_mesh["indices"]:
            colors.append(color_per_atom[idx])
        return np.array(colors)

    def _color_scheme_element(self):
        molecule = self._complex._molecules[self._complex.current_frame]

        color_per_atom = [cpk_colors(a) for a in molecule.atoms]
        
        colors = []
        for idx in self._temp_mesh["indices"]:
            colors.append(color_per_atom[idx])
        return np.array(colors)
    
    def _color_scheme_ss(self):
        molecule = self._complex._molecules[self._complex.current_frame]

        unknown_color = [0.5, 0.5, 0.5, 1.0]
        coil_color = [0.0784, 1.0, 0.0784, 1.0]
        sheet_color = [0.941, 0.941, 0, 1.0]
        helix_color = [1.0, 0.0784, 0.0784, 1.0]

        ss_colors = [unknown_color, coil_color, sheet_color, helix_color]

        color_per_atom = []
        for c in molecule.chains:
            for a in c.atoms:
                ss = int(a.residue.secondary_structure)
                a_color = ss_colors[ss]
                color_per_atom.append(a_color)
        
        colors = []
        for idx in self._temp_mesh["indices"]:
            colors.append(color_per_atom[idx])
        return np.array(colors)
    
    def done_upload(self, m):
        self._is_busy = False
    
    def done_destroy(self, m):
        self._is_busy = False
        self.nanome_mesh = None
    
    def upload_mesh(self):
        self.nanome_mesh.upload(self.done_upload)

    def destroy_mesh(self):
        if self.nanome_mesh:
            self.nanome_mesh.destroy(self.done_destroy)
        self._temp_mesh = None

    async def set_ao(self, new_ao):
        if new_ao != self.ao:
            self.ao = new_ao
            await self.finished()
            if self.nanome_mesh:
                if new_ao:
                    self._is_busy = True
                    self.compute_AO()
                    if self._color_scheme == enums.ColorScheme.Monochrome:
                        #Clear color array
                        self._temp_mesh["colors"] = np.repeat(1.0, 4 * len(self._temp_mesh["vertices"]) / 3)
                else:
                    #Clear AO array
                    self._temp_mesh["ao"] = np.repeat(1.0, len(self._temp_mesh["vertices"]) / 3)
                #Reconstruct color array and darken it with AO values
                self.nanome_mesh.colors = np.asarray(self.darken_colors()).flatten()
                self.upload_mesh()
                await self.finished()

    def darken_colors(self):
        if len(self._temp_mesh["ao"]) < 1:
            return self._temp_mesh["colors"]
        cols = []
        for i in range(int(len(self._temp_mesh["vertices"])/3)):
            ao = self._temp_mesh["ao"][i]
            r,g,b,a = self._temp_mesh["colors"][i*4:i*4+4]
            cols.append([r * ao, g * ao, b * ao, a])
        return cols

    async def set_probe_radius(self, new_radius, recompute=True):
        if self._probe_radius != new_radius:
            self._probe_radius = new_radius
            if recompute:
                await self.compute_mesh()
    
    async def set_alpha(self, new_alpha):
        if self._alpha != new_alpha:
            self._alpha = new_alpha
            await self.finished()
            if self.nanome_mesh:
                self._is_busy = True
                if self.is_shown:
                    self.nanome_mesh.color = nanome.util.Color(self._colorv3.x, self._colorv3.y, self._colorv3.z, self._alpha)
                else:
                    self.nanome_mesh.color = nanome.util.Color(self._colorv3.x, self._colorv3.y, self._colorv3.z, 0)
                self.upload_mesh()
                await self.finished()

    async def set_compute_by_chain(self, new_by_chain, recompute=True):
        if self._by_chain != new_by_chain:
            self._by_chain = new_by_chain
            if recompute:
                await self.compute_mesh()
    
    async def set_selected_only(self, new_selected_only, recompute=True):
        if self.selected_only != new_selected_only:
            self.selected_only = new_selected_only
            if recompute:
                await self.compute_mesh()

    async def set_MSMS_quality(self, density, hdensity, recompute=True):
        if self._msms_density != density or self._msms_hdensity != hdensity:
            self._msms_density = density
            self._msms_hdensity = hdensity
            self._custom_quality = True
            if recompute:
                await self.compute_mesh()

    async def finished(self):
        if not self._is_busy:
            return
        max_time = 60.0 * 5 #5 min
        count_time = 0.0
        step = 0.1
        while self._is_busy:
            await asyncio.sleep(step)
            count_time += step
            if count_time >= max_time:
                return

    async def compute_mesh(self):

        #Wait for previous mesh to be computed if there is any
        await self.finished()
        self.destroy_mesh()
        #Wait for the mesh to be destroyed
        await self.finished()

        self._is_busy = True

        Logs.debug("Computing MSMS mesh with: AO:{0} | ByChain:{1} | Selection:{2} | ProbeRadius:{3}".format(self.ao, self._by_chain, self.selected_only, self._probe_radius))

        molecule = self._complex._molecules[self._complex.current_frame]

        if self._by_chain and len(list(molecule.chains)) > 0:
            self._temp_mesh = self._compute_mesh_by_chain(molecule)
        else:
            self._temp_mesh = self._compute_whole_mesh(molecule)

        if len(self._temp_mesh["vertices"]) > 0 and self.ao:
            self.compute_AO()
        else:
            N_vert = len(self._temp_mesh["vertices"])/3
            self._temp_mesh["colors"] = np.repeat(1.0, 4 * N_vert)

        if len(self._temp_mesh["vertices"]) > 0:
            self._create_nanome_mesh()
        else:
            Logs.error("Failed to compute MSMS")
            self.destroy_mesh()
            self._is_busy = False
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.message, "MSMS failed")
            return
        

        self.apply_color_scheme()

        self.__plugin.send_notification(nanome.util.enums.NotificationTypes.message, "Receiving mesh (" + str(len(self.nanome_mesh.vertices)/3) + " vertices)")
        self.upload_mesh()
        self.is_shown = True
        await self.finished()

    def auto_MSMS_quality(self, N):
        if N > 5000:
            self._msms_hdensity = 3.0
        if N > 20000:
            self._msms_hdensity = 1.0

    def count_selected_atoms(self, mol):
        count_atoms = 0
        for chain in mol.chains:
            for atom in chain.atoms:
                if not self.selected_only or atom.selected:
                    count_atoms+=1
        return count_atoms

    def _compute_mesh_by_chain(self, molecule):
        self.atoms_to_process = 0
        result = {}
        result["vertices"] = []
        result["normals"] = []
        result["triangles"] = []
        result["colors"] = []
        result["indices"] = []
        result["ao"] = []

        self.atoms_to_process = self.count_selected_atoms(molecule)

        if self.atoms_to_process == 0 and self.selected_only:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.message, "Nothing is selected")
            return result

        if not self._custom_quality:
            self.auto_MSMS_quality(self.atoms_to_process)

        count_atoms = 0
        for chain in molecule.chains:
            positions = []
            radii = []
            for atom in chain.atoms:
                if not self.selected_only or atom.selected:
                    positions.append(atom.position)
                    rad = atom.vdw_radius
                    #Replace unknown atoms with Carbons
                    if rad < 0.0001:
                        rad = 1.7
                    radii.append(rad)
            if len(positions) != 0:
                v, n, t, i = compute_MSMS(positions, radii, self._probe_radius, self._msms_density, self._msms_hdensity)
                self._add_to_temp_mesh(result, count_atoms, v, n, t, i)
            
            count_atoms += len(positions)

        return result

    def _add_to_temp_mesh(self, temp_mesh, n_atoms, v, n, t, i):

        id_v = int(len(temp_mesh["vertices"]) / 3)
        temp_mesh["vertices"] += v
        temp_mesh["normals"] += n
        for ind in i:
            temp_mesh["indices"].append(ind + n_atoms)
        for i in t:
            temp_mesh["triangles"].append(i + id_v)

    def _compute_whole_mesh(self, molecule):
        self.atoms_to_process = 0
        result = {}
        result["vertices"] = []
        result["normals"] = []
        result["triangles"] = []
        result["colors"] = []
        result["indices"] = []
        result["ao"] = []

        positions = []
        radii = []

        count_atoms = 0
        for atom in molecule.atoms:
            if not self.selected_only or atom.selected:
                positions.append(atom.position)
                radii.append(atom.vdw_radius)
                count_atoms+=1

        self.atoms_to_process = count_atoms

        if len(positions) == 0 and self.selected_only:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.message, "Nothing is selected")
            return result

        if not self._custom_quality:
            self.auto_MSMS_quality(self.atoms_to_process)

        verts, norms, tri, indices = compute_MSMS(positions, radii, self._probe_radius, self._msms_density, self._msms_hdensity)
        result["vertices"] = verts
        result["normals"] = norms
        result["triangles"] = tri
        result["indices"] = indices

        return result

    def compute_AO(self):
        cols = []
        aoExePath = get_AOEmbree_Executable()
        if aoExePath != "":
            cols = run_AOEmbree(aoExePath, self._temp_mesh)
        self._temp_mesh["ao"] = cols
    
    def _create_nanome_mesh(self):
        self.nanome_mesh = shapes.Mesh()
        self.nanome_mesh.vertices = np.asarray(self._temp_mesh["vertices"]).flatten()
        self.nanome_mesh.normals = np.asarray(self._temp_mesh["normals"]).flatten()
        self.nanome_mesh.triangles = np.asarray(self._temp_mesh["triangles"]).flatten()
        if len(self._temp_mesh["colors"]) == 0:
            self.nanome_mesh.colors = np.repeat(1.0,  4 * len(self.nanome_mesh.vertices) / 3)
        else:
            self.nanome_mesh.colors = np.asarray(self._temp_mesh["colors"]).flatten()
        self.nanome_mesh.anchors[0].anchor_type = nanome.util.enums.ShapeAnchorType.Complex
        self.nanome_mesh.anchors[0].position = nanome.util.Vector3(0, 0, 0)
        self.nanome_mesh.anchors[0].target = self._complex.index
        self.nanome_mesh.color = nanome.util.Color(self._colorv3.x, self._colorv3.y, self._colorv3.z, self._alpha)
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

    subprocess.run(stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        args=[exePath, "-if ", msms_input.name, "-of ", msms_output.name, "-probe_radius", str(probe_radius), "-density", str(density), "-hdensity", str(hdensity), "-no_area", "-no_rest", "-no_header"])
    if os.path.isfile(msms_output.name + ".vert") and os.path.isfile(msms_output.name + ".face"):
        verts, norms, indices = parse_MSMS_verts_norms(msms_output.name + ".vert")
        faces = parse_MSMS_Faces(msms_output.name + ".face")
    else:
        Logs.error("Failed to run MSMS")
    return (verts, norms, faces, indices)

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


def run_AOEmbree(exePath, temp_mesh, AO_steps = 512, AO_max_dist = 50.0):
    verts = temp_mesh["vertices"]
    norms = temp_mesh["normals"]
    faces = temp_mesh["triangles"]

    Logs.debug("Run AOEmbree on", int(len(verts)/3),"vertices")
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
            vertCol.append(ao)
    except Exception as e:
        Logs.warning("AO computation failed")
        return []
    return vertCol

def cpk_colors(a):
    colors = {}
    colors["xx"] = "#030303"
    colors["h"] = "#FFFFFF"
    colors["he"] = "#D9FFFF"
    colors["li"] = "#CC80FF"
    colors["be"] = "#C2FF00"
    colors["b"] = "#FFB5B5"
    colors["c"] = "#909090"
    colors["n"] = "#3050F8"
    colors["o"] = "#FF0D0D"
    colors["f"] = "#B5FFFF"
    colors["ne"] = "#B3E3F5"
    colors["na"] = "#AB5CF2"
    colors["mg"] = "#8AFF00"
    colors["al"] = "#BFA6A6"
    colors["si"] = "#F0C8A0"
    colors["p"] = "#FF8000"
    colors["s"] = "#FFFF30"
    colors["cl"] = "#1FF01F"
    colors["ar"] = "#80D1E3"
    colors["k"] = "#8F40D4"
    colors["ca"] = "#3DFF00"
    colors["sc"] = "#E6E6E6"
    colors["ti"] = "#BFC2C7"
    colors["v"] = "#A6A6AB"
    colors["cr"] = "#8A99C7"
    colors["mn"] = "#9C7AC7"
    colors["fe"] = "#E06633"
    colors["co"] = "#F090A0"
    colors["ni"] = "#50D050"
    colors["cu"] = "#C88033"
    colors["zn"] = "#7D80B0"
    colors["ga"] = "#C28F8F"
    colors["ge"] = "#668F8F"
    colors["as"] = "#BD80E3"
    colors["se"] = "#FFA100"
    colors["br"] = "#A62929"
    colors["kr"] = "#5CB8D1"
    colors["rb"] = "#702EB0"
    colors["sr"] = "#00FF00"
    colors["y"] = "#94FFFF"
    colors["zr"] = "#94E0E0"
    colors["nb"] = "#73C2C9"
    colors["mo"] = "#54B5B5"
    colors["tc"] = "#3B9E9E"
    colors["ru"] = "#248F8F"
    colors["rh"] = "#0A7D8C"
    colors["pd"] = "#006985"
    colors["ag"] = "#C0C0C0"
    colors["cd"] = "#FFD98F"
    colors["in"] = "#A67573"
    colors["sn"] = "#668080"
    colors["sb"] = "#9E63B5"
    colors["te"] = "#D47A00"
    colors["i"] = "#940094"
    colors["xe"] = "#429EB0"
    colors["cs"] = "#57178F"
    colors["ba"] = "#00C900"
    colors["la"] = "#70D4FF"
    colors["ce"] = "#FFFFC7"
    colors["pr"] = "#D9FFC7"
    colors["nd"] = "#C7FFC7"
    colors["pm"] = "#A3FFC7"
    colors["sm"] = "#8FFFC7"
    colors["eu"] = "#61FFC7"
    colors["gd"] = "#45FFC7"
    colors["tb"] = "#30FFC7"
    colors["dy"] = "#1FFFC7"
    colors["ho"] = "#00FF9C"
    colors["er"] = "#00E675"
    colors["tm"] = "#00D452"
    colors["yb"] = "#00BF38"
    colors["lu"] = "#00AB24"
    colors["hf"] = "#4DC2FF"
    colors["ta"] = "#4DA6FF"
    colors["w"] = "#2194D6"
    colors["re"] = "#267DAB"
    colors["os"] = "#266696"
    colors["ir"] = "#175487"
    colors["pt"] = "#D0D0E0"
    colors["au"] = "#FFD123"
    colors["hg"] = "#B8B8D0"
    colors["tl"] = "#A6544D"
    colors["pb"] = "#575961"
    colors["bi"] = "#9E4FB5"
    colors["po"] = "#AB5C00"
    colors["at"] = "#754F45"
    colors["rn"] = "#428296"
    colors["fr"] = "#420066"
    colors["ra"] = "#007D00"
    colors["ac"] = "#70ABFA"
    colors["th"] = "#00BAFF"
    colors["pa"] = "#00A1FF"
    colors["u"] = "#008FFF"
    colors["np"] = "#0080FF"
    colors["pu"] = "#006BFF"
    colors["am"] = "#545CF2"
    colors["cm"] = "#785CE3"
    colors["bk"] = "#8A4FE3"
    colors["cf"] = "#A136D4"
    colors["es"] = "#B31FD4"
    colors["fm"] = "#B31FBA"
    colors["md"] = "#B30DA6"
    colors["no"] = "#BD0D87"
    colors["lr"] = "#C70066"
    colors["rf"] = "#CC0059"
    colors["db"] = "#D1004F"
    colors["sg"] = "#D90045"
    colors["bh"] = "#E00038"
    colors["hs"] = "#E6002E"
    colors["mt"] = "#EB0026"
    colors["ds"] = "#ED0023"
    colors["rg"] = "#F00021"
    colors["cn"] = "#E5001E"
    colors["nh"] = "#F4001C"
    colors["fl"] = "#F70019"
    colors["mc"] = "#FA0019"
    colors["lv"] = "#FC0017"
    colors["ts"] = "#FC0014"
    colors["og"] = "#FC000F"
    a_type = a.symbol.lower()
    if a_type not in colors:
        return [1.0, 0, 1.0, 1.0]#Pink unknown
    h = colors[a_type].lstrip('#')
    return list(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)) + [1.0]