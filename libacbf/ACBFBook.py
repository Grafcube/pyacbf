import os
import pathlib
from typing import List, Dict, Optional, Union
from re import sub, findall, IGNORECASE
from lxml import etree
import zipfile as Zip
from libacbf.Constants import BookNamespace
from libacbf.ACBFMetadata import ACBFMetadata
from libacbf.ACBFBody import ACBFBody
from libacbf.ACBFData import ACBFData

class ACBFBook:
	"""
	docstring
	"""
	def __init__(self, file_path: str = "libacbf/templates/base_template_1.1.acbf"):
		self.is_open: bool = True

		self.book_path = os.path.abspath(file_path)

		self.archive_path: Optional[Union[Zip.Path]] = None

		self.archive: Optional[Union[Zip.ZipFile]] = None

		path = pathlib.Path(file_path)
		if path.suffix == ".acbf":
			with open(file_path, encoding="utf-8") as book:
				contents = book.read()
		elif path.suffix == ".cbz":
			self.archive = Zip.ZipFile(file_path, 'r')
			self.archive_path = Zip.Path(self.archive)
		elif path.suffix == ".cbr":
			pass
		elif path.suffix == ".cb7":
			pass
		else:
			raise ValueError("File is not an ACBF Ebook")

		if self.archive is not None:
			arch_iter = self.archive_path.iterdir()
			acbf_path = None
			while True:
				try:
					acbf_path = next(arch_iter)
				except StopIteration:
					raise ValueError("File is not an ACBF Ebook")
				if acbf_path.name.endswith(".acbf"):
					break

			contents = acbf_path.read_text("utf-8")

		self.root = etree.fromstring(bytes(contents, encoding="utf-8"))
		self.tree = self.root.getroottree()

		validate_acbf(self.root)

		self.namespace: BookNamespace = BookNamespace(f"{{{self.root.nsmap[None]}}}")
		self.styles: List[str] = findall(r'<\?xml-stylesheet type="text\/css" href="(.+)"\?>', contents, IGNORECASE)

		self.Metadata: ACBFMetadata = ACBFMetadata(self)

		self.Body: ACBFBody = ACBFBody(self)

		self.Data: ACBFData = ACBFData(self)

		self.Stylesheet: Optional[str] = None
		if self.root.find(f"{self.namespace.ACBFns}style") is not None:
			self.Stylesheet = self.root.find(f"{self.namespace.ACBFns}style").text.strip()

		self.References: Dict[str, Dict[str, str]] = get_references(self.root.find(f"{self.namespace.ACBFns}references"), self.namespace)

	def save(self, path: str = ""):
		if path == "":
			path = self.book_path

	def close(self):
		if self.archive is not None:
			self.archive.close()
			self.is_open = False

	def __enter__(self):
		return self

	def __exit__(self, exception_type, exception_value, traceback):
		self.close()

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

def get_references(ref_root, ns: BookNamespace) -> Dict[str, Dict[str, str]]:
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
