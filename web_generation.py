import bpy
import bmesh
import numpy as np
import time


def knn(points: np.ndarray, k: int=5)-> np.ndarray:
    """A naive but simple K-Nearest-Neigbours graph generation algorithm.
    
    Note: This has O(n^2) complexity for both memory and computational costs.
    Could be replace this with a more efficient implementation.
    This would however add third party dependencies (e.g. pyflann).
    For this scene this function is NOT the bottleneck,
    so I didn't bother investing in it.
    
    Args:
        points: 3d point cloud of shape [N, 3].
        k: Number of nearest neighbors to look for.
    Returns:
        KNN-Graph: List of the indices of the k nearest neigbours of each point.
        Point itself is always included! Shape [N, k]
    """

    other_points = points.reshape([1, -1, 3])
    points = points.reshape([-1, 1, 3])
    differences = points - other_points
    distances = np.sqrt(np.einsum("nmd,nmd->nm", differences, differences))
    sorted_idxs = np.argsort(distances, axis=1)
    return sorted_idxs[:, :k]


def particles_to_web(k: int=7):
    """ Connects the nearest neigbours of all particles in the "Liquid Domain" object
    with an edge. The GeometryNodes of the ParticleMeshObject automatically creates a mesh from that.
    
    Args:
        k: The number of particles with which each particle is going to be connected.
    
    Notes:
        This is a proove of concept implementation
        This function can be registered as frame_change_pre handler to update the mesh every frame.
        Most work is done by the geometry nodes, which convert the web into a mesh. This takes way longer than building the KNN graph.
    """
    t0 = time.time()
    print("Extracting particle positions")
    obj = bpy.data.objects["Liquid Domain"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj = obj.evaluated_get(depsgraph)
    particle_system = obj.particle_systems.active
    
    particles = np.array([p.location for p in particle_system.particles])
    print("Elapsed time: {} sec".format(time.time() - t0))
    t0 = time.time()
    
    print("Computing KNN")
    knn_idxs = knn(particles, k=k)
    print("Elapsed time: {} sec".format(time.time() - t0))
    t0 = time.time()
    
    print("Creating / updating mesh")
    # manipulate mesh with vertices at particle positions 
    bm = bmesh.new()
    obj = bpy.data.objects["ParticleMeshObject"]  
    # move the particles to the new positions and get rid of the old edges
    mesh = obj.data
    bm.from_mesh(mesh)
    # particle count could have changed => rebuild the mesh from scratch
    if len(particles) != len(bm.verts):
        context="VERTS"  # remove all vertices
        geom=bm.verts
    else:
        context = "EDGES_FACES"  # keep vertices, remove edges
        geom=bm.edges
    bmesh.ops.delete(bm, geom=geom, context=context)
    if context != "EDGES_FACES":
        for position in particles:
            bm.verts.new(position)
    else:  # just move existing vertices
        for vertice, position in zip(bm.verts, particles):
            vertice.co.xyz = position
    
    # add new edges based on NN-graph
    bm.verts.ensure_lookup_table()
    existing_edges = set()  # prevents adding same edges in other direction
    for edges in knn_idxs:
        start = edges[0]
        for end in edges[1:]:
            if (end, start) not in existing_edges:
                bm.edges.new([bm.verts[start], bm.verts[end]])
                existing_edges.add((start, end))
    # update the mesh
    bm.to_mesh(mesh)
    mesh.update()
    bm.free()
    
    print("Elapsed time: {} sec".format(time.time() - t0))
    print("done")


# This is how you add the function as frame_change_pre handler:
def my_handler(scene):  
    particles_to_web()

def register():
    bpy.app.handlers.frame_change_pre.append(my_handler)

def unregister():
    bpy.app.handlers.frame_change_pre.remove(my_handler)

# call the function once when the script is called
particles_to_web()

# remove old handlers
for handler in bpy.app.handlers.frame_change_pre:
    bpy.app.handlers.frame_change_pre.remove(bpy.app.handlers.frame_change_pre[-1])

# register handler
register()