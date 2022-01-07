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


class NN_GRAPH_OT_dummy_operator(bpy.types.Operator):
    bl_idname = "nn_graph.dummy_operator"
    bl_label = "Dummy Operator"
    bl_description = "This operator tries to use annoy."
    bl_options = {"REGISTER"}

    def execute(self, context):
        # "angular", "euclidean", "manhattan", "hamming", or "dot"
        nn_idx = annoy.AnnoyIndex(3, "euclidean")
        print(nn_idx)
        return {"FINISHED"}


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

        layout.operator(NN_GRAPH_OT_dummy_operator.bl_idname)

        for i in range(4):
            layout.operator_menu_enum(
                NN_GRAPH_OT_dummy_operator.bl_idname,
                property=f"Test{i}",
                text="Hello World{i}",
                text_ctxt="",
                translate=False,
                icon="CONSOLE",
            )


classes = (NN_GRAPH_OT_dummy_operator, NN_GRAPH_PT_panel)


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


preference_classes = (
    NN_GRAPH_PT_warning_panel,
    NN_GRAPH_OT_install_dependencies,
    NN_GRAPH_preferences,
)


def register():
    global dependencies_installed
    dependencies_installed = False

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
    for cls in preference_classes:
        bpy.utils.unregister_class(cls)

    if dependencies_installed:
        for cls in classes:
            bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

