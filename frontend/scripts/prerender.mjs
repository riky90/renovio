// Prerender delle pagine pubbliche e file per i crawler (build, dopo `vite build`
// e `vite build --ssr`). Scrive:
//   dist/<path>/index.html  HTML statico con contenuto e metadati per pagina
//   dist/sitemap.xml        le pagine indicizzabili
//   dist/robots.txt         regole per i crawler, AI compresi, e la sitemap
//   dist/llms.txt           riassunto del sito per gli assistenti AI
//
// Il dominio viene da VITE_SITE_URL (provvisorio: cambia senza toccare codice).

import { readFile, writeFile, mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const radice = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dist = path.join(radice, "dist");
const server = path.join(radice, "dist-server");
const SITE_URL = (process.env.VITE_SITE_URL || "https://stima-lovat.vercel.app").replace(/\/$/, "");

const { render, PAGINE_PUBBLICHE, llmsTxt } = await import(pathToFileURL(path.join(server, "entry-server.js")).href);
const template = await readFile(path.join(dist, "index.html"), "utf8");

function inietta(html, head) {
  let pagina = template.replace('<div id="root"></div>', `<div id="root">${html}</div>`);
  if (head) {
    pagina = pagina
      .replace(/<title>[\s\S]*?<\/title>/, `<title>${head.titolo.replace(/</g, "&lt;")}</title>`)
      .replace(/<!--seo:inizio-->[\s\S]*?<!--seo:fine-->/, head.tags);
  }
  return pagina;
}

for (const url of PAGINE_PUBBLICHE) {
  const { html, head } = await render(url);
  if (!head) throw new Error(`La pagina ${url} non dichiara i metadati (<Seo>)`);
  const destinazione = url === "/" ? path.join(dist, "index.html") : path.join(dist, url, "index.html");
  await mkdir(path.dirname(destinazione), { recursive: true });
  await writeFile(destinazione, inietta(html, head));
  console.log(`prerender ${url}`);
}

// Il guscio delle rotte dell'app (account, admin): niente contenuto, fuori
// dall'indice; Vercel lo serve con i rewrite di vercel.json. Ogni altro URL
// inesistente riceve 404.html, servita da Vercel con lo stato 404.
const { html: html404, head: head404 } = await render("/pagina-che-non-esiste");
await writeFile(path.join(dist, "app.html"), inietta("", head404));
await writeFile(path.join(dist, "404.html"), inietta(html404, head404));

const oggi = new Date().toISOString().slice(0, 10);
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${PAGINE_PUBBLICHE.map((u) => `  <url><loc>${SITE_URL}${u}</loc><lastmod>${oggi}</lastmod></url>`).join("\n")}
</urlset>
`;
await writeFile(path.join(dist, "sitemap.xml"), sitemap);

const robots = `# Renovio: contenuti pubblici aperti a motori di ricerca e assistenti AI.
User-agent: *
Allow: /
Disallow: /admin
Disallow: /le-mie-stime
Disallow: /impostazioni
Disallow: /dettaglio-pro
Disallow: /nuova-stima
Disallow: /reimposta-password
Disallow: /passa-a-pro

Sitemap: ${SITE_URL}/sitemap.xml
`;
await writeFile(path.join(dist, "robots.txt"), robots);
await writeFile(path.join(dist, "llms.txt"), llmsTxt(SITE_URL));

await rm(server, { recursive: true, force: true });
console.log(`sitemap, robots.txt e llms.txt per ${SITE_URL}`);
