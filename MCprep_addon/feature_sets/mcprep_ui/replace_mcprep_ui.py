import bpy
from bpy.types import UILayout, Context
from MCprep_addon import util 
from MCprep_addon.mcprep_ui import (
	MCPREP_PT_spawn, 
	MCPREP_PT_mob_spawner, 
	MCPREP_PT_model_spawner,
	MCPREP_PT_item_spawner,
	MCPREP_PT_effects_spawner,
	MCPREP_PT_entity_spawner,
	MCPREP_PT_meshswap_spawner
)
from typing import Union

icon_ref = {}

def get_icon(section:Union[str], icon_name:str, override:bool = False, not_found:str = 'NONE'):
	"""
	section: (main, mobs, item, effect)
	override for parts that need icon to be on
	"""
	use_icons = not env.use_icons or override
	icon = None
	if section != "":
		if use_icons or env.preview_collections[section] != "":
			icon = env.preview_collections[section].get(icon_name)
	if not icon:
		icons = UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items.keys()

		for i, k in enumerate(icons):
			icon_ref[k] = i

		icon = icon_ref.get(icon_name)
		if icon:
			return icon + 9
		else:
			return icon_ref[not_found]

	return icon.icon_id

def draw_spawner_mob(self, context: Context):
	scn_props = context.scene.mcprep_props

	layout = self.layout
	layout.label(text="Import pre-rigged mobs & players")
	split = layout.split()
	col = split.column(align=True)

	row = col.row()
	row.prop(scn_props, "spawn_rig_category", text="")
	if scn_props.mob_list:
		row = col.row()
		row.template_list(
			"MCPREP_UL_mob", "",
			scn_props, "mob_list",
			scn_props, "mob_list_index",
			rows=4)
	elif scn_props.mob_list_all:
		box = col.box()
		b_row = box.row()
		b_row.label(text="")
		b_col = box.column()
		b_col.scale_y = 0.7
		b_col.label(text="No mobs in category,")
		b_col.label(text="install a rig below or")
		b_col.label(text="copy file to folder.")
		b_row = box.row()
		b_row.label(text="")
	else:
		box = col.box()
		b_row = box.row()
		b_row.label(text="No mobs loaded")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.reload_spawners", text="Reload assets", icon="ERROR")

	# get which rig is selected
	if scn_props.mob_list:
		name = scn_props.mob_list[scn_props.mob_list_index].name
		mcmob_type = scn_props.mob_list[scn_props.mob_list_index].mcmob_type
	else:
		name = ""
		mcmob_type = ""
	col = layout.column(align=True)
	row = col.row(align=True)
	row.scale_y = 1.5
	row.enabled = len(scn_props.mob_list) > 0
	p = row.operator("mcprep.mob_spawner", text="Spawn " + name)
	if mcmob_type:
		p.mcmob_type = mcmob_type

	# Skip prep materials in case of unique shader.
	if conf.json_data and name in conf.json_data.get("mob_skip_prep", []):
		p.prep_materials = False

	p = col.operator("mcprep.mob_install_menu")
	p.mob_category = scn_props.spawn_rig_category

	split = layout.split()
	col = split.column(align=True)
	row = col.row(align=True)
	if not scn_props.show_settings_spawner:
		row.prop(
			scn_props, "show_settings_spawner",
			text="Advanced", icon="TRIA_RIGHT")
		row.operator(
			"mcprep.open_preferences",
			text="", icon="PREFERENCES").tab = "settings"
	else:
		row.prop(
			scn_props, "show_settings_spawner",
			text="Advanced", icon="TRIA_DOWN")
		row.operator(
			"mcprep.open_preferences",
			text="", icon="PREFERENCES").tab = "settings"

def draw_spawner_meshswap(self, context: Context):
	scn_props = context.scene.mcprep_props

	layout = self.layout
	layout.label(text="Import pre-made blocks (e.g. lights)")
	split = layout.split()
	col = split.column(align=True)

	if scn_props.meshswap_list:
		col.template_list(
			"MCPREP_UL_meshswap", "",
			scn_props, "meshswap_list",
			scn_props, "meshswap_list_index",
			rows=4)
		# col.label(text=datapass.split("/")[0])
	elif not context.scene.meshswap_path.lower().endswith('.blend'):
		box = col.box()
		b_row = box.row()
		b_row.label(text="Meshswap file must be a .blend")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.meshswap_path_reset", icon=LOAD_FACTORY,
			text="Reset meshswap path")
	elif not os.path.isfile(bpy.path.abspath(context.scene.meshswap_path)):
		box = col.box()
		b_row = box.row()
		b_row.label(text="Meshswap file not found")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.meshswap_path_reset", icon=LOAD_FACTORY,
			text="Reset meshswap path")
	else:
		box = col.box()
		b_row = box.row()
		b_row.label(text="No blocks loaded")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.reload_spawners",
			text="Reload assets", icon="ERROR")

	col = layout.column(align=True)
	row = col.row()
	row.scale_y = 1.5
	row.enabled = len(scn_props.meshswap_list) > 0
	if scn_props.meshswap_list:
		name = scn_props.meshswap_list[scn_props.meshswap_list_index].name
		block = scn_props.meshswap_list[scn_props.meshswap_list_index].block
		method = scn_props.meshswap_list[scn_props.meshswap_list_index].method
		p = row.operator("mcprep.meshswap_spawner", text="Place: " + name)
		p.block = block
		p.method = method
		p.location = util.get_cuser_location(context)
		# Ensure meshswap with rigs is made real, so the rigs can be used.
		if conf.json_data and block in conf.json_data.get("make_real", []):
			p.make_real = True

	else:
		row.operator("mcprep.meshswap_spawner", text="Place block")
	# something to directly open meshswap file??

def draw_spawner_item(self, context: Context):
	"""Code for drawing the item spawner"""
	scn_props = context.scene.mcprep_props

	layout = self.layout
	layout.label(text="Generate items from textures")
	split = layout.split()
	col = split.column(align=True)

	if scn_props.item_list:
		col.template_list(
			"MCPREP_UL_item", "",
			scn_props, "item_list",
			scn_props, "item_list_index",
			rows=4)
		col = layout.column(align=True)
		row = col.row(align=True)
		row.scale_y = 1.5
		name = scn_props.item_list[scn_props.item_list_index].name
		row.operator("mcprep.spawn_item", text="Place: " + name)
		row = col.row(align=True)
		row.operator("mcprep.spawn_item_file")
	else:
		box = col.box()
		b_row = box.row()
		b_row.label(text="No items loaded")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.reload_spawners",
			text="Reload assets", icon="ERROR")

		col = layout.column(align=True)
		col.enabled = False
		row = col.row(align=True)
		row.scale_y = 1.5
		row.operator("mcprep.spawn_item", text="Place item")
		row = col.row(align=True)
		row.operator("mcprep.spawn_item_file")

def draw_spawner_entity(self, context: Context):
	scn_props = context.scene.mcprep_props

	layout = self.layout
	layout.label(text="Import pre-rigged entities")
	split = layout.split()
	col = split.column(align=True)

	if scn_props.entity_list:
		col.template_list(
			"MCPREP_UL_entity", "",
			scn_props, "entity_list",
			scn_props, "entity_list_index",
			rows=4)

	elif not context.scene.entity_path.lower().endswith('.blend'):
		box = col.box()
		b_row = box.row()
		b_row.label(text="Entity file must be a .blend")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.entity_path_reset", icon=LOAD_FACTORY,
			text="Reset entity path")
	elif not os.path.isfile(bpy.path.abspath(context.scene.entity_path)):
		box = col.box()
		b_row = box.row()
		b_row.label(text="Entity file not found")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.entity_path_reset", icon=LOAD_FACTORY,
			text="Reset entity path")
	else:
		box = col.box()
		b_row = box.row()
		b_row.label(text="No entities loaded")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.reload_spawners",
			text="Reload assets", icon="ERROR")

	col = layout.column(align=True)
	row = col.row()
	row.scale_y = 1.5
	row.enabled = len(scn_props.entity_list) > 0
	if scn_props.entity_list:
		name = scn_props.entity_list[scn_props.entity_list_index].name
		entity = scn_props.entity_list[scn_props.entity_list_index].entity
		p = row.operator("mcprep.entity_spawner", text="Spawn: " + name)
		p.entity = entity
	else:
		row.operator("mcprep.entity_spawner", text="Spawn Entity")

def draw_spawner_model(self, context: Context):
	"""Code for drawing the model block spawner"""
	scn_props = context.scene.mcprep_props
	addon_prefs = util.get_user_preferences(context)

	layout = self.layout
	layout.label(text="Generate models from .json files")
	split = layout.split()
	col = split.column(align=True)

	if scn_props.model_list:
		col.template_list(
			"MCPREP_UL_model", "",
			scn_props, "model_list",
			scn_props, "model_list_index",
			rows=4)

		col = layout.column(align=True)
		row = col.row(align=True)
		row.scale_y = 1.5
		model = scn_props.model_list[scn_props.model_list_index]
		ops = row.operator("mcprep.spawn_model", text="Place: " + model.name)
		ops.location = util.get_cuser_location(context)
		ops.filepath = model.filepath
		if addon_prefs.MCprep_exporter_type == "Mineways":
			ops.snapping = "offset"
		elif addon_prefs.MCprep_exporter_type == "jmc2obj":
			ops.snapping = "center"
	else:
		box = col.box()
		b_row = box.row()
		b_row.label(text="No models loaded")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.reload_spawners",
			text="Reload assets", icon="ERROR")

		col = layout.column(align=True)
		row = col.row(align=True)
		row.enabled = False
		row.scale_y = 1.5
		row.operator(mcmodel.MCPREP_OT_spawn_minecraft_model.bl_idname)

	ops = col.operator("mcprep.import_model_file")
	ops.location = util.get_cuser_location(context)
	if addon_prefs.MCprep_exporter_type == "Mineways":
		ops.snapping = "center"
	elif addon_prefs.MCprep_exporter_type == "jmc2obj":
		ops.snapping = "offset"

def draw_spawner_effect(self, context: Context):
	"""Code for drawing the effects spawner"""
	scn_props = context.scene.mcprep_props

	layout = self.layout
	col = layout.column(align=True)
	col.label(text="Load/generate effects")

	# Alternate draw approach, using UI list.
	if scn_props.effects_list:
		col.template_list(
			"MCPREP_UL_effects", "",
			scn_props, "effects_list",
			scn_props, "effects_list_index",
			rows=4)
		col = layout.column(align=True)
		row = col.row(align=True)
		row.scale_y = 1.5
		effect = scn_props.effects_list[scn_props.effects_list_index]
		if effect.effect_type in (effects.GEO_AREA, effects.PARTICLE_AREA):
			ops = row.operator(
				"mcprep.spawn_global_effect", text="Add: " + effect.name)
			ops.effect_id = str(effect.index)
		elif effect.effect_type in (effects.COLLECTION, effects.IMG_SEQ):
			ops = row.operator(
				"mcprep.spawn_instant_effect", text="Add: " + effect.name)
			ops.effect_id = str(effect.index)
			ops.location = util.get_cuser_location(context)
			ops.frame = context.scene.frame_current
	else:
		box = col.box()
		b_row = box.row()
		b_row.label(text="No effects loaded")
		b_row = box.row()
		b_row.scale_y = 2
		b_row.operator(
			"mcprep.reload_spawners",
			text="Reload assets", icon="ERROR")

		col = layout.column(align=True)
		row = col.row(align=True)
		row.scale_y = 1.5
		row.enabled = False
		row.operator("mcprep.spawn_item", text="Add effect")
	row = col.row(align=True)
	ops = row.operator("mcprep.spawn_particle_planes")
	ops.location = util.get_cuser_location(context)
	ops.frame = context.scene.frame_current

def draw_spawner_advance(self, context: Context):
	layout = self.layout
	col = layout.column()
	
	box = col.box()
	b_row = box.row()
	b_col = b_row.column(align=False)
	b_col.label(text="Resource pack")
	subrow = b_col.row(align=True)
	subrow.prop(context.scene, "mcprep_texturepack_path", text="")
	subrow.operator(
		"mcprep.reset_texture_path", icon=LOAD_FACTORY, text="")
	b_row = box.row()
	b_col = b_row.column(align=True)
	b_col.operator("mcprep.reload_models")
	b_row = box.row()
	b_col = b_row.column(align=True)
	b_col.operator("mcprep.reload_items")
	
	box = col.box()
	b_row = box.row()
	b_col = b_row.column(align=False)
	b_col.label(text="Mob spawner folder")
	subrow = b_col.row(align=True)
	subrow.prop(context.scene, "mcprep_mob_path", text="")
	subrow.operator(
		"mcprep.spawn_path_reset", icon=LOAD_FACTORY, text="")
	b_row = box.row()
	b_col = b_row.column(align=True)
	ops = b_col.operator("mcprep.openfolder", text="Open mob folder")
	ops.folder = context.scene.mcprep_mob_path

	if not scn_props.mob_list:
		b_col.operator("mcprep.mob_install_icon")
	else:
		icon_index = scn_props.mob_list[scn_props.mob_list_index].index
	if "mob-{}".format(icon_index) in conf.preview_collections["mobs"]:
		b_col.operator(
		"mcprep.mob_install_icon", text="Change mob icon")
	else:
		b_col.operator("mcprep.mob_install_icon")
	b_col.operator("mcprep.mob_uninstall")
	b_col.operator("mcprep.reload_mobs", text="Reload mobs")
	b_col.label(text=mcmob_type)
	
	box = col.box()
	b_row = box.row()
	b_col = b_row.column(align=False)
	b_col.label(text="Meshswap file")
	subrow = b_col.row(align=True)
	subrow.prop(context.scene, "meshswap_path", text="")
	subrow.operator(
		"mcprep.meshswap_path_reset", icon=LOAD_FACTORY, text="")
	if not context.scene.meshswap_path.lower().endswith('.blend'):
		b_col.label(text="MeshSwap file must be a .blend", icon="ERROR")
	elif not os.path.isfile(bpy.path.abspath(context.scene.meshswap_path)):
		b_col.label(text="MeshSwap file not found", icon="ERROR")
	b_row = box.row()
	b_col = b_row.column(align=True)
	b_col.operator("mcprep.reload_meshswap")
	
	box = col.box()
	b_row = box.row()
	b_col = b_row.column(align=False)
	b_col.label(text="Entity file")
	subrow = b_col.row(align=True)
	subrow.prop(context.scene, "entity_path", text="")
	subrow.operator("mcprep.entity_path_reset", icon=LOAD_FACTORY, text="")
		if not context.scene.entity_path.lower().endswith('.blend'):
			b_col.label(text="MeshSwap file must be a .blend", icon="ERROR")
		elif not os.path.isfile(bpy.path.abspath(context.scene.entity_path)):
			b_col.label(text="MeshSwap file not found", icon="ERROR")
		b_row = box.row()
		b_col = b_row.column(align=True)
		b_col.operator("mcprep.reload_entities")
	
	
	box = col.box()
	b_col = box.column()
	b_col.label(text="Effects:")
	b_row = box.row()
	b_col = b_row.column(align=False)
	b_col.label(text="Effects folder")
	subrow = b_col.row(align=True)
	subrow.prop(context.scene, "mcprep_effects_path", text="")
	subrow.operator("mcprep.effects_path_reset", icon=LOAD_FACTORY, text="")
		base = bpy.path.abspath(context.scene.mcprep_effects_path)
		if not os.path.isdir(base):
			b_col.label(text="Effects folder not found", icon="ERROR")
		elif not os.path.isdir(os.path.join(base, "collection")):
			b_col.label(text="Effects/collection folder not found", icon="ERROR")
		elif not os.path.isdir(os.path.join(base, "geonodes")):
			b_col.label(text="Effects/geonodes folder not found", icon="ERROR")
		elif not os.path.isdir(os.path.join(base, "particle")):
			b_col.label(text="Effects/particle folder not found", icon="ERROR")
		b_row = box.row()
		b_col = b_row.column(align=True)
		b_col.operator("mcprep.reload_effects")

@classmethod
def disable_poll(cls, context: Context):
	return False

def drawing_spawner_tabs(self, contex: Context):
	self.draw_old(context)
	scn_props = contrxt.scene.mcprep_props
	layout = self.layout
	col = layout.column()
	col_text = col.column()
	col_text.label(text="Still under work in progress")
	col.prop(scn_props, "spawner_tabs", expand=True)
	if scn_props.spawner_tabs == "ENTITY":
		self.draw_spawner_mob(context)
		self.draw_spawner_entity(context)
	elif scn_props.spawner_tabs == "BLOCK":
		self.draw_spawner_model(context)
		self.draw_spawner_meshswap(context)
	elif scn_props.spawner_tabs == "ITEM":
		self.draw_spawner_item(context)
	elif scn_props.spawner_tabs == "EFFECT":
		self.draw_spawner_effect(context)
	else:
		self.draw_spawner_advance(context)

spawner_items = [
		('BLOCK', "Block", "Block spawner", get_icon("main", "model_icon"), 0),
		('ENTITY', "Entity", "Entity Mob rigs spawner", get_icon("main", "entity_icon"), 1),
		('ITEM', "Item", "Item spawner", get_icon("main", "sword_icon"), 2),
		('EFFECT', "Effect", "Effect spawner", get_icon("main", "sword_icon"), 3),
		('ADVANCE', "Advance", "Advance settings", get_icon("main", "sword_icon"), 3)]
	
def spawner_tabs_items():
	return spawner_items

def register():
	# Disable panels with poll
	MCPREP_PT_mob_spawner.poll_old = MCPREP_PT_mob_spawner.poll
	MCPREP_PT_mob_spawner.poll = disable_poll
	MCPREP_PT_model_spawner.poll_old = MCPREP_PT_model_spawner.poll
	MCPREP_PT_model_spawner.poll = disable_poll
	MCPREP_PT_item_spawner.poll_old = MCPREP_PT_item_spawner.poll
	MCPREP_PT_item_spawner.poll = disable_poll
	MCPREP_PT_effects_spawner.poll_old = MCPREP_PT_effects_spawner.poll
	MCPREP_PT_effects_spawner.poll = disable_poll
	MCPREP_PT_entity_spawner.poll_old = MCPREP_PT_entity_spawner.poll
	MCPREP_PT_entity_spawner.poll = disable_poll
	MCPREP_PT_meshswap_spawner.poll_old = MCPREP_PT_meshswap_spawner.poll
	MCPREP_PT_meshswap_spawner.poll = disable_poll
	
	
	bpy.types.Scene.mcprep_props.spawner_tabs = bpy.props.EnumProperty(
		name="Spawner tabs",
		description="Spawner",
		items=spawner_tabs_items
	)
	
	# Change drawing
	MCPREP_PT_spawn.draw_old = MCPREP_PT_spawn.draw
	MCPREP_PT_spawn.draw = drawing_spawner_tabs

def unregister():
	try:
		MCPREP_PT_mob_spawner.poll = MCPREP_PT_mob_spawner.poll_old
		MCPREP_PT_model_spawner.poll = MCPREP_PT_model_spawner.poll_old
		MCPREP_PT_item_spawner.poll = MCPREP_PT_item_spawner.poll_old
		MCPREP_PT_effects_spawner.poll = MCPREP_PT_effects_spawner.poll_old
		MCPREP_PT_entity_spawner.poll = MCPREP_PT_entity_spawner.poll_old
		MCPREP_PT_meshswap_spawner.poll = MCPREP_PT_meshswap_spawner.poll_old
		MCPREP_PT_spawn.draw = MCPREP_PT_spawn.draw_old
	except AttributeError:
		print("Warn")