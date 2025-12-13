CREATE TABLE submit (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "timestamp" DATETIME NOT NULL,
  "ip" TEXT NOT NULL,
  "email" TEXT,
  "secret" TEXT,
  "url" TEXT,
  "answer" TEXT,
  "correct" INTEGER,
  "next_url" TEXT
);
