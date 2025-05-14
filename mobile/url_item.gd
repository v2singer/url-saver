extends PanelContainer

func set_url(url: String):
	$MarginContainer/VBoxContainer/URLLabel.text = url

func set_tags(tags: Array):
	var tags_text = ""
	for tag in tags:
		if tags_text != "":
			tags_text += ", "
		tags_text += tag
	$MarginContainer/VBoxContainer/TagsLabel.text = tags_text 