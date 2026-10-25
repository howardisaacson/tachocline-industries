-- Same psql -1 transaction as the migration file. psql expands
-- :'ti_migration_filename' in a file. It does not expand it in -c.
INSERT INTO schema_migrations (filename) VALUES (:'ti_migration_filename');
