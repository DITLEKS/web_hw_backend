-- Admin user storage

CREATE TABLE IF NOT EXISTS admins (
  id            SERIAL PRIMARY KEY,
  email         VARCHAR(254) NOT NULL UNIQUE,
  first_name    VARCHAR(100) NOT NULL,
  last_name     VARCHAR(100) NOT NULL,
  role          VARCHAR(50)  NOT NULL DEFAULT 'admin',
  password_hash TEXT         NOT NULL,
  is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

INSERT INTO admins (email, first_name, last_name, role, password_hash, is_active) VALUES
  ('admin@smartlight.ru', 'Сергей', 'Петров', 'admin', 'qY9LkCXI64xRE+B6A7t4QNU4lkOIehVn+qr72zhqqsPtggtD9PUf4UrdRl8cd5iK', TRUE)
ON CONFLICT (email) DO NOTHING;
