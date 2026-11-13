# Godot 4 CharacterBody3D player movement script (player.gd)
# Attach to a CharacterBody3D node. Add a Camera3D as a child (named "Camera3D").

extends CharacterBody3D

@export var speed: float = 5.0
@export var jump_velocity: float = 4.5
var gravity := ProjectSettings.get_setting("physics/3d/default_gravity")

func _physics_process(delta: float) -> void:
    var input_dir := Vector3.ZERO
    input_dir.x = Input.get_action_strength("move_right") - Input.get_action_strength("move_left")
    input_dir.z = Input.get_action_strength("move_backward") - Input.get_action_strength("move_forward")

    if input_dir.length() > 0.001:
        input_dir = input_dir.normalized()
        var cam := get_node_or_null("Camera3D")
        if cam:
            var basis := cam.global_transform.basis
            var dir_world := (basis.x * input_dir.x) + (basis.z * input_dir.z)
            dir_world.y = 0
            dir_world = dir_world.normalized()
            velocity.x = dir_world.x * speed
            velocity.z = dir_world.z * speed
        else:
            velocity.x = input_dir.x * speed
            velocity.z = input_dir.z * speed
    else:
        velocity.x = lerp(velocity.x, 0, 0.15)
        velocity.z = lerp(velocity.z, 0, 0.15)

    if not is_on_floor():
        velocity.y -= gravity * delta

    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_velocity

    velocity = move_and_slide()
