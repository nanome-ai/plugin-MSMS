import json
import os
import tempfile
import sys
from random import randint

import nanome
from nanome import shapes
from nanome.util import enums, Color, Logs, Process

BASE_DIR = os.path.join(os.path.dirname(__file__))
MSMS_PATH = None
AO_PATH = None

MSMS_PROBE_RADIUS = 1.5
MSMS_DENSITY = 10.0
MSMS_HDENSITY_SM = 3.0
MSMS_HDENSITY_LG = 1.0
AO_STEPS = 512
AO_MAX_DIST = 50.0

with open(os.path.join(BASE_DIR, 'assets/colors.json')) as f:
    COLOR_BY_ELEMENT = json.load(f)

COLOR_BY_OPTIONS = [
    ('All', enums.ColorScheme.Monochrome),
    ('Chain', enums.ColorScheme.Chain),
    ('Residue', enums.ColorScheme.Residue),
    ('Element', enums.ColorScheme.Element),
    ('Secondary Structure', enums.ColorScheme.SecondaryStructure),
]

COLOR_PRESETS = [
    ('Custom', '#808080'),
    ('Red', '#ff0000'),
    ('Orange', '#ff8000'),
    ('Yellow', '#ffff00'),
    ('Yellow Green', '#80ff00'),
    ('Green', '#00ff00'),
    ('Aqua Green', '#00ff80'),
    ('Cyan', '#00ffff'),
    ('Azure', '#0080ff'),
    ('Blue', '#0000ff'),
    ('Violet', '#8000ff'),
    ('Magenta', '#ff00ff'),
    ('Pink', '#ff0080'),
    ('White', '#ffffff'),
    ('Gray', '#808080'),
    ('Black', '#000000'),
]

if sys.platform == 'linux':
    AO_PATH = os.path.join(BASE_DIR, 'bin/linux/AOEmbree')
    MSMS_PATH = os.path.join(BASE_DIR, 'bin/linux/msms')
    os.environ['LD_LIBRARY_PATH'] = os.path.join(BASE_DIR, 'bin/linux')
elif sys.platform == 'darwin':
    MSMS_PATH = os.path.join(BASE_DIR, 'bin/darwin/msms')
elif sys.platform == 'win32':
    AO_PATH = os.path.join(BASE_DIR, 'bin/win32/AOEmbree.exe')
    MSMS_PATH = os.path.join(BASE_DIR, 'bin/win32/msms.exe')


class MSMSInstance:
    def __init__(self, name: str, index: int, atoms: 'list[nanome.structure.Atom]'):
        self.name = name
        self.index = index
        self.atoms = atoms

        self.color_by: enums.ColorScheme = enums.ColorScheme.Chain
        self.color: Color = Color.from_hex(COLOR_PRESETS[randint(1, 12)][1])
        self.visible = True

        self.vertices: list[float] = []
        self.normals: list[float] = []
        self.triangles: list[int] = []
        self.colors: list[float] = []
        self.indices: list[int] = []
        self.ao: list[float] = []
        self.mesh = shapes.Mesh()

    @property
    def num_vertices(self):
        return len(self.vertices) // 3

    @property
    def hex_color(self):
        # output only rgb values
        return self.color.hex[:-2]

    @hex_color.setter
    def hex_color(self, value):
        color = Color.from_hex(value)
        color.a = self.color.a
        self.color = color

    async def generate(self, by_chain=False, ao=True):
        if by_chain:
            await self.compute_msms_by_chain()
        else:
            await self.compute_msms(self.atoms)
        if ao and AO_PATH:
            await self.compute_ao()
        await self.create_mesh()

    def destroy(self):
        self.mesh.destroy()

    async def compute_msms_by_chain(self):
        atoms_by_chain = [[]]
        current_chain = self.atoms[0].chain.name
        for atom in self.atoms:
            if atom.chain.name != current_chain:
                current_chain = atom.chain.name
                atoms_by_chain.append([])
            atoms_by_chain[-1].append(atom)

        num_atoms = 0
        for atoms in atoms_by_chain:
            await self.compute_msms(atoms, num_atoms)
            num_atoms += len(atoms)

    async def compute_msms(self, atoms: 'list[nanome.structure.Atom]', index_offset=0):
        temp_dir = tempfile.TemporaryDirectory()
        msms_input = tempfile.NamedTemporaryFile(dir=temp_dir.name, suffix='.xyzr', delete=False)
        msms_output = tempfile.NamedTemporaryFile(dir=temp_dir.name, suffix='.out', delete=False)
        hdensity = MSMS_HDENSITY_SM if len(atoms) < 20000 else MSMS_HDENSITY_LG

        with open(msms_input.name, 'w') as f:
            for atom in atoms:
                x, y, z = atom.position
                # replace unknown atoms with carbon
                r = 1.7 if atom.vdw_radius < 0.0001 else atom.vdw_radius
                f.write(f'{x:.5f} {y:.5f} {z:.5f} {r:.5f}\n')

        p = Process(MSMS_PATH, label=f'MSMS {len(atoms)} atoms', output_text=True, timeout=0)
        p.on_error = Logs.warning
        p.args = [
            '-if ', msms_input.name,
            '-of ', msms_output.name,
            '-probe_radius', str(MSMS_PROBE_RADIUS),
            '-density', str(MSMS_DENSITY),
            '-hdensity', str(hdensity),
            '-no_area', '-no_header',
            '-all_components'
        ]
        exit_code = await p.start()
        if exit_code != 0 or not os.path.isfile(msms_output.name + '.vert'):
            raise Exception('Failed to run MSMS')

        file_index = 0
        while True:
            name = msms_output.name
            if file_index > 0:
                name += f'_{file_index}'
            if not os.path.isfile(name + '.vert'):
                break
            vertex_offset = self.num_vertices
            with open(name + '.vert', 'r') as f:
                for l in f.readlines():
                    if l.startswith('#'):
                        continue
                    s = l.split()
                    self.vertices += map(float, s[0:3])
                    self.normals += map(float, s[3:6])
                    self.indices.append(int(s[7]) - 1 + index_offset)
            with open(name + '.face', 'r') as f:
                for l in f.readlines():
                    if l.startswith('#'):
                        continue
                    s = l.split()
                    self.triangles += [int(x) - 1 + vertex_offset for x in s[0:3]]
            file_index += 1

    async def compute_ao(self):
        temp_dir = tempfile.TemporaryDirectory()
        ao_input = tempfile.NamedTemporaryFile(dir=temp_dir.name, suffix='.obj', delete=False)
        ao_output = tempfile.NamedTemporaryFile(dir=temp_dir.name, suffix='.out', delete=False)

        with open(ao_input.name, 'w') as f:
            for v in range(self.num_vertices):
                i = v * 3
                f.write(f'v {self.vertices[i]:.6f} {self.vertices[i + 1]:.6f} {self.vertices[i + 2]:.6f}\n')
                f.write(f'vn {self.normals[i]:.6f} {self.normals[i + 1]:.6f} {self.normals[i + 2]:.6f}\n')
            for t in range(len(self.triangles) // 3):
                i = t * 3
                f.write(f'f {self.triangles[i] + 1} {self.triangles[i + 1] + 1} {self.triangles[i + 2] + 1}\n')

        p = Process(AO_PATH, label=f'AOEmbree {self.num_vertices} vertices', output_text=True, timeout=0)
        p.on_error = Logs.warning
        p.args = [
            '-a', '-n',
            '-i', ao_input.name,
            '-o', ao_output.name,
            '-s', str(AO_STEPS),
            '-d', str(AO_MAX_DIST)
        ]
        exit_code = await p.start()

        if exit_code != 0 or not os.path.isfile(ao_output.name):
            Logs.warning('Failed to run AOEmbree')
            return

        with open(ao_output.name, 'r') as f:
            data = ' '.join(f.readlines()).split()
            if len(data) != self.num_vertices:
                Logs.warning(f'AOEmbree output has wrong number of vertices, expected {self.num_vertices}, got {len(data)}')
                return
            self.ao = list(map(float, data))

    async def create_mesh(self):
        anchor: shapes.Anchor = self.mesh.anchors[0]
        anchor.anchor_type = enums.ShapeAnchorType.Complex
        anchor.target = self.index

        self.mesh.vertices = self.vertices
        self.mesh.normals = self.normals
        self.mesh.triangles = self.triangles
        self.mesh.colors = [1, 1, 1, 1] * self.num_vertices
        self.mesh.color = Color.White()
        self.mesh.unlit = len(self.ao) > 0
        await self.apply_color()

    def toggle_visible(self, show=None):
        if show == self.visible:
            return
        self.visible = not self.visible if show is None else show
        self.mesh.color.a = self.color.a if self.visible else 0
        self.mesh.upload()

    async def apply_color(self):
        if self.color_by == enums.ColorScheme.Monochrome:
            r, g, b = (c / 255 for c in self.color.rgb)
            self.colors = [r, g, b, 1] * self.num_vertices
        elif self.color_by == enums.ColorScheme.Chain:
            self.apply_color_by_chain()
        elif self.color_by == enums.ColorScheme.Residue:
            self.apply_color_by_residue()
        elif self.color_by == enums.ColorScheme.Element:
            self.apply_color_by_element()
        elif self.color_by == enums.ColorScheme.SecondaryStructure:
            self.apply_color_by_secondary_structure()

        self.mesh.color.a = self.color.a
        await self.apply_color_to_mesh()

    def apply_color_by_chain(self):
        chain_names = sorted(set(atom.chain.name for atom in self.atoms))
        color_per_atom = []
        for atom in self.atoms:
            i = chain_names.index(atom.chain.name)
            t = i / len(chain_names)
            r, g, b = (c / 255 for c in self.color.rgb)
            r, g, b = (c + (1 - c) * t for c in (r, g, b))
            color_per_atom.append([r, g, b, 1])
        self.apply_color_per_atom(color_per_atom)

    def apply_color_by_residue(self):
        residue_names = sorted(set(atom.residue.name for atom in self.atoms))
        color_per_atom = []
        for atom in self.atoms:
            i = residue_names.index(atom.residue.name)
            t = i / len(residue_names)
            r, g, b = (c / 255 for c in self.color.rgb)
            r, g, b = (c + (1 - c) * t for c in (r, g, b))
            color_per_atom.append([r, g, b, 1])
        self.apply_color_per_atom(color_per_atom)

    def apply_color_by_element(self):
        color_per_atom = []
        for atom in self.atoms:
            hex = COLOR_BY_ELEMENT.get(atom.symbol.lower(), '#ff00ff')
            r, g, b = (c / 255 for c in Color.from_hex(hex).rgb)
            color_per_atom.append([r, g, b, 1])
        self.apply_color_per_atom(color_per_atom)

    def apply_color_by_secondary_structure(self):
        unknown_color = [0.5, 0.5, 0.5, 1.0]
        coil_color = [0.0784, 1.0, 0.0784, 1.0]
        sheet_color = [0.941, 0.941, 0, 1.0]
        helix_color = [1.0, 0.0784, 0.0784, 1.0]
        colors = [unknown_color, coil_color, sheet_color, helix_color]

        color_per_atom = []
        for atom in self.atoms:
            ss = int(atom.residue.secondary_structure)
            color_per_atom.append(colors[ss])
        self.apply_color_per_atom(color_per_atom)

    def apply_color_per_atom(self, color_per_atom):
        self.colors = []
        for i in self.indices:
            self.colors += color_per_atom[i]

    async def apply_color_to_mesh(self):
        has_ao = len(self.ao) > 0
        for i in range(self.num_vertices):
            j = i * 4
            r, g, b = self.colors[j:j + 3]
            ao = self.ao[i] if has_ao else 1
            self.mesh.colors[j:j + 3] = [r * ao, g * ao, b * ao]

        if self.visible:
            await self.mesh.upload()
