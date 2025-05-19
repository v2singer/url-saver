extends Control

const CONFIG_FILE = "user://server_config.cfg"
var config: ConfigFile
var server_item_scene = preload("res://server_item.tscn")

func _ready():
	config = ConfigFile.new()
	load_config()
	update_server_list()

func load_config():
	var err = config.load(CONFIG_FILE)
	if err != OK:
		# Create default config if it doesn't exist
		config.set_value("servers", "default", "http://localhost:8080")
		config.save(CONFIG_FILE)

func save_config():
	config.save(CONFIG_FILE)

func update_server_list():
	var server_list = $VBoxContainer/ServerList
	for child in server_list.get_children():
		child.queue_free()
	
	# Add default server first
	var default_server = config.get_value("servers", "default", "http://192.168.1.11:8080")
	add_server_item(default_server, true)
	
	# Add other servers
	var servers = config.get_section_keys("servers")
	for server in servers:
		if server != "default":
			var url = config.get_value("servers", server)
			add_server_item(url, false)

func add_server_item(url: String, is_default: bool):
	var item = server_item_scene.instantiate()
	$VBoxContainer/ServerList.add_child(item)
	item.set_url(url)
	item.set_default(is_default)
	if not is_default:
		item.delete_requested.connect(_on_delete_server)

func _on_close_pressed():
	queue_free()

func _on_add_server_pressed():
	var url = $VBoxContainer/AddServerPanel/VBoxContainer/ServerURLLineEdit.text.strip_edges()
	
	if url.is_empty():
		$VBoxContainer/AddServerPanel/VBoxContainer/StatusLabel.text = "Please enter a server URL"
		return
	
	if not url.begins_with("http://") and not url.begins_with("https://"):
		$VBoxContainer/AddServerPanel/VBoxContainer/StatusLabel.text = "URL must start with http:// or https://"
		return
	
	# Generate a unique key for the new server
	var key = "server_" + str(Time.get_unix_time_from_system())
	config.set_value("servers", key, url)
	save_config()
	
	$VBoxContainer/AddServerPanel/VBoxContainer/ServerURLLineEdit.text = ""
	$VBoxContainer/AddServerPanel/VBoxContainer/StatusLabel.text = "Server added successfully"
	update_server_list()

func _on_delete_server(url: String):
	var servers = config.get_section_keys("servers")
	for server in servers:
		if server != "default" and config.get_value("servers", server) == url:
			config.erase_section_key("servers", server)
			break
	save_config()
	update_server_list() 