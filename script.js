function normalizeUrl(url) {
  if (!url) return "";
  url = url.trim();
  if (!/^https?:\/\//i.test(url)) url = "https://" + url;
  return url;
}

function addParam(url, param) {
  if (!param) return url;
  const p = param.trim();
  if (!p) return url;

  const u = new URL(url);
  // param dạng "a=b" hoặc "a=b&c=d"
  p.split("&").forEach(kv => {
    const [k, v = ""] = kv.split("=");
    if (k) u.searchParams.set(k, v);
  });
  return u.toString();
}

function parseLines(text) {
  return text
    .split("\n")
    .map(l => l.trim())
    .filter(Boolean)
    .map(line => {
      // format: "label url" hoặc chỉ "url"
      const parts = line.split(/\s+/);
      if (parts.length === 1) return { label: "", url: normalizeUrl(parts[0]) };
      const label = parts[0];
      const url = normalizeUrl(parts.slice(1).join(" "));
      return { label, url };
    });
}

function preview() {
  const input = document.getElementById("input").value;
  const append = document.getElementById("append").value;

  const items = parseLines(input).map(x => ({ ...x, url: addParam(x.url, append) }));
  document.getElementById("count").textContent = `Results: ${items.length} item(s)`;

  const root = document.getElementById("results");
  root.innerHTML = "";

  items.forEach(({ label, url }) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      ${label ? `<div class="tag">${label}</div>` : ""}
      <div class="mono">URL<br>${url}</div>
      <div class="muted" style="margin-top:8px;">
        Mở link để xem preview (OG image/text hiển thị đúng trong app/chat).
      </div>
      <div style="margin-top:8px;">
        <a href="https://metatags.io/?url=${encodeURIComponent(url)}" target="_blank" rel="noopener noreferrer">Open (OG Preview)</a>
      </div>
    `;
    root.appendChild(card);
  });
}

document.getElementById("btn").addEventListener("click", preview);
