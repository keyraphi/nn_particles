# nn_particles
A simple script + geometry-nodes for making a "web" from a particle system

## How does it work?
There is a fluid simulation in the scene, which is hold by the _Fluid Domain_. The script connects each particle with its `k` closest neighbours - `k=7` in the demo. The coordinates of the particles are used as vertices whereas the connections to the nearest neigbours are set as edges in the _ParticleMeshObject_.
The _ParticleMeshObject_ has a GeometryNode setup _Geometry Nodes.001_, which converts the edges into curves, shapes them and extracts some information for shading.

In principle this should work for any particle system. The name "Fluid Domain" is hard-coded in the script, but feel free to change that.

## How can I reproduce it?
You first have to bake the fluid simulation in the _Fluid Domain_ object. Then go to the Script tab and run the script. The _ParticleMeshObject_ will then automatically update on every frame change.

## What do I get.
Here is what the demo produces. The look is obviously not tuned

![Particles](/demo_videos/Particles0001-0250.webm)
![KNN Graph](/demo_videos/Edges0001-0250.webm)
![Geometry Nodes Result](/demo_videos/GeoNodes_eevee0001-0250.webm)
