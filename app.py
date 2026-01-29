from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import os

app = Flask(__name__)

# UI theo style "cũ": đơn giản, card, border, radius, font system
PAGE = """
<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OneLink OG Batch Preview</title>
  <style>
    body { font-family: -apple-system, system-ui, Arial; margin: 16px; }
    h1 { font-size: 22px; margin: 0 0 10px; }
    .hint { color:#666; margin: 0 0 10px; font-size: 13px; }
    textarea { width:100%; padding:10px; font-size:14px; height:220px; box-sizing:border-box; }
    input { padding:10px; font-size:14px; width: 320px; max-width: 100%; box-sizing:border-box; }
    button { padding:10px 14px; font-size:16px; margin-top:8px; cursor:pointer; }
    .row { display:flex; gap:10px; flex-wrap:wrap; margin-top:10px; align-items:center; }
    .card { border:1px solid #ddd; border-radius:12px; padding:12px; margin-top:14px; }
    .label { color:#666; font-size:13px; margin-top:8px; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size:12px; word-break:break-all; }
    img { max-width:100%; border-radius:10px; border:1px solid #eee; }
    .pill { display:inline-block; padding:2px 8px; border:1px solid #ddd; border-radius:999px; font-size:12px; }
    .err { color:#b00020; }
    .muted { color:#666; }
    .grid { display:grid; grid-template-columns: 1fr; gap: 12px; }
    @media (min-width: 980px) {
      .grid { grid-template-columns: 1fr 1fr; }
    }
  </style>
</head>
<body>
  <h1>OneLink OG Batch Preview</h1>
  <p class="hint">Dán nhiều link (mỗi dòng 1 link, có thể kèm label). Ví dụ: <span class="mono">en https://...</span></p>

  <form method="POST">
    <textarea name="lines" placeholder="en https://...
kr https://...">{{ lines|default('') }}</textarea>

    <div class="row">
      <div>
        <div class="hint" style="margin:0 0 6px;">Optional: append param to ALL URLs</div>
        <input name="append_param" placeholder="af_country=KR (or leave empty)" value="{{ append_param|default('') }}" />
      </div>
      <button type="submit">Preview All</button>
    </div>
  </form>

  {% if results is not none %}
    <p class="hint">Results: {{ results|length }} item(s)</p>

    <div class="grid">
    {% for r in results %}
      <div class="card">
        <div><span class="pill">{{ r.label }}</span></div>

        <div class="label">URL</div>
        <div class="mono">{{ r.url }}</div>

        {% if r.error %}
          <div class="label err">ERROR</div>
          <div class="mono err">{{ r.error }}</div>
        {% else %}
          <div class="label">og:title</div>
          <div><b>{{ r.og_title or '-' }}</b></div>

          <div class="label">og:description</div>
          <div>{{ r.og_desc or '-' }}</div>

          <div class="label">og:image</div>
          {% if r.og_image %}
            <img src="{{ r.og_image }}" alt="og:image" />
            <div class="mono muted" style="margin-top:6px;">{{ r.og_image }}</div>
          {% else %}
            <div class="muted">-</div>
          {% endif %}
        {% endif %}
      </div>
    {% endfor %}
    </div>
  {% endif %}
</body>
</html>
"""

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)

def normalize_url(u: str) -> str:
    u = u.strip().strip("<>").strip()
    if not u:
        return ""
    if not u.startswith("http://") and not u.startswith("https://"):
        u = "https://" + u
    return u

def append_query(url: str, kv: str) -> str:
    """
    kv format: key=value (single pair). If empty -> return original.
    """
    kv = (kv or "").strip()
    if not kv or "=" not in kv:
        return url

    key, val = kv.split("=", 1)
    key, val = key.strip(), val.strip()
    if not key:
        return url

    p = urlparse(url)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q[key] = val
    new_query = urlencode(q, doseq=True)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))

def parse_lines(raw: str):
    """
    Each line:
      - "label https://...."
      - or just "https://...." (auto label = index)
    """
    items = []
    for idx, line in enumerate((raw or "").splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        parts = s.split()
        if len(parts) >= 2 and parts[1].startswith(("http://", "https://")):
            label = parts[0]
            url = " ".join(parts[1:]).strip()
        else:
            label = f"#{idx}"
            url = s
        items.append((label, normalize_url(url)))
    return items

def fetch_og(label: str, url: str, append_param: str):
    try:
        target = append_query(url, append_param)

        headers = {
            "User-Agent": DEFAULT_UA,
            # nếu mày muốn “đẩy theo ngôn ngữ” nhanh: có thể map theo label sau này
            "Accept-Language": "en-US,en;q=0.9",
        }

        resp = requests.get(target, headers=headers, timeout=12, allow_redirects=True)
        final_url = resp.url

        soup = BeautifulSoup(resp.text, "html.parser")

        def og(name):
            tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
            return (tag.get("content").strip() if tag and tag.get("content") else "")

        og_title = og("og:title")
        og_desc = og("og:description")
        og_image = og("og:image")

        # fallback (trường hợp og:title trống)
        if not og_title:
            t = soup.find("title")
            og_title = t.get_text(strip=True) if t else ""

        return {
            "label": label,
            "url": final_url,
            "og_title": og_title,
            "og_desc": og_desc,
            "og_image": og_image,
            "error": "",
        }
    except Exception as e:
        return {
            "label": label,
            "url": url,
            "og_title": "",
            "og_desc": "",
            "og_image": "",
            "error": str(e),
        }

@app.route("/", methods=["GET", "POST"])
def index():
    lines = ""
    append_param = ""
    results = None

    if request.method == "POST":
        lines = request.form.get("lines", "")
        append_param = request.form.get("append_param", "").strip()
        items = parse_lines(lines)

        # chạy song song để nhanh khi 10~20 link
        out = []
        with ThreadPoolExecutor(max_workers=min(10, max(1, len(items)))) as ex:
            futures = [ex.submit(fetch_og, label, url, append_param) for label, url in items]
            for f in as_completed(futures):
                out.append(f.result())

        # giữ thứ tự theo label input: sort theo thứ tự xuất hiện (label có thể trùng)
        # cách đơn giản: map label->index theo input
        order = {label: i for i, (label, _) in enumerate(items)}
        out.sort(key=lambda x: order.get(x["label"], 10**9))

        results = out

    return render_template_string(PAGE, lines=lines, append_param=append_param, results=results)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
