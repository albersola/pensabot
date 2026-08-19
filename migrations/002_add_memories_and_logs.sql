ALTER TABLE chats ADD COLUMN user_id TEXT;

UPDATE chats
SET user_id = conversation_id
WHERE user_id IS NULL;

ALTER TABLE chats ALTER COLUMN user_id SET NOT NULL;

CREATE INDEX chats_user_recent_idx
    ON chats (user_id, id DESC);

CREATE TABLE memories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    memory_key TEXT NOT NULL,
    content TEXT NOT NULL,
    source_conversation_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, memory_key)
);

CREATE INDEX memories_user_updated_idx
    ON memories (user_id, updated_at DESC);

CREATE TABLE logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT,
    conversation_id TEXT,
    event TEXT NOT NULL,
    message TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX logs_user_created_idx
    ON logs (user_id, created_at DESC);

CREATE INDEX logs_conversation_created_idx
    ON logs (conversation_id, created_at DESC);
