from __future__ import annotations
import os
from typing import TYPE_CHECKING, List, Dict, Optional
if TYPE_CHECKING:
	from libacbf.ACBFBook import ACBFBook

from collections import namedtuple
from pathlib import Path
from magic.magic import from_buffer
from re import IGNORECASE, fullmatch, split, sub
import requests
from lxml import etree
from libacbf.ACBFData import ACBFData
from libacbf.BookData import BookData
from libacbf.Constants import BookNamespace, ImageRefType, PageTransitions
import libacbf.Structs as structs

Vec2 = namedtuple("Vector2", "x y")
url_pattern = r'(((ftp|http|https):\/\/)|(\/)|(..\/))(\w+:{0,1}\w*@)?(\S+)(:[0-9]+)?(\/|\/([\w#!:.?+=&%@!\-\/]))?'

class Page:
	"""
	docstring
	"""
	def __init__(self, page, book: ACBFBook):
		self.book = book

		ns: BookNamespace = book.namespace
		book_data: ACBFData = book.Data

		# Optional
		self.bg_color: Optional[str] = None
		if "bgcolor" in page.keys():
			self.bg_color = page.attrib["bgcolor"]

		self.transition: Optional[PageTransitions] = None
		if "transition" in page.keys():
			self.transition = PageTransitions[page.attrib["transition"]]

		# Sub
		self.image_ref: str = page.find(f"{ns.ACBFns}image").attrib["href"]

		ref_t = None
		img = None
		if self.image_ref.startswith("#"):
			file_id = sub("#", "", self.image_ref)
			ref_t = ImageRefType.Embedded
			img = book_data[file_id]
		elif self.image_ref.startswith("zip:"):
			ref_t = ImageRefType.Archived
			# Data in archive (after reading archive is added)
		elif fullmatch(url_pattern, self.image_ref, IGNORECASE):
			response = requests.get(self.image_ref)
			file_id = split("/", self.image_ref)[-1]
			contents = response.content
			contents_type = from_buffer(contents, True)
			ref_t = ImageRefType.URL
			img = BookData(file_id, contents_type, contents)
		else:
			if self.image_ref.startswith("file://"):
				file_path = Path(os.path.abspath(self.image_ref))
			else:
				file_path = Path(self.image_ref)
			path = None

			if os.path.isabs(self.image_ref):
				ref_t = ImageRefType.Local
				path = file_path
			else:
				if book.archive_path is not None:
					ref_t = ImageRefType.SelfArchived
					path = book.archive_path/file_path

				else:
					ref_t = ImageRefType.Local
					parent_dir = Path(book.book_path).parent
					path = parent_dir/file_path

			file_id = path.name
			with open(path, "rb") as image:
				contents = image.read()
			contents_type = from_buffer(contents, True)
			img = BookData(file_id, contents_type, contents)

		self.ref_type: ImageRefType = ref_t

		self.image: BookData = img

		## Optional
		self.title: Dict[str, str] = {}
		title_items = page.findall(f"{ns.ACBFns}title")
		for t in title_items:
			if "lang" in t.keys():
				self.title[t.attrib["lang"]] = t.text
			else:
				self.title["_"] = t.text

		self.text_layers: Dict[str, TextLayer] = get_textlayers(page, ns)

		self.frames: List[structs.Frame] = get_frames(page, ns)

		self.jumps: List[structs.Jump] = get_jumps(page, ns)

class TextLayer:
	"""
	docstring
	"""
	def __init__(self, layer, ns: BookNamespace):
		self.language = layer.attrib["lang"]

		self.bg_color = None
		if "bgcolor" in layer.keys():
			self.bg_color = layer.attrib["bgcolor"]

		self.text_areas: List[TextArea] = []
		areas = layer.findall(f"{ns.ACBFns}text-area")
		for ar in areas:
			self.text_areas.append(TextArea(ar, ns))

class TextArea:
	"""
	docstring
	"""
	def __init__(self, area, ns: BookNamespace):
		self.points = get_points(area.attrib["points"])

		self.paragraph: str = ""
		pa = []
		for p in area.findall(f"{ns.ACBFns}p"):
			text = sub(r"<\/?p[^>]*>", "", str(etree.tostring(p, encoding="utf-8"), encoding="utf-8").strip())
			pa.append(text)
		self.paragraph = "\n".join(pa)

		# Optional
		self.bg_color = None
		if "bgcolor" in area.keys():
			self.bg_color = area.attrib["bgcolor"]

		self.rotation = 0
		if "text-rotation" in area.keys():
			self.rotation = area.attrib["text-rotation"]

		self.type = None
		if "type" in area.keys():
			self.rotation = area.attrib["type"]

		self.inverted = False
		if "inverted" in area.keys():
			self.rotation = area.attrib["inverted"]

		self.transparent = False
		if "transparent" in area.keys():
			self.rotation = area.attrib["transparent"]

def get_textlayers(item, ns: BookNamespace):
	text_layers = {}
	textlayer_items = item.findall(f"{ns.ACBFns}text-layer")
	for lr in textlayer_items:
		new_lr = TextLayer(lr, ns)
		text_layers[new_lr.language] = new_lr
	return text_layers

def get_frames(item, ns: BookNamespace):
	frames = []
	frame_items = item.findall(f"{ns.ACBFns}frame")
	for fr in frame_items:
		frame = structs.Frame()
		frame.points = get_points(fr.attrib["points"])

		if "bgcolor" in fr.keys():
			frame.bgcolor = fr.attrib["bgcolor"]

		frames.append(frame)

	return frames

def get_jumps(item, ns: BookNamespace):
	jumps = []
	jump_items = item.findall(f"{ns.ACBFns}jump")
	for jp in jump_items:
		jump = structs.Jump()
		jump.points = get_points(jp.attrib["points"])
		jump.page = jp.attrib["page"]

		jumps.append(jump)

	return jumps

def get_points(pts_str: str):
	pts = []
	pts_l = split(" ", pts_str)
	for pt in pts_l:
		ls = split(",", pt)
		pts.append(Vec2(int(ls[0]), int(ls[1])))
	return pts
