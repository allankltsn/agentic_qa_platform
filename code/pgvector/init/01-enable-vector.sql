-- Habilita a extensão pgvector de forma idempotente no primeiro boot do banco.
-- A imagem `pgvector/pgvector` já traz a extensão compilada; aqui apenas a
-- registramos no banco padrão (POSTGRES_DB). O carregamento do Knowledge cria a
-- tabela de vetores sozinho no primeiro uso.
CREATE EXTENSION IF NOT EXISTS vector;
