Godot import and usage instructions

Files provided:
- player.gd : CharacterBody3D movement script

Workflow:
1. Run the Blender script to generate a GLB: tools\\blender\\create_earth.py
   Example (Windows):
   "F:\\Blender 5.1\\blender.exe" --background --python tools\\blender\\create_earth.py
   This will export exports/earth.glb inside the tools/blender folder.

2. Open or create a Godot 4 project and copy the exported earth.glb into the project folder (e.g., res://models/earth.glb).

3. Create a new scene (3D) and:
   - Add a Node3D as root.
   - Instance the imported earth.glb. Position at origin and scale as needed.
   - Add a CharacterBody3D node as the player. Attach the provided player.gd script.
   - Add a Camera3D as a child of the Player (name it Camera3D).

4. Configure InputMap: move_forward/backward/left/right and jump.

Notes:
- For spherical gravity (player walks around planet) request "planet gravity" behavior.
