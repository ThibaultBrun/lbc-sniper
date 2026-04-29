#!/usr/bin/env node
/**
 * Post-build script : pour chaque annonce VTT active en base, on genere un
 * fichier HTML statique <dist>/ad/<id>/index.html avec :
 *  - title + meta description specifiques (title accroche, prix, modele)
 *  - Open Graph + Twitter cards (preview reseau social)
 *  - JSON-LD Product (= Google reconnait que c'est une annonce produit)
 *  - le contenu textuel inline pour que Googlebot lise sans executer le JS
 *  - le bundle Vue qui s'hydrate par-dessus pour l'interactivite
 *
 * On genere aussi /sitemap.xml et /robots.txt.
 *
 * Lance par GitHub Actions apres `npm run build`.
 *
 * Variables d'env attendues:
 *   VITE_SUPABASE_URL
 *   VITE_SUPABASE_ANON_KEY
 *   SITE_URL  (optionnel, defaut: https://trouve-ton-vtt.pista.bike)
 */
import { createClient } from "@supabase/supabase-js";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DIST = path.resolve(__dirname, "..", "dist");
const SITE_URL = process.env.SITE_URL || "https://trouve-ton-vtt.pista.bike";

const SUPABASE_URL = process.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = process.env.VITE_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error("Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY env vars");
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function trim(s, n) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function tierLabel(score) {
  if (score == null) return "À analyser";
  if (score >= 85) return "Excellente affaire";
  if (score >= 70) return "Bonne affaire";
  if (score >= 50) return "Prix du marché";
  if (score >= 30) return "Un peu cher";
  return "Surévalué";
}

function adTitle(ad) {
  const brand = ad.brand || "";
  const model = ad.model || "";
  const year = ad.year ? ` ${ad.year}` : "";
  const price = ad.current_price ? ` ${Math.round(ad.current_price)}€` : "";
  const desc = [brand, model].filter(Boolean).join(" ").trim() || ad.subject;
  return trim(`${desc}${year}${price}`, 60);
}

function adDescription(ad) {
  const score = ad.deal_score ?? 0;
  const label = tierLabel(score);
  const market = ad.estimated_market_eur;
  const discount =
    market && ad.current_price && market > ad.current_price
      ? ` (${Math.round(((market - ad.current_price) / market) * 100)}% sous la cote)`
      : "";
  const cat = ad.category_label === "VTT DH" ? "VTT de descente" : "VTT enduro";
  const city = ad.city ? ` à ${ad.city}` : "";
  return trim(
    `${cat}${city} : ${label}, score ${score}/100${discount}. Analyse IA gratuite : prix de marché, points forts, points de vigilance.`,
    155,
  );
}

function adKeywords(ad) {
  const tokens = new Set();
  if (ad.brand) tokens.add(ad.brand.toLowerCase());
  if (ad.model) tokens.add(ad.model.toLowerCase());
  if (ad.category_label) tokens.add(ad.category_label.toLowerCase());
  if (ad.electric) {
    tokens.add("électrique");
    tokens.add("vae");
    tokens.add("vtt électrique");
    tokens.add("e-mtb");
  }
  if (ad.year) tokens.add(String(ad.year));
  // Expressions commerciales courantes que les utilisateurs tapent dans Google
  tokens.add("vtt occasion");
  tokens.add("vtt d'occasion");
  tokens.add("bonne affaire");
  tokens.add("bonne affaire vtt");
  tokens.add("vtt pas cher");
  tokens.add("analyse ia");
  tokens.add("cote vtt");
  tokens.add("leboncoin");
  return Array.from(tokens).join(", ");
}

// JSON-LD Product schema pour Google Shopping / Rich results
function jsonLdProduct(ad) {
  const data = {
    "@context": "https://schema.org/",
    "@type": "Product",
    name: trim(ad.subject || "VTT", 100),
    description: trim(ad.body || ad.subject || "", 500),
    image: ad.image_url || undefined,
    brand: ad.brand ? { "@type": "Brand", name: ad.brand } : undefined,
    offers: {
      "@type": "Offer",
      url: `${SITE_URL}/ad/${ad.id}`,
      priceCurrency: "EUR",
      price: ad.current_price ? String(ad.current_price) : undefined,
      itemCondition: "https://schema.org/UsedCondition",
      availability: "https://schema.org/InStock",
      seller: { "@type": "Organization", name: "Leboncoin (via Trouve Ton VTT)" },
    },
    aggregateRating: ad.deal_score != null
      ? {
          "@type": "AggregateRating",
          ratingValue: String(Math.round(ad.deal_score / 10)),
          bestRating: "10",
          ratingCount: "1",
          reviewCount: "1",
        }
      : undefined,
  };
  // Strip undefined fields
  return JSON.stringify(data, (_, v) => (v === undefined ? undefined : v));
}

// ------------------------------------------------------------------
// Fetch active ads
// ------------------------------------------------------------------

async function fetchAds() {
  const { data, error } = await supabase
    .from("ads")
    .select(
      "id, subject, body, current_price, image_url, city, category_label, brand, model, year, electric, deal_score, estimated_market_eur, last_seen_at",
    )
    .eq("is_active", true)
    .in("category_label", ["VTT enduro", "VTT DH"])
    .order("deal_score", { ascending: false, nullsFirst: false })
    .limit(2000);
  if (error) {
    console.error("Failed to fetch ads:", error);
    process.exit(1);
  }
  return data || [];
}

// ------------------------------------------------------------------
// Patch the original index.html for each ad
// ------------------------------------------------------------------

function buildAdHtml(template, ad) {
  const title = `${adTitle(ad)} — Trouve Ton VTT`;
  const description = adDescription(ad);
  const keywords = adKeywords(ad);
  const url = `${SITE_URL}/ad/${ad.id}`;
  const image = ad.image_url || `${SITE_URL}/og-default.png`;
  const inlineContent = `
    <article style="display:none">
      <h1>${escapeHtml(adTitle(ad))}</h1>
      <p>${escapeHtml(description)}</p>
      ${ad.body ? `<div>${escapeHtml(trim(ad.body, 1500))}</div>` : ""}
      ${ad.current_price ? `<p>Prix : ${ad.current_price} €</p>` : ""}
      ${ad.estimated_market_eur ? `<p>Cote estimée : ${ad.estimated_market_eur} €</p>` : ""}
      ${ad.city ? `<p>Localisation : ${escapeHtml(ad.city)}</p>` : ""}
    </article>
  `.trim();

  // Replace title
  let html = template.replace(
    /<title>.*?<\/title>/,
    `<title>${escapeHtml(title)}</title>`,
  );

  // Inject meta tags + JSON-LD just before </head>
  const metaBlock = `
    <meta name="description" content="${escapeHtml(description)}" />
    <meta name="keywords" content="${escapeHtml(keywords)}" />
    <link rel="canonical" href="${url}" />
    <meta property="og:type" content="product" />
    <meta property="og:title" content="${escapeHtml(title)}" />
    <meta property="og:description" content="${escapeHtml(description)}" />
    <meta property="og:image" content="${escapeHtml(image)}" />
    <meta property="og:url" content="${url}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="${escapeHtml(title)}" />
    <meta name="twitter:description" content="${escapeHtml(description)}" />
    <meta name="twitter:image" content="${escapeHtml(image)}" />
    <script type="application/ld+json">${jsonLdProduct(ad)}</script>
  `.trim();

  html = html.replace("</head>", `${metaBlock}</head>`);

  // Inject hidden inline content into <div id="app"></div> so Googlebot
  // sees the textual content even without executing JS. Vue will replace
  // this content on hydration anyway.
  html = html.replace(
    /<div id="app"><\/div>/,
    `<div id="app">${inlineContent}</div>`,
  );

  return html;
}

function buildHomeHtml(template, ads) {
  const title = "Trouve Ton VTT — Bonnes affaires VTT enduro et descente, analysées par IA";
  const description = `Découvre les meilleures affaires VTT du moment sur Le Bon Coin. ${ads.length} annonces analysées automatiquement par IA : score de prix, points forts, points de vigilance. Gratuit, sans inscription.`;
  const url = SITE_URL;

  // SEO content : un H1 + un bref pitch + les 12 meilleures affaires en clair
  const top = ads.filter((a) => (a.deal_score ?? 0) >= 70).slice(0, 12);
  const topList = top
    .map(
      (a) =>
        `<li><a href="${SITE_URL}/ad/${a.id}">${escapeHtml(adTitle(a))}</a> — ${tierLabel(a.deal_score)}, score ${a.deal_score}/100${a.city ? `, ${escapeHtml(a.city)}` : ""}</li>`,
    )
    .join("\n");

  const inlineContent = `
    <article style="display:none">
      <h1>Trouve Ton VTT — Les meilleures affaires VTT enduro et descente</h1>
      <p>Une intelligence artificielle analyse chaque annonce VTT publiée sur Le Bon Coin et te dit instantanément si c'est une bonne affaire ou pas. Brand, modèle, année, prix marché, points forts et points de vigilance — tout est expliqué en quelques secondes.</p>
      <h2>Pour qui ?</h2>
      <p>Pour quiconque cherche un VTT d'occasion (enduro, all-mountain, descente, électrique) sans passer des heures à éplucher des centaines d'annonces et sans se faire avoir sur le prix.</p>
      <h2>Top 12 affaires du moment</h2>
      <ul>${topList}</ul>
      <p>Service gratuit, sans inscription nécessaire. Connecte-toi avec Google pour ajouter des favoris et recevoir des alertes mail quand de nouvelles bonnes affaires correspondent à tes critères.</p>
    </article>
  `.trim();

  let html = template.replace(/<title>.*?<\/title>/, `<title>${escapeHtml(title)}</title>`);

  const metaBlock = `
    <meta name="description" content="${escapeHtml(description)}" />
    <meta name="keywords" content="vtt occasion, vtt d'occasion, vtt enduro, vtt enduro occasion, vtt dh, vtt descente, vtt all mountain, vtt électrique, vae, e-mtb, leboncoin, bonne affaire vtt, vtt pas cher, analyse ia, cote vtt, lapierre, specialized, canyon, commencal, santa cruz, trek" />
    <link rel="canonical" href="${url}" />
    <meta property="og:type" content="website" />
    <meta property="og:title" content="${escapeHtml(title)}" />
    <meta property="og:description" content="${escapeHtml(description)}" />
    <meta property="og:url" content="${url}" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="${escapeHtml(title)}" />
    <meta name="twitter:description" content="${escapeHtml(description)}" />
  `.trim();

  html = html.replace("</head>", `${metaBlock}</head>`);
  html = html.replace(
    /<div id="app"><\/div>/,
    `<div id="app">${inlineContent}</div>`,
  );

  return html;
}

// ------------------------------------------------------------------
// Sitemap + robots.txt
// ------------------------------------------------------------------

function buildSitemap(ads) {
  const today = new Date().toISOString().slice(0, 10);
  const urls = [
    { loc: SITE_URL, priority: 1.0, changefreq: "daily" },
    { loc: `${SITE_URL}/a-propos`, priority: 0.5, changefreq: "monthly" },
    { loc: `${SITE_URL}/mentions-legales`, priority: 0.3, changefreq: "yearly" },
    { loc: `${SITE_URL}/confidentialite`, priority: 0.3, changefreq: "yearly" },
    { loc: `${SITE_URL}/cgu`, priority: 0.3, changefreq: "yearly" },
    ...ads.map((a) => ({
      loc: `${SITE_URL}/ad/${a.id}`,
      priority: 0.7,
      changefreq: "weekly",
      lastmod: a.last_seen_at ? a.last_seen_at.slice(0, 10) : today,
    })),
  ];

  const body = urls
    .map(
      (u) =>
        `  <url>\n    <loc>${u.loc}</loc>\n    <changefreq>${u.changefreq}</changefreq>\n    <priority>${u.priority}</priority>${u.lastmod ? `\n    <lastmod>${u.lastmod}</lastmod>` : ""}\n  </url>`,
    )
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${body}
</urlset>`;
}

function buildRobotsTxt() {
  return `User-agent: *
Allow: /
Disallow: /secret
Disallow: /favoris

Sitemap: ${SITE_URL}/sitemap.xml
`;
}

// ------------------------------------------------------------------
// Main
// ------------------------------------------------------------------

async function main() {
  console.log("=== Prerender ===");
  console.log(`SITE_URL: ${SITE_URL}`);

  const indexPath = path.join(DIST, "index.html");
  const template = await fs.readFile(indexPath, "utf8");

  const ads = await fetchAds();
  console.log(`Fetched ${ads.length} active VTT ads`);

  // Patch home with SEO content
  const homeHtml = buildHomeHtml(template, ads);
  await fs.writeFile(indexPath, homeHtml);
  // Same for 404.html (SPA fallback) so deep links keep meta home
  await fs.writeFile(path.join(DIST, "404.html"), homeHtml);
  console.log("✓ index.html + 404.html patched with SEO meta tags");

  // Generate one HTML per ad
  let count = 0;
  for (const ad of ads) {
    const dir = path.join(DIST, "ad", String(ad.id));
    await fs.mkdir(dir, { recursive: true });
    const html = buildAdHtml(template, ad);
    await fs.writeFile(path.join(dir, "index.html"), html);
    count++;
  }
  console.log(`✓ Generated ${count} per-ad HTML files`);

  // Sitemap
  await fs.writeFile(path.join(DIST, "sitemap.xml"), buildSitemap(ads));
  console.log("✓ sitemap.xml");

  // Robots.txt
  await fs.writeFile(path.join(DIST, "robots.txt"), buildRobotsTxt());
  console.log("✓ robots.txt");

  console.log("=== Prerender done ===");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
