-- Guardian graph. Schemaless where speed matters; edges carry the meaning.
DEFINE TABLE IF NOT EXISTS family SCHEMALESS;
DEFINE TABLE IF NOT EXISTS person SCHEMALESS;
DEFINE INDEX IF NOT EXISTS person_phone ON person FIELDS phone UNIQUE;
DEFINE TABLE IF NOT EXISTS member_of TYPE RELATION FROM person TO family;
DEFINE TABLE IF NOT EXISTS case SCHEMALESS;
DEFINE TABLE IF NOT EXISTS fingerprint SCHEMALESS;   -- domain:, brand+domain:, wallet:, phone:, text: hashes
DEFINE TABLE IF NOT EXISTS scam_text SCHEMALESS;
DEFINE INDEX IF NOT EXISTS scam_text_vec ON scam_text FIELDS embedding HNSW DIMENSION 1024 DIST COSINE;  -- reworded-scam matching
DEFINE TABLE IF NOT EXISTS has_fp TYPE RELATION FROM case TO fingerprint;

-- Example graph queries for the pitch / debugging:
-- Which other cases share a fingerprint with this one (the "herd")?
--   SELECT ->has_fp->fingerprint<-has_fp<-case AS related FROM case:A2041;
-- Everyone who protects Rosa:
--   SELECT <-member_of<-person[WHERE role = 'guardian'] FROM family:main;
