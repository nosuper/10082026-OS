"""The /aura-next route must serve the built React page.

Requires `npm run build` in frontend-react/ to have run first (CI builds
it before the site tests; see .github/workflows/ci.yml).

This file tested /aura until #103. The four things it asserts were never
about the frappe-ui app specifically - a shell that renders, assets that
actually resolve, a CSRF token that reaches the browser, and deep links
that land on the shell - and /aura-next had no equivalent test of its
own. Deleting the Vue app would have deleted the only assertions
covering any of them, which is why this moved rather than went.
"""

import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response


class TestAuraNextPage(FrappeTestCase):
    def test_aura_next_route_renders(self):
        set_request(method="GET", path="/aura-next")
        response = get_response()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"aura-next-root", response.get_data())

    def test_aura_next_assets_are_servable(self):
        # A page shell that serves while its JS/CSS 404 renders as a
        # blank white page - assert every referenced asset resolves on
        # disk under sites/assets (i.e. the app assets symlink exists).
        set_request(method="GET", path="/aura-next")
        html = get_response().get_data().decode()
        asset_paths = re.findall(r'"(/assets/[^"]+)"', html)
        self.assertTrue(asset_paths, "aura-next.html references no /assets/ files")
        sites_dir = os.path.abspath(os.path.join(frappe.get_site_path(), ".."))
        for path in asset_paths:
            fs_path = os.path.join(sites_dir, path.lstrip("/"))
            self.assertTrue(
                os.path.exists(fs_path),
                f"{path} not servable: {fs_path} missing (assets symlink?)",
            )

    def test_page_injects_rendered_csrf_token(self):
        # Without a CSRF token in the shell, every POST from the SPA
        # fails for logged-in users (and the T2 guest-redirect turned
        # that into an infinite reload loop). Assert the Jinja tag is
        # present in the source and actually rendered.
        set_request(method="GET", path="/aura-next")
        html = get_response().get_data().decode()
        self.assertIn("window.csrf_token", html)
        self.assertNotIn(
            "{{ csrf_token }}", html, "csrf_token Jinja tag not rendered"
        )

    def test_deep_link_resolves_to_same_page(self):
        # website_route_rules forwards /aura-next/<anything> to the SPA
        # shell, which is what lets the router own the path.
        set_request(method="GET", path="/aura-next/deals")
        response = get_response()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"aura-next-root", response.get_data())

    def test_the_retired_route_no_longer_serves(self):
        """/aura was the rollback path and #103 retired it.

        Asserted rather than assumed: removing a route rule and leaving
        the built page on disk in a container would still serve it, and
        the difference is invisible from the repo. A 404 here is the
        whole of what "retired" means.
        """
        set_request(method="GET", path="/aura")
        self.assertEqual(get_response().status_code, 404)
