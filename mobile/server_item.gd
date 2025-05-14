extends Panel

signal delete_requested(url)

var server_url: String

func set_url(url: String):
	server_url = url
	$HBoxContainer/URLLabel.text = url

func set_default(is_default: bool):
	$HBoxContainer/DefaultLabel.visible = is_default
	$HBoxContainer/DeleteButton.visible = not is_default

func _on_delete_pressed():
	delete_requested.emit(server_url) 