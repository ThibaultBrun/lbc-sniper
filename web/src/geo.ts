// Format compact d'une commune dans web/public/communes/<lettre>.json :
// [nom, code_insee, lng, lat]
export type CommuneRecord = [string, string, number, number];

export type Commune = {
  name: string;
  insee: string;
  lat: number;
  lng: number;
};

function recordToCommune(r: CommuneRecord): Commune {
  return { name: r[0], insee: r[1], lng: r[2], lat: r[3] };
}

/** Normalise une chaîne pour l'autocomplete : retire accents + minuscules. */
export function normalize(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

const cache = new Map<string, Commune[]>();
const inflight = new Map<string, Promise<Commune[]>>();

/** Charge les communes commencant par la lettre indiquee (cache). */
export async function loadCommunesByLetter(letter: string): Promise<Commune[]> {
  const key = normalize(letter)[0] ?? "";
  if (!key.match(/[a-z]/)) return [];
  if (cache.has(key)) return cache.get(key)!;
  if (inflight.has(key)) return inflight.get(key)!;
  const p = (async () => {
    const res = await fetch(`/communes/${key}.json`);
    if (!res.ok) {
      cache.set(key, []);
      return [];
    }
    const data = (await res.json()) as CommuneRecord[];
    const list = data.map(recordToCommune);
    cache.set(key, list);
    return list;
  })();
  inflight.set(key, p);
  try {
    return await p;
  } finally {
    inflight.delete(key);
  }
}

/** Recherche d'une commune par début de nom. */
export async function searchCommunes(query: string, max = 20): Promise<Commune[]> {
  const q = normalize(query);
  if (q.length < 2) return [];
  const list = await loadCommunesByLetter(q);
  return list
    .filter((c) => normalize(c.name).startsWith(q))
    .slice(0, max);
}

/** Distance Haversine en km entre 2 points. */
export function haversineKm(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const R = 6371; // rayon Terre en km
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

/** Demande la position courante du navigateur (Promise). */
export function getCurrentPosition(): Promise<{ lat: number; lng: number }> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation non disponible dans ce navigateur"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => reject(err),
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60000 },
    );
  });
}
