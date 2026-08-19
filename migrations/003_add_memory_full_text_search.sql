ALTER TABLE memories
ADD COLUMN search_vector TSVECTOR
GENERATED ALWAYS AS (
    to_tsvector('simple', COALESCE(content, ''))
) STORED;

CREATE INDEX memories_search_vector_idx
    ON memories USING GIN (search_vector);
