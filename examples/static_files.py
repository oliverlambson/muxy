# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "muxy[compress]",
#     "granian[uvloop]>=2.6.0,<3.0.0",
#     "httpx>=0.28.1,<0.29.0",
# ]
#
# [tool.uv.sources]
# muxy = { path = "../", editable = true }
# ///
"""Static files app demo.

Shows usage of the static_files app for serving pre-compressed static files
with content-addressable URLs. Demonstrates:
- Pre-compression at startup (zstd, brotli, gzip)
- Content negotiation based on Accept-Encoding
- Hash-based cache-busting URLs
- Using url_path() for template integration
"""

import asyncio
import logging
import sys
import tempfile
from pathlib import Path

import httpx
import uvloop
from granian.server.embed import Server

from muxy import Router
from muxy.apps.static_files import static_files
from muxy.rsgi import HTTPProtocol, HTTPScope

ADDRESS = "127.0.0.1"
PORT = 8000


async def main() -> None:
    """Script entrypoint"""
    logging.basicConfig(level=logging.INFO)

    # Create temporary static files directory with sample files
    with tempfile.TemporaryDirectory() as tmpdir:
        static_dir = Path(tmpdir)
        create_sample_files(static_dir)

        # Create static files app - this pre-compresses files at startup
        # The prefix parameter handles stripping /static from incoming requests
        # and prepending it to url_path() results
        static_app, url_path = static_files(static_dir, prefix="/static")

        # Show the generated URLs
        print("--- Generated URLs ---", file=sys.stderr)
        print(f"  styles.css -> {url_path('styles.css')}", file=sys.stderr)
        print(f"  app.js -> {url_path('app.js')}", file=sys.stderr)
        print(f"  lib/utils.js -> {url_path('lib/utils.js')}", file=sys.stderr)
        print(f"  logo.png -> {url_path('logo.png')}", file=sys.stderr)
        print(file=sys.stderr)

        # Show compressed file variants created
        print("--- Compressed variants created ---", file=sys.stderr)
        for f in sorted(static_dir.rglob("*")):
            if f.is_file():
                print(
                    f"  {f.relative_to(static_dir)} ({f.stat().st_size} bytes)",
                    file=sys.stderr,
                )
        print(file=sys.stderr)

        # Set up router
        router = Router()
        router.not_found(not_found)
        router.method_not_allowed(method_not_allowed)
        router.get("/static/{path...}", static_app)
        router.get("/", home(url_path))

        # Run server and make requests
        task = asyncio.create_task(serve(router))
        await asyncio.sleep(0.1)
        await requests(url_path)
        task.cancel()


def create_sample_files(static_dir: Path) -> None:
    """Create sample static files for the demo."""
    # CSS file (compressible)
    css = static_dir / "styles.css"
    css.write_text(
        """\
body {
    font-family: system-ui, sans-serif;
    background: #f5f5f5;
    color: #333;
    margin: 0;
    padding: 20px;
}
h1 { color: #0066cc; }
.container { max-width: 800px; margin: 0 auto; }
"""
        + "/* padding */" * 100  # Make it large enough to compress well
    )

    # JavaScript file (compressible)
    js = static_dir / "app.js"
    js.write_text(
        """\
console.log('App loaded');
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM ready');
});
"""
        + "// padding\n" * 100
    )

    # Nested JavaScript file
    lib = static_dir / "lib"
    lib.mkdir()
    utils = lib / "utils.js"
    utils.write_text(
        """\
export function formatDate(d) { return d.toISOString(); }
export function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
"""
        + "// padding\n" * 100
    )

    # Binary file (non-compressible)
    logo = static_dir / "logo.png"
    logo.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)


async def not_found(_scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(404, [("content-type", "text/plain")], "Not found")


async def method_not_allowed(_scope: HTTPScope, proto: HTTPProtocol) -> None:
    proto.response_str(405, [("content-type", "text/plain")], "Method not allowed")


def home(url_path: callable) -> callable:
    """Home page that demonstrates using url_path for template integration."""

    async def handler(_scope: HTTPScope, proto: HTTPProtocol) -> None:
        css_url = url_path("styles.css")
        js_url = url_path("app.js")

        html = f"""\
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="{css_url}">
</head>
<body>
    <div class="container">
        <h1>Static Files Demo</h1>
        <p>This page uses hash-based static file URLs for optimal caching.</p>
        <p>CSS: <code>{css_url}</code></p>
        <p>JS: <code>{js_url}</code></p>
    </div>
    <script src="{js_url}"></script>
</body>
</html>
"""
        proto.response_str(200, [("content-type", "text/html")], html)

    return handler


async def serve(router: Router) -> None:
    """Runtime for the RSGI-app."""
    server = Server(router, address=ADDRESS, port=PORT, log_access=True)
    try:
        await server.serve()
    except asyncio.CancelledError:
        await server.shutdown()


async def requests(url_path: callable) -> None:
    """Make requests demonstrating content negotiation."""
    base_url = f"http://{ADDRESS}:{PORT}"

    async with httpx.AsyncClient(base_url=base_url) as client:
        css_url = url_path("styles.css")

        print("--- Content negotiation demo ---", file=sys.stderr)

        # Request with zstd
        response = await client.get(css_url, headers={"accept-encoding": "zstd"})
        print("Accept-Encoding: zstd", file=sys.stderr)
        print(f"  Status: {response.status_code}", file=sys.stderr)
        print(
            f"  Content-Encoding: {response.headers.get('content-encoding', 'none')}",
            file=sys.stderr,
        )
        print(
            f"  Content-Length: {response.headers.get('content-length')}",
            file=sys.stderr,
        )
        print(
            f"  Cache-Control: {response.headers.get('cache-control')}", file=sys.stderr
        )
        print(file=sys.stderr)

        # Request with brotli
        response = await client.get(css_url, headers={"accept-encoding": "br"})
        print("Accept-Encoding: br", file=sys.stderr)
        print(
            f"  Content-Encoding: {response.headers.get('content-encoding', 'none')}",
            file=sys.stderr,
        )
        print(
            f"  Content-Length: {response.headers.get('content-length')}",
            file=sys.stderr,
        )
        print(file=sys.stderr)

        # Request with gzip (httpx default)
        response = await client.get(css_url, headers={"accept-encoding": "gzip"})
        print("Accept-Encoding: gzip", file=sys.stderr)
        print(
            f"  Content-Encoding: {response.headers.get('content-encoding', 'none')}",
            file=sys.stderr,
        )
        print(
            f"  Content-Length: {response.headers.get('content-length')}",
            file=sys.stderr,
        )
        print(file=sys.stderr)

        # Request without compression
        response = await client.get(css_url, headers={"accept-encoding": "identity"})
        print("Accept-Encoding: identity (no compression)", file=sys.stderr)
        print(
            f"  Content-Encoding: {response.headers.get('content-encoding', 'none')}",
            file=sys.stderr,
        )
        print(
            f"  Content-Length: {response.headers.get('content-length')}",
            file=sys.stderr,
        )
        print(file=sys.stderr)

        # Test 404 for invalid hash
        response = await client.get("/static/styles.00000000.css")
        print(f"Invalid hash -> Status: {response.status_code}", file=sys.stderr)

        # Test 404 for missing hash
        response = await client.get("/static/styles.css")
        print(f"Missing hash -> Status: {response.status_code}", file=sys.stderr)


if __name__ == "__main__":
    uvloop.run(main())
