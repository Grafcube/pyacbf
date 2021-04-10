import pathlib
from typing import List, Dict, AnyStr, Optional
from re import sub, findall, IGNORECASE
from lxml import etree
from libacbf.Constants import BookNamespace
import libacbf.ACBFMetadata as metadata
from libacbf.ACBFBody import ACBFBody
from libacbf.ACBFData import ACBFData

class ACBFBook:
	"""
	docstring
	"""
	def __init__(self, file_path: AnyStr = "libacbf/templates/base_template_1.1.acbf"):
		self.book_path = file_path

		self.tree = None
		self.root = None

		if pathlib.Path(file_path).suffix != ".acbf": # TODO cbz handling
			raise ValueError("File is not an ACBF Ebook")
		else:
			with open(file_path, encoding="utf-8") as book:
				contents = book.read()
				self.root = etree.fromstring(bytes(contents, encoding="utf-8"))
				self.tree = self.root.getroottree()

		validate_acbf(self.root)

		self.Namespace: BookNamespace = BookNamespace(r"{" + self.root.nsmap[None] + r"}")
		self.styles: List[AnyStr] = findall(r'<\?xml-stylesheet type="text\/css" href="(.+)"\?>', contents, IGNORECASE)

		self.Metadata: metadata = metadata.ACBFMetadata(self.root.find(f"{self.Namespace.ACBFns}meta-data"), self.Namespace)

		self.Body: ACBFBody = ACBFBody(self.root.find(f"{self.Namespace.ACBFns}body"), self.Namespace)

		self.Stylesheet: Optional[AnyStr] = None
		if self.root.find(f"{self.Namespace.ACBFns}style") is not None:
			self.Stylesheet = self.root.find(f"{self.Namespace.ACBFns}style").text.strip()

		self.References: Dict[AnyStr, Dict[AnyStr, AnyStr]] = get_references(self.root.find(f"{self.Namespace.ACBFns}references"), self.Namespace)

		self.Data: Dict[AnyStr, ACBFData] = get_ACBF_data(self.root, self.Namespace)

	def save(self, path: AnyStr = ""):
		if path == "":
			path = self.book_path

def validate_acbf(root):
	"""
	docstring
	"""
	tree = root.getroottree()
	version = tree.docinfo.xml_version
	xsd_path = f"libacbf/schema/acbf-{version}.xsd"

	with open(xsd_path, encoding="utf-8") as file:
		acbf_root = etree.fromstring(bytes(file.read(), encoding="utf-8"))
		acbf_tree = acbf_root.getroottree()
		acbf_schema = etree.XMLSchema(acbf_tree)

	# TODO fix schema error. When fixed, remove try/except
	try:
		acbf_schema.assertValid(tree)
	except etree.DocumentInvalid as err:
		print("Validation failed. File may be valid (bug)")
		print(err)

def get_references(ref_root, ns: BookNamespace) -> Dict[AnyStr, Dict[AnyStr, AnyStr]]:
		references = {}
		if ref_root is None:
			return references
		reference_items = ref_root.findall(f"{ns.ACBFns}reference")
		for ref in reference_items:
			pa = []
			for p in ref.findall(f"{ns.ACBFns}p"):
				text = sub(r"<\/?p[^>]*>", "", str(etree.tostring(p, encoding="utf-8"), encoding="utf-8").strip())
				pa.append(text)
			references[ref.attrib["id"]] = {"paragraph": "\n".join(pa)}
		return references

def get_ACBF_data(root, ns: BookNamespace):
	data = {}
	if root.find(f"{ns.ACBFns}data") is not None:
		base = root.find(f"{ns.ACBFns}data")
		data_items = base.findall(f"{ns.ACBFns}binary")
		for b in data_items:
			new_data = ACBFData()
			new_data.id = b.attrib["id"]
			new_data.type = b.attrib["content-type"]
			new_data.data = b.text
			data[new_data.id] = new_data
	return data
