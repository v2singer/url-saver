extends Control

const CONFIG_FILE = "user://server_config.cfg"
const API_HISTORY = "/extension/urls"
const API_SAVE = "/extension/urls"
const MAX_RETRIES = 1
const RETRY_DELAY = 1.0  # seconds

var http_request: HTTPRequest
var history_request: HTTPRequest
var url_item_scene = preload("res://url_item.tscn")
var config_panel_scene = preload("res://config_panel.tscn")
var config: ConfigFile
var current_server_index = 0
var server_urls = []
var is_requesting = false
var retry_count = 0
var retry_timer: Timer

func _ready():
	if OS.get_name() == "Windows":
		DisplayServer.window_set_size(Vector2i(1280, 720))
	elif OS.get_name() == "Android":
		DisplayServer.window_set_size(Vector2i(720, 1280))
	# 等待一帧以确保所有节点都已准备好
	await get_tree().process_frame
	
	http_request = HTTPRequest.new()
	history_request = HTTPRequest.new()
	add_child(http_request)
	add_child(history_request)
	http_request.request_completed.connect(_on_request_completed)
	history_request.request_completed.connect(_on_history_request_completed)
	
	# 创建重试定时器
	retry_timer = Timer.new()
	retry_timer.one_shot = true
	retry_timer.timeout.connect(_on_retry_timeout)
	add_child(retry_timer)
	
	# Load server configuration
	load_server_config()
	# 加载历史记录
	load_history()
	
	# 检查是否有传入的URL
	if OS.has_feature("Android"):
		_check_android_intent()
	elif OS.has_feature("iOS"):
		_check_ios_url()

func _check_android_intent():
	if OS.has_feature("Android"):
		var intent_data = Engine.get_singleton("GodotAndroid").get_intent_data()
		if intent_data:
			# 处理分享的文字内容
			if intent_data.has("text"):
				var shared_text = intent_data["text"]
				_handle_shared_text(shared_text)
			# 处理分享的URL
			elif intent_data.has("url"):
				var shared_url = intent_data["url"]
				_handle_shared_url(shared_url)

func _check_ios_url():
	if OS.has_feature("iOS"):
		# 注册处理URL的回调
		Engine.get_singleton("GodotIOS").connect("url_received", _on_ios_url_received)
		# 检查启动URL
		var launch_url = Engine.get_singleton("GodotIOS").get_launch_url()
		if launch_url:
			_handle_shared_url(launch_url)

func _on_ios_url_received(url: String):
	_handle_shared_url(url)

func _handle_shared_url(url: String, tags: Array = ["bilibili"]):
	if url.begins_with("http://") or url.begins_with("https://"):
		# 自动保存URL到服务器
		_save_url_to_server(url, tags)

func _save_url_to_server(url: String, tags: Array):
	if is_requesting:
		return
		
	var headers = ["Content-Type: application/json"]
	var body = JSON.stringify({
		"url": url,
		"tags": tags
	})
	
	is_requesting = true
	var server_url = get_current_server_url() + API_SAVE
	
	var error = http_request.request(server_url, headers, HTTPClient.METHOD_POST, body)
	if error != OK:
		is_requesting = false
		if error in [25, 44]:  # 网络相关错误
			if retry_count < MAX_RETRIES:
				retry_timer.start(RETRY_DELAY)
			else:
				try_next_server()
		else:
			try_next_server()

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


func get_current_server_url():
	if server_urls.size() == 0:
		return "http://localhost:8080"
	return server_urls[current_server_index]

func try_next_server():
	current_server_index = (current_server_index + 1) % server_urls.size()
	retry_count = 0
	load_history()

func _on_retry_timeout():
	if retry_count < MAX_RETRIES:
		retry_count += 1
		print("Retrying request, attempt ", retry_count, " of ", MAX_RETRIES)
		load_history()
	else:
		print("Max retries reached, trying next server")
		try_next_server()

func load_history():
	if is_requesting:
		return
		
	is_requesting = true
	var server_url = get_current_server_url() + API_HISTORY
	
	# 设置超时
	var client = HTTPClient.new()
	client.set_blocking_mode(true)
	client.set_read_chunk_size(65536)  # 64KB chunks
	
	var error = history_request.request(server_url)
	if error != OK:
		print("Error requesting history: ", error)
		is_requesting = false
		if error in [25, 44]:  # 网络相关错误
			if retry_count < MAX_RETRIES:
				retry_timer.start(RETRY_DELAY)
			else:
				try_next_server()
		else:
			try_next_server()

func _on_history_request_completed(result, response_code, _headers, body):
	is_requesting = false
	print("History request completed with result: ", result, " response code: ", response_code)
	
	if result == HTTPRequest.RESULT_SUCCESS and response_code == 200:
		var json = JSON.parse_string(body.get_string_from_utf8())
		if json:
			clear_history_list()
			for item in json:
				add_url_item(item.url, item.tags)
		retry_count = 0  # 重置重试计数
	else:
		if result in [HTTPRequest.RESULT_CONNECTION_ERROR, HTTPRequest.RESULT_CHUNKED_BODY_SIZE_MISMATCH]:
			if retry_count < MAX_RETRIES:
				retry_timer.start(RETRY_DELAY)
			else:
				try_next_server()
		else:
			try_next_server()
		retry_count = 0  # 重置重试计数

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
	if is_requesting:
		return
		
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
	
	is_requesting = true
	var server_url = get_current_server_url() + API_SAVE
	if has_node("AddURLPanel/VBoxContainer/StatusLabel"):
		$AddURLPanel/VBoxContainer/StatusLabel.text = "Sending..."
	
	var error = http_request.request(server_url, headers, HTTPClient.METHOD_POST, body)
	if error != OK and has_node("AddURLPanel/VBoxContainer/StatusLabel"):
		$AddURLPanel/VBoxContainer/StatusLabel.text = "Error: " + str(error)
		is_requesting = false
		if error in [25, 44]:  # 网络相关错误
			if retry_count < MAX_RETRIES:
				retry_timer.start(RETRY_DELAY)
			else:
				try_next_server()
		else:
			try_next_server()

func _on_request_completed(result, response_code, _headers, _body):
	is_requesting = false
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
			retry_count = 0  # 重置重试计数
			retry_count = 0  # 重置重试计数
			load_history()  # 重新加载历史记录
		else:
			$AddURLPanel/VBoxContainer/StatusLabel.text = "Error: Server returned " + str(response_code)
			if result in [HTTPRequest.RESULT_CONNECTION_ERROR, HTTPRequest.RESULT_CHUNKED_BODY_SIZE_MISMATCH]:
				if retry_count < MAX_RETRIES:
					retry_timer.start(RETRY_DELAY)
				else:
					try_next_server()
			else:
				try_next_server()
	else:
		$AddURLPanel/VBoxContainer/StatusLabel.text = "Error: Request failed"
		if result in [HTTPRequest.RESULT_CONNECTION_ERROR, HTTPRequest.RESULT_CHUNKED_BODY_SIZE_MISMATCH]:
			if retry_count < MAX_RETRIES:
				retry_timer.start(RETRY_DELAY)
			else:
				try_next_server()
		else:
			try_next_server() 

func _handle_shared_text(text: String):
	# 检查文本是否包含URL
	var url_regex = RegEx.new()
	url_regex.compile("https?://\\S+")
	var result = url_regex.search(text)
	
	if result:
		# 如果文本包含URL，提取并处理URL
		var url = result.get_string()
		_handle_shared_url(url)
	else:
		# 如果不是URL，可以显示一个对话框让用户确认是否保存为文本
		var dialog = AcceptDialog.new()
		dialog.title = "收到分享的文本"
		dialog.dialog_text = "是否保存以下文本？\n\n" + text
		dialog.confirmed.connect(func(): _save_text_to_server(text))
		add_child(dialog)
		dialog.popup_centered()

func _save_text_to_server(text: String):
	# 将文本保存到服务器
	_save_url_to_server(text, ["text"]) 
