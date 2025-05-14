extends Control

const CONFIG_FILE = "user://server_config.cfg"
const API_HISTORY = "/extension/urls"
const API_SAVE = "/extension/urls"

var http_request: HTTPRequest
var history_request: HTTPRequest
var url_item_scene = preload("res://url_item.tscn")
var config_panel_scene = preload("res://config_panel.tscn")
var config: ConfigFile
var current_server_index = 0
var server_urls = []

func _ready():
	# 等待一帧以确保所有节点都已准备好
	await get_tree().process_frame
	
	http_request = HTTPRequest.new()
	history_request = HTTPRequest.new()
	add_child(http_request)
	add_child(history_request)
	http_request.request_completed.connect(_on_request_completed)
	history_request.request_completed.connect(_on_history_request_completed)
	
	# 确保节点存在后再连接信号
	if has_node("VBoxContainer/AddButton"):
		$VBoxContainer/AddButton.pressed.connect(_on_add_pressed)
		print('add connectted')
	else:
		print('add pressed not connectted')
	
	if has_node("VBoxContainer/HBoxContainer/ConfigButton"):
		$VBoxContainer/HBoxContainer/ConfigButton.pressed.connect(_on_config_pressed)
	
	if has_node("AddURLPanel/VBoxContainer/SubmitButton"):
		$AddURLPanel/VBoxContainer/SubmitButton.pressed.connect(_on_submit_pressed)
	
	if has_node("AddURLPanel/VBoxContainer/HBoxContainer/CloseButton"):
		$AddURLPanel/VBoxContainer/HBoxContainer/CloseButton.pressed.connect(_on_close_pressed)
	
	# Load server configuration
	load_server_config()
	# 加载历史记录
	load_history()

func load_server_config():
	config = ConfigFile.new()
	var err = config.load(CONFIG_FILE)
	if err != OK:
		# Create default config if it doesn't exist
		config.set_value("servers", "default", "http://localhost:8080")
		config.save(CONFIG_FILE)
	
	# Load all server URLs
	server_urls.clear()
	var servers = config.get_section_keys("servers")
	for server in servers:
		var url = config.get_value("servers", server)
		server_urls.append(url)

func get_current_server_url() -> String:
	if server_urls.size() == 0:
		return "http://localhost:8080"
	return server_urls[current_server_index]

func try_next_server():
	current_server_index = (current_server_index + 1) % server_urls.size()
	load_history()

func load_history():
	var server_url = get_current_server_url() + API_HISTORY
	var error = history_request.request(server_url)
	if error != OK:
		print("Error requesting history: ", error)
		try_next_server()

func _on_history_request_completed(result, response_code, headers, body):
	if result == HTTPRequest.RESULT_SUCCESS and response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			clear_history_list()
			for item in json:
				add_url_item(item.url, item.tags)
	else:
		try_next_server()

func clear_history_list():
	if has_node("VBoxContainer/ScrollContainer/HistoryList"):
		for child in $VBoxContainer/ScrollContainer/HistoryList.get_children():
			child.queue_free()

func add_url_item(url: String, tags: Array):
	if has_node("VBoxContainer/ScrollContainer/HistoryList"):
		var item = url_item_scene.instantiate()
		$VBoxContainer/ScrollContainer/HistoryList.add_child(item)
		item.set_url(url)
		item.set_tags(tags)

func _on_add_pressed():
	if has_node("AddURLPanel"):
		$AddURLPanel.visible = true

func _on_config_pressed():
	var config_panel = config_panel_scene.instantiate()
	add_child(config_panel)

func _on_close_pressed():
	if has_node("AddURLPanel"):
		$AddURLPanel.visible = false

func _on_submit_pressed():
	if not has_node("AddURLPanel/VBoxContainer/URLLineEdit") or not has_node("AddURLPanel/VBoxContainer/TagLineEdit"):
		return
		
	var url = $AddURLPanel/VBoxContainer/URLLineEdit.text
	var tags = $AddURLPanel/VBoxContainer/TagLineEdit.text
	
	if url.is_empty():
		if has_node("AddURLPanel/VBoxContainer/StatusLabel"):
			$AddURLPanel/VBoxContainer/StatusLabel.text = "Please enter a URL"
		return
		
	var headers = ["Content-Type: application/json"]
	var body = JSON.stringify({
		"url": url,
		"tags": tags.split(",")
	})
	
	var server_url = get_current_server_url() + API_SAVE
	if has_node("AddURLPanel/VBoxContainer/StatusLabel"):
		$AddURLPanel/VBoxContainer/StatusLabel.text = "Sending..."
	
	var error = http_request.request(server_url, headers, HTTPClient.METHOD_POST, body)
	if error != OK and has_node("AddURLPanel/VBoxContainer/StatusLabel"):
		$AddURLPanel/VBoxContainer/StatusLabel.text = "Error: " + str(error)
		try_next_server()

func _on_request_completed(result, response_code, headers, body):
	if not has_node("AddURLPanel/VBoxContainer/StatusLabel"):
		return
		
	if result == HTTPRequest.RESULT_SUCCESS:
		if response_code == 201:  # 服务器返回201表示创建成功
			$AddURLPanel/VBoxContainer/StatusLabel.text = "Successfully saved!"
			if has_node("AddURLPanel/VBoxContainer/URLLineEdit"):
				$AddURLPanel/VBoxContainer/URLLineEdit.text = ""
			if has_node("AddURLPanel/VBoxContainer/TagLineEdit"):
				$AddURLPanel/VBoxContainer/TagLineEdit.text = ""
			if has_node("AddURLPanel"):
				$AddURLPanel.visible = false
			load_history()  # 重新加载历史记录
		else:
			$AddURLPanel/VBoxContainer/StatusLabel.text = "Error: Server returned " + str(response_code)
			try_next_server()
	else:
		$AddURLPanel/VBoxContainer/StatusLabel.text = "Error: Request failed"
		try_next_server() 
