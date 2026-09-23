# engine/autoload/pipeline_data.gd
# Amorce FOURNIE PAR LA PIPELINE (chargement de données, sans LLM runtime).
extends Node
## Charge le bundle runtime compilé par la pipeline. Le jeu final n'a pas
## besoin d'un LLM : toutes les règles/effets/dialogues sont des données.

const DATA_PATH := "res://engine/data/runtime_data.json"
const DIALOGS_PATH := "res://engine/data/dialogs_compiled.json"
const RULES_PATH := "res://engine/data/rules_compiled.json"

var runtime: Dictionary = {}
var dialogs: Array = []
var rules: Dictionary = {}

func _ready() -> void:
	runtime = _load_json(DATA_PATH)
	dialogs = _load_json(DIALOGS_PATH)
	rules = _load_json(RULES_PATH)

func _load_json(path: String) -> Variant:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("PipelineData: fichier manquant " + path)
		return {}
	return JSON.parse_string(f.get_as_text())

func get_entity(kind: String, id: String) -> Dictionary:
	for e in runtime.get("entities", {}).get(kind, []):
		if e.get("id") == id:
			return e
	return {}
