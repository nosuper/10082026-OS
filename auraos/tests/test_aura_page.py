"""The /aura route must serve the built frappe-ui page.

Requires `npm run build` in frontend/ to have run first (CI builds it
before the site tests; see .github/workflows/ci.yml).
"""

import os
import re

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

    def test_aura_assets_are_servable(self):
        # A page shell that serves while its JS/CSS 404 renders as a
        # blank white page — assert every referenced asset resolves on
        # disk under sites/assets (i.e. the app assets symlink exists).
        set_request(method="GET", path="/aura")
        html = get_response().get_data().decode()
        asset_paths = re.findall(r'"(/assets/[^"]+)"', html)
        self.assertTrue(asset_paths, "aura.html references no /assets/ files")
        sites_dir = os.path.abspath(os.path.join(frappe.get_site_path(), ".."))
        for path in asset_paths:
            fs_path = os.path.join(sites_dir, path.lstrip("/"))
            self.assertTrue(
                os.path.exists(fs_path),
                f"{path} not servable: {fs_path} missing (assets symlink?)",
            )

    def test_page_injects_rendered_csrf_token(self):
        # Without a CSRF token in the shell, every frappe-ui POST from
        # the SPA fails for logged-in users (and the T2 guest-redirect
        # turned that into an infinite reload loop). Assert the Jinja
        # tag is present in the source and actually rendered.
        set_request(method="GET", path="/aura")
        html = get_response().get_data().decode()
        self.assertIn("window.csrf_token", html)
        self.assertNotIn(
            "{{ csrf_token }}", html, "csrf_token Jinja tag not rendered"
        )

    def test_deep_link_resolves_to_same_page(self):
        # website_route_rules forwards /aura/<anything> to the SPA shell.
        set_request(method="GET", path="/aura/deals")
        response = get_response()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"aura-frontend-root", response.get_data())
