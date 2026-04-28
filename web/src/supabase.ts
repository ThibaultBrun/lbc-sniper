import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  throw new Error(
    "VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY doivent être définis dans web/.env",
  );
}

export const supabase = createClient(url, anonKey);

export async function getAdById(id: number): Promise<Ad | null> {
  const { data, error } = await supabase
    .from("ads")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  if (error) throw error;
  return (data as Ad | null) ?? null;
}

export type Ad = {
  id: number;
  watch_id: string;
  subject: string;
  body: string | null;
  url: string;
  image_url: string | null;
  city: string | null;
  zipcode: string | null;
  category_name: string | null;
  category_label: string | null;
  current_price: number | null;
  brand: string | null;
  model: string | null;
  year: number | null;
  frame_material: string | null;
  wheel_size: string | null;
  electric: boolean | null;
  size_label: string | null;
  condition_score: number | null;
  estimated_market_eur: number | null;
  deal_score: number | null;
  reasoning: string | null;
  pros: string[] | null;
  cons: string[] | null;
  enriched_at: string | null;
  enrich_error: string | null;
  first_publication: string | null;
  first_seen_at: string;
  last_seen_at: string;
  is_active: boolean;
  // Attributs LBC structurés (depuis la migration 20260427212853)
  attributes: Record<string, string> | null;
  mileage_km: number | null;
  fuel: string | null;
  gearbox: string | null;
  regyear: number | null;
};
