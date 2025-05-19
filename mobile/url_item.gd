extends PanelContainer

var current_url: String = ""

func _ready():
	# 连接RichTextLabel的信号
	$MarginContainer/VBoxContainer/URLLabel.gui_input.connect(_on_url_label_gui_input)

func set_url(url: String):
	current_url = url
	$MarginContainer/VBoxContainer/URLLabel.text = "[url]" + url + "[/url]"

func set_tags(tags: Array):
	var tags_text = ""
	for tag in tags:
		if tags_text != "":
			tags_text += ", "
		tags_text += tag
	$MarginContainer/VBoxContainer/TagsLabel.text = tags_text

func _on_url_label_gui_input(event: InputEvent):
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
			# 长按检测
			await get_tree().create_timer(0.5).timeout
			if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT):
				# 复制URL到剪贴板
				DisplayServer.clipboard_set(current_url)
				# 显示复制成功提示
				var notification = Label.new()
				notification.text = "URL已复制到剪贴板"
				notification.position = get_global_mouse_position()
				add_child(notification)
				# 1秒后移除提示
				await get_tree().create_timer(1.0).timeout
				notification.queue_free() 