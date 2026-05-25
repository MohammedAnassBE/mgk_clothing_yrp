# Copyright (c) 2026, MGK Clothing and contributors
# For license information, please see license.txt

from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.model.document import Document


class MGKAgent(Document):
	def onload(self):
		"""Load linked Address and Contact records into `__onload` for the sidebar."""
		load_address_and_contact(self)

	def on_trash(self):
		delete_contact_and_address("MGK Agent", self.name)
