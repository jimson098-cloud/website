# Supabase Setup (Vercel Persistent Storage)

1. Open je Supabase project en ga naar **SQL Editor**.
2. Run de SQL uit `supabase_schema.sql`.
3. Ga naar **Storage** en maak een publieke bucket met naam `site-images`.
4. In Vercel bij je project -> **Settings -> Environment Variables**, voeg toe:
   - `SECRET_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_BUCKET` (waarde: `site-images`)
5. Redeploy je Vercel project.

Na deploy werkt admin-opslag persistent voor:
- homepage teksten
- admin wachtwoord
- geuploade homepage afbeeldingen
