console.log("script.js loaded");
const OG_WORKER =
  "https://og-proxy.emmanguyen2804.workers.dev/?url=";
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
  // param dạng "a=b" hoặc "a=b&c=d" nha
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
      <div class="og muted" style="margin-top:8px;">Đang load OG preview...</div>
    `;

    root.appendChild(card);

    fetch(OG_WORKER + encodeURIComponent(url))
      .then(res => res.json())
      .then(og => {
        const box = card.querySelector(".og");
        if (!og || (!og.title && !og.description && !og.image)) {
          box.innerHTML = `<span class="error">Không lấy được OG</span>`;
          return;
        }
        box.innerHTML = `
          ${og.title ? `<div><b>og:title</b><br>${og.title}</div>` : ""}
          ${og.description ? `<div style="margin-top:4px;"><b>og:description</b><br>${og.description}</div>` : ""}
          ${og.image ? `<img src="${og.image}" style="max-width:100%;margin-top:8px;border-radius:8px;" />` : ""}
        `;
      })
      .catch(() => {
        card.querySelector(".og").innerHTML = `<span class="error">OG error</span>`;
      });
  });
}


document.getElementById("btn").addEventListener("click", preview);
