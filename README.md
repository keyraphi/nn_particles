# Web from Particles
A simple script + geometry-nodes for making a "web" from a particle system. This could be used to generate some cool effects in Blender.
The inspiration came from the tutorial [Recreating Hollywood VFX in Blender](https://www.youtube.com/watch?v=C5UmtZRqy5Y&lc=UgzXTcDJOjjcZbc9ued4AaABAg.9WXV2WZ8fH19Wj2qDGdDHg) by [Bad Normals](https://www.youtube.com/c/BadNormals/videos).

## How does it work?
There is a FLIP fluid simulation in the scene, which is hold by the _Fluid Domain_. The script connects each particle with its `k` closest neighbours - `k=7` in the demo. The coordinates of the particles are used as vertices whereas the connections to the nearest neigbours are set as edges in the _ParticleMeshObject_.
The _ParticleMeshObject_ has a GeometryNode setup _Geometry Nodes.001_, which converts the edges into curves, shapes them and extracts some information for shading.

In principle this should work for any particle system. The name "Fluid Domain" is hard-coded in the script, but feel free to change that.

## How can I reproduce it?
You first have to bake the fluid simulation in the _Fluid Domain_ object. Then go to the Script tab and run the script. The _ParticleMeshObject_ will then automatically update on every frame change.

## What do I get.
Here is what the demo produces. Note this is just a proove of concept.

The particles of the fluid simulation

https://user-images.githubusercontent.com/7500902/147886304-3a88ce0b-3189-4bbc-b416-07b7078507b5.mp4

The connecting edges (this is what the script creates)

https://user-images.githubusercontent.com/7500902/147887143-e4ae5261-55b4-45f0-a4cc-df097b97b752.mp4

The result from the geometry nodes and some fancy lights.

https://user-images.githubusercontent.com/7500902/147886768-df1af49c-5d9a-4219-9add-7b180a389003.mp4


## Will it scale
The code takes about 40ms to run on my 10 year old PC for the example above. With geometry nodes I get about 6 fps. This will however not scale well.
The KNN-algorithm is naive and has a quadratic complexity. It could be replaced with something like [flann](https://github.com/flann-lib/flann) if hundred of thousands of points need to be connected quickly.
Here is a video with some more particles (4sec per frame): [more points](https://youtu.be/IgjyHYfrs-I).
On my machine ~11k particles are the limit of what is possible (15sec per frame): [11k particles](https://youtu.be/7T_UaafsotM).

## Limitations and Future Work
As mentioned before the NN-Graph generation has a quadratic computational and memory complexity, so it will get slow really quicly if many points are used.
Also the web mesh is re-generated in every frame. Cycles therefore does not treat it as a moving/deforming object, instead as a new static object in every frame. This essentially makes rendered motion blur impossible. It might be possible to add vector motion blur via code (not sure about that), but that is currently also msising.
This demo is not very usefull as it is. I might convert it into a plugin if I find the time. 
