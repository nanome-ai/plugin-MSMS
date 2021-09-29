import nanome
from nanome.util import Logs, Process
import tempfile, sys, subprocess, os

class MSMSProcess():
    def __init__(self, plugin):
        self.__plugin = plugin
        self.__process_running = False

    def start_process(self, workspace, probeRadius = 1.4, density = 10.0, hdensity = 3.0):
        #Run MSMS on every complex
        for c in workspace.complexes:
            positions = []
            radii = []
            molecule = c._molecules[c.current_frame]
            for atom in molecule.atoms:
                positions.append(atom.position)
                radii.append(atom.vdw_radius)

            msms_input = tempfile.NamedTemporaryFile(delete=False, suffix='.xyzr')
            msms_output = tempfile.NamedTemporaryFile(delete=False, suffix='.out')
            with open(msms_input.name, 'w') as msms_file:
                for i in range(len(positions)):
                    msms_file.write("{0:.5f} {1:.5f} {2:.5f} {3:.5f}\n".format(-positions[i].x, positions[i].y, positions[i].z, radii[i]))
            exePath = getMSMSExecutable()

            subprocess.run(args=[exePath, "-if ", msms_input.name, "-of ", msms_output.name, "-probe_radius", str(probeRadius), "-density", str(density), "-hdensity", str(hdensity), "-no_area", "-no_rest", "-no_header"])
            if os.path.isfile(msms_output.name + ".vert") and os.path.isfile(msms_output.name + ".face"):
                verts, norms, indices = parseVerticesNormals(msms_output.name + ".vert")
                faces = parseFaces(msms_output.name + ".face")

                aoExePath = getAOEmbreeExecutable()
                colors = []
                if aoExePath != "":
                    colors = runAOEmbree(aoExePath, verts, norms, faces)
                self.__plugin.make_mesh(verts, norms, faces, c.index, colors)

            else:
                Logs.error("Failed to run MSMS")
                self.stop_process()
    
    def stop_process(self):
        if self.__process_running:
            self.__process.stop()
        self.__process_running = False

    def update(self):
        if not self.__process_running:
            Logs.debug('MSMS done')
            self.stop_process()

    def __on_process_error(self, error):
        Logs.warning('Error during MSMS:')
        Logs.warning(error)

def getMSMSExecutable():
    if sys.platform == "linux" or sys.platform == "linux2":
        return "nanome_msms/MSMS_binaries/Linux/msms"
    elif sys.platform == "darwin":
        return "nanome_msms/MSMS_binaries/OSX/msms"
    elif sys.platform == "win32":
        return "nanome_msms/MSMS_binaries/Windows/msms.exe"

def getAOEmbreeExecutable():
    if sys.platform == "win32":
        return "nanome_msms/AO_binaries/Windows/AOEmbree.exe"
    return ""

def parseVerticesNormals(path):
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
            #Invert x for normals => Unity !
            n = [-float(s[3]), float(s[4]), float(s[5])]
            idx = int(s[7]) - 1
            verts += v
            norms += n
            indices.append(idx)
    return (verts, norms, indices)

def parseFaces(path):
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


def runAOEmbree(exePath, verts, norms, faces):
    #Write mesh to OBJ file
    ao_input = tempfile.NamedTemporaryFile(delete=False, suffix='.obj')
    with open(ao_input.name, "w") as f:
        for v in range(int(len(verts) / 3)):
            f.write("v {0:.6f} {1:.6f} {2:.6f}\n".format(verts[v * 3], verts[v * 3 + 1], verts[v * 3 + 2]))
            f.write("vn {0:.6f} {1:.6f} {2:.6f}\n".format(norms[v * 3], norms[v * 3 + 1], norms[v * 3 + 2]))
        for t in range(int(len(faces) / 3)):
            f.write("f {} {} {}\n".format(faces[t * 3] + 1, faces[t * 3 + 1] + 1, faces[t * 3 + 2] + 1))
    #Run AOEmbree
    AOvalues = subprocess.run(args=[exePath, "-i", ao_input.name, "-a", "-s", str(512), "-d", str(50.0)], capture_output=True, text=True)
    vertCol = []
    sAOValues = AOvalues.stdout.split()
    for i in range(int(len(verts) / 3)):
        ao = float(sAOValues[i])
        vertCol += [ao, ao, ao, 1.0]
    return vertCol
