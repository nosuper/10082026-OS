"""The /aura route must serve the built frappe-ui page.

Requires `npm run build` in frontend/ to have run first (CI builds it
before the site tests; see .github/workflows/ci.yml).
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response


class TestAuraPage(FrappeTestCase):
    def test_aura_route_renders(self):
        set_request(method="GET", path="/aura")
        response = get_response()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"aura-frontend-root", response.get_data())

    def test_deep_link_resolves_to_same_page(self):
        # website_route_rules forwards /aura/<anything> to the SPA shell.
        set_request(method="GET", path="/aura/deals")
        response = get_response()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"aura-frontend-root", response.get_data())
