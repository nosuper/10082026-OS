import frappe


def get_context(context):
    # The React SPA shell is Jinja-rendered; hand it a CSRF token so the app
    # can make POST calls (saves, inserts, logout) as a logged-in user.
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()
    context.csrf_token = csrf_token

    # **And therefore this page must never be cached.** The token above
    # belongs to one session, and it is baked into the HTML - so a cached
    # copy is one visitor's token handed to the next. Frappe's website page
    # cache did exactly that on production: `/aura-next` came back with
    # `X-From-Cache: True` and the same token every time, a Guest render
    # served to signed-in people, and every POST they made failed with
    # `CSRFTokenError: Invalid Request`. The app looked fine and did nothing,
    # including log out, because logging out is a POST too.
    #
    # There is no version of this page worth caching. It is a shell of a few
    # kilobytes whose entire job is to carry a per-session token and point at
    # hashed asset files, and those assets are cached properly by their
    # filenames.
    context.no_cache = 1
    return context
