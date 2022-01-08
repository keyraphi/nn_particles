# -*- coding: utf-8 -*-

bl_info = {
    "name": "Nearest Neighbour Graph Mesh from Particles",
    "author": "Raphael Braun",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Particle-NN",
    "description": "Add-on for generating a nearest neighbour graph mesh from a particle system.",
    "warning": "Works best with installation of additional dependencies",
    "wiki_url": "https://github.com/keyraphi/nn_particles/wiki",
    "tracker_url": "https://github.com/keyraphi/nn_particles/issues",
    "support": "COMMUNITY",
    "category": "3D View",
}


import bpy
import os
import sys
import numpy as np
import bmesh
import subprocess
import importlib
from collections import namedtuple
from typing import Optional


# Dependency installation handling from:
# https://github.com/robertguetzkow/blender-python-examples/tree/master/add_ons/install_dependencies

# Named tuple for dependencies specification
Dependency = namedtuple("Dependency", ["module", "package", "name", "purpose"])


# For reasonable performance we need a fast approximate knn library Lets use
# "annoy", seems good enough and easy to install
dependencies = (
    Dependency(
        module="annoy",
        package=None,
        name=None,
        purpose="Fast Approximate Nearest neigbour graph generation.",
    ),
)
dependencies_installed = False


def import_module(
    module_name: str, global_name: Optional[str] = None, reload: bool = True
):
    """
    Import a module.
    Args:
        module_name: Module to import.
        global_name:
            (Optional) Name under which the module is imported. If None the
            module_name will be used. This allows to import under a different
            name with the same effect as e.g. "import numpy as np" where "np"
            is the global_name under which the module can be accessed.
        reload: Whether or not to re-import a module if it is already in the scope.
    "
    raises: ImportError and ModuleNotFoundError
    """
    if global_name is None:
        global_name = module_name

    if global_name in globals() and reload:
        importlib.reload(globals()[global_name])
    else:
        # Attempt to import the module and assign it to globals dictionary. This allow to access the module under
        # the given name, just like the regular import would.
        globals()[global_name] = importlib.import_module(module_name)


def install_pip():
    """
    Installs pip if not already present. Please note that ensurepip.bootstrap() also calls pip, which adds the
    environment variable PIP_REQ_TRACKER. After ensurepip.bootstrap() finishes execution, the directory doesn't exist
    anymore. However, when subprocess is used to call pip, in order to install a package, the environment variables
    still contain PIP_REQ_TRACKER with the now nonexistent path. This is a problem since pip checks if PIP_REQ_TRACKER
    is set and if it is, attempts to use it as temp directory. This would result in an error because the
    directory can't be found. Therefore, PIP_REQ_TRACKER needs to be removed from environment variables.
    """

    try:
        # Check if pip is already installed
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True)
    except subprocess.CalledProcessError:
        import ensurepip

        ensurepip.bootstrap()
        os.environ.pop("PIP_REQ_TRACKER", None)


def install_and_import_module(
    module_name: str,
    package_name: Optional[str] = None,
    global_name: Optional[str] = None,
):
    """
    Installs the package through pip and attempts to import the installed module.
        module_name: Module to import.
        package_name:
            (Optional) Name of the package that needs to be installed. If None
            it is assumed to be equal to the module_name.
        global_name:
            (Optional) Name under which the module is imported. If None the
            module_name will be used. This allows to import under a different
            name with the same effect as e.g. "import numpy as np" where "np"
            is the global_name under which the module can be accessed.

    raises: subprocess.CalledProcessError and ImportError
    """
    if package_name is None:
        package_name = module_name

    if global_name is None:
        global_name = module_name

    # Blender disables the loading of user site-packages by default. However, pip will still check them to determine
    # if a dependency is already installed. This can cause problems if the packages is installed in the user
    # site-packages and pip deems the requirement satisfied, but Blender cannot import the package from the user
    # site-packages. Hence, the environment variable PYTHONNOUSERSITE is set to disallow pip from checking the user
    # site-packages. If the package is not already installed for Blender's Python interpreter, it will then try to.
    # The paths used by pip can be checked with `subprocess.run([sys.executable, "-m", "site"], check=True)`

    # Create a copy of the environment variables and modify them for the subprocess call
    environ_copy = dict(os.environ)

    environ_copy["PYTHONNOUSERSITE"] = "1"

    subprocess.run(
        [sys.executable, "-m", "pip", "install", package_name],
        check=True,
        env=environ_copy,
    )

    # The installation succeeded, attempt to import the module again
    import_module(module_name, global_name)


class NN_GRAPH_OT_web_operator(bpy.types.Operator):
    bl_idname = "nn_graph.web_operator"
    bl_label = "Web Operator"
    bl_description = "Generates a web from the active particle system of the selected emitter."
    bl_options = {"REGISTER"}

    def execute(self, context):
        emitter = context.scene.particle_nn_graph_emitter
        particle_coordinates = self.get_particle_coordinates(emitter, context)
        knn = self.compute_knn(
            particle_coordinates,
            context.scene.particle_nn_graph_distance,
            context.scene.particle_nn_graph_connections + 1,
        )
        web_name = context.scene.particle_nn_graph_emitter.name + "_web"
        # web (edges only)
        web = self.generate_web(particle_coordinates, knn, web_name, context)
        if context.scene.particle_nn_graph_add_geometry_nodes:
            # convert to real mesh
            web = self.add_geometry_nodes(web, context)
        return {"FINISHED"}

    def add_geometry_nodes(self, obj, context):
        """Makes sure that the web obj has a geometry-node setup.
        This will only add a geometry node setup if the object does not have one yet.
        Args:
            obj: The web object to which the geometry nodes are added.
            context: The current context.
        Returns:
            The web object.
        """
        if self.has_geometry_nodes(obj):
            return obj
        # create Geometry Node modifier
        mod = obj.modifiers.new("GeometryNodes_web", 'NODES') 
        mod.name="GeometryNodes_web"
        node_group = mod.node_group
        node_group.name = "GeometryNodes_web"
        nodes = node_group.nodes
        # convert web to curve
        # TODO: This does not work :/
        mesh_to_curve = nodes.new("MESH_TO_CURVE")
        curve_to_curve = nodes.new("CURVE_TO_MESH")
        print("all nodes:", [n for n in nodes])
        return obj

    def has_geometry_nodes(self, obj):
        """Checks if a given object uses geometry node modifiers"""
        for mod in obj.modifiers:
            if mod.type == "NODES":
                return True
        return False

    def generate_web(
        self, points: np.ndarray, knn: np.ndarray, obj_name: str, context
    ):
        """Generate (or update existing) web object from given knn.
        Args:
            points: 3D coordinates of the particles. Shape [N, 3]
            knn: The knn index structure. Shape [N, k]
            obj_name: The name of the generated/updated object.
            context: current blender context.

        Returns:
            The generated object
        """
        # use bmesh to create web
        bm = bmesh.new()
        if obj_name in bpy.data.objects:
            obj = bpy.data.objects[obj_name]
            mesh = obj.data
            bm.from_mesh(mesh)
        else:
            mesh = bpy.data.meshes.new("mesh")
            obj = bpy.data.objects.new(obj_name, mesh)
            context.collection.objects.link(obj)
        # Check if vertex count is already correct
        if len(points) != len(bm.verts):
            context = "VERTS"
            geom = bm.verts
        else:
            context = "EDGES_FACES"  # keep vertices
            geom = bm.edges
        bmesh.ops.delete(bm, geom=geom, context=context)
        if context != "EDGES_FACES":
            # create the new vertices
            for point in points:
                bm.verts.new(point)
        else:
            # move existing vertices
            for vertex, point in zip(bm.verts, points):
                vertex.co.xyz = point

        # add edges
        bm.verts.ensure_lookup_table()
        existing_edges = set()  # do not add edges in both directions
        for edge in knn:
            start = edge[0]
            for end in edge[1:]:
                if (end, start) not in existing_edges and (
                    start,
                    end,
                ) not in existing_edges:
                    bm.edges.new([bm.verts[start], bm.verts[end]])
                    existing_edges.add((start, end))
        # update the mesh
        bm.to_mesh(mesh)
        mesh.update()
        bm.free()
        return obj

    def get_particle_coordinates(self, emitter, context) -> np.ndarray:
        """Gets the 3d-coordinates of the particles from the given emitter.
        Returns array of shape [N, 3], where N is the number of particles.
        """
        depsgraph = context.evaluated_depsgraph_get()
        emitter = emitter.evaluated_get(depsgraph)
        particle_system = emitter.particle_systems.active
        particles = np.array([p.location for p in particle_system.particles])
        return particles

    def compute_knn(
        self, points: np.ndarray, distance_measure: str, k: int
    ) -> np.ndarray:
        """Generates a KNN for the given points.
        Args:
            points:
                Array of 3d points. Shape [N, 3].
            distance_measure:
                The distance measure. One of ['angular', 'euclidean', 'manhattan', 'dot']
            k:
                Number of nearest neigbours to find (point itself included).
        Returns:
            The k nearest neigbours of each point. Shape [N, K], type: int.
        """
        if dependencies_installed:
            return self._annoy_knn(points, distance_measure, k)
        else:
            return self._numpy_knn(points, distance_measure, k)

    def _annoy_knn(self, points: np.ndarray, distance_measure: str, k: int):
        """Fast knn search using annoy."""
        nn_idx = annoy.AnnoyIndex(3, distance_measure)
        # build index structure
        for i, point in enumerate(points):
            nn_idx.add_item(i, point)
        nn_idx.build(10)
        knn = np.array([nn_idx.get_nns_by_item(i, k) for i in range(len(points))])
        return knn

    def _numpy_knn(self, points: np.ndarray, distance_measure: str, k: int):
        """Slow knn search using numpy. This will not scale beyond 1000 points"""
        other_points = points.reshape([1, -1, 3])
        points = points.reshape([-1, 1, 3])
        differences = points - other_points
        if distance_measure == "euclidean":
            distances = np.sqrt(np.einsum("nmd,nmd->nm", differences, differences))
        elif distance_measure == "manhattan":
            distances = np.sum(np.abs(differences), axis=2)
        elif distance_measure == dot:
            distances = np.einsum("nmd,nmd->nm", differences, differences)
        else:
            assert distance_measure == "angular"
            points_len = np.linalg.norm(points, ord=2, axis=2, keepdims=True)
            other_points_len = np.linalg.norm(
                other_points, ord=2, axis=2, keepdims=True
            )
            norm_differences = points / points_len - other_points / other_points_len
            distances = np.sqrt(
                np.einsum("nmd,nmd->nm", norm_differences, norm_differences)
            )

        sorted_idx = np.argsort(distances, axis=1)
        return sorted_idx[:, :k]


class NN_GRAPH_PT_panel(bpy.types.Panel):
    bl_label = "Particle NN Graph"
    bl_category = "Particle NN Graph"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        if not dependencies_installed:
            lines = [
                f"Install dependencies",
                f"for better performance.",
                f"-> Addon preferences",
            ]
            box = layout.box()
            for line in lines:
                box.label(text=line)
        else:
            box = layout.box()
            box.label(text="All dependencies installed.")

        row = layout.row()
        row.prop_search(
            context.scene,
            "particle_nn_graph_emitter",
            context.scene,
            "objects",
            text="Emitter",
        )
        row = layout.row()
        row.prop(context.scene, "particle_nn_graph_distance")
        row = layout.row()
        row.prop(context.scene, "particle_nn_graph_connections")
        row = layout.row()
        row.prop(context.scene, "particle_nn_graph_add_geometry_nodes")
        row = layout.row()
        row.operator(NN_GRAPH_OT_web_operator.bl_idname)


class NN_GRAPH_PT_warning_panel(bpy.types.Panel):
    bl_label = "Performance Warning"
    bl_category = "Particle NN Graph"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(self, context):
        return not dependencies_installed

    def draw(self, context):
        layout = self.layout

        lines = [
            f"For optimal performance please install dependencies in the preferences:",
            f"1. Open the preferences (Edit > Preferences > Add-ons).",
            f"2. Search for the \"{bl_info.get('name')}\" add-on.",
            f"3. Open the details section of the add-on.",
            f'4. Click on the "{NN_GRAPH_OT_install_dependencies.bl_label}" button.',
        ]

        for line in lines:
            layout.label(text=line)


class NN_GRAPH_OT_install_dependencies(bpy.types.Operator):
    bl_idname = "nn_graph.install_dependencies"
    bl_label = "Install dependencies"
    bl_description = (
        "Downloads and installs the required python packages for this add-on. "
        "Internet connection is required. Blender may have to be started with "
        "elevated permissions in order to install the package."
    )
    bl_options = {"REGISTER", "INTERNAL"}

    @classmethod
    def poll(self, context):
        # Deactivate when dependencies have been installed
        return not dependencies_installed

    def execute(self, context):
        try:
            install_pip()
            for dependency in dependencies:
                install_and_import_module(
                    module_name=dependency.module,
                    package_name=dependency.package,
                    global_name=dependency.name,
                )
        except (subprocess.CalledProcessError, ImportError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        global dependencies_installed
        dependencies_installed = True

        # Register the panels, operators, etc. since dependencies are installed
        for cls in classes:
            bpy.utils.register_class(cls)

        return {"FINISHED"}


class NN_GRAPH_preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        lines = [
            "Building the Nearest-Neigbour-Graph without dedicated library",
            "is possible, however it will not scale well beyond ~1000 particles.",
            "If you want to use more particles you have to install further dependencies:",
            *[f'Dependency: "{dep.module}", for {dep.purpose}' for dep in dependencies],
            "This will allow you to build NN-Graphs with millions of particles.",
        ]
        for line in lines:
            layout.label(text=line)
        layout.operator(NN_GRAPH_OT_install_dependencies.bl_idname, icon="CONSOLE")


# Keep track of what to register
classes = (
    NN_GRAPH_OT_web_operator,
    NN_GRAPH_PT_panel,
)

preference_classes = (
    NN_GRAPH_PT_warning_panel,
    NN_GRAPH_OT_install_dependencies,
    NN_GRAPH_preferences,
)

# keep track of registered properties
possible_distances = [
    ("angular", "Angular", "Euclidean distance of normalized vectors", 1),
    ("euclidean", "Euclidean", "Euclidean distance (root squared error)", 2),
    ("manhattan", "Manhattan", "Manhattan distance (absolute error)", 3),
    ("dot", "Dot", "Dot product distance (cosine error)", 4),
]
distance_property = bpy.props.EnumProperty(
    items=possible_distances, name="Distance", default=2
)


def emitter_poll(self, obj):
    """Checks if an object contains a particle system"""
    for modifier in obj.modifiers:
        if modifier.type == "PARTICLE_SYSTEM":
            return True
    return False


properties = [
    ("particle_nn_graph_distance", distance_property),
    (
        "particle_nn_graph_emitter",
        bpy.props.PointerProperty(type=bpy.types.Object, poll=emitter_poll),
    ),
    (
        "particle_nn_graph_connections",
        bpy.props.IntProperty(name="Connections", default=5, min=1, soft_max=30),
    ),
    (
        "particle_nn_graph_add_geometry_nodes",
        bpy.props.BoolProperty(name="Geometry Nodes", default=False),
    ),
]


def register():
    global dependencies_installed
    dependencies_installed = False

    for (prop_name, prop_value) in properties:
        setattr(bpy.types.Scene, prop_name, prop_value)

    for cls in preference_classes:
        bpy.utils.register_class(cls)

    try:
        for dependency in dependencies:
            import_module(module_name=dependency.module, global_name=dependency.name)
        dependencies_installed = True
    except ModuleNotFoundError:
        # Don't register other panels, operators etc.
        return

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for (prop_name, _) in properties:
        delattr(bpy.types.Scene, prop_name)

    for cls in preference_classes:
        bpy.utils.unregister_class(cls)

    if dependencies_installed:
        for cls in classes:
            bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
