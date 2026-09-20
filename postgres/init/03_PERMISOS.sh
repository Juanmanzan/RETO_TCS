
set -e

psql \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=app_user="$APP_DB_USER" \
  --set=app_password="$APP_DB_PASSWORD" <<'EOSQL'

-- verifica si el usuario ya existe, si no existe lo crea con la contrasena definida en el entorno
SELECT format(
    'CREATE USER %I WITH PASSWORD %L',
    :'app_user',
    :'app_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_roles
    WHERE rolname = :'app_user'
)
\gexec

-- permite que el usuario pueda conectarse a la base de datos actual
SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I',
    current_database(),
    :'app_user'
)
\gexec

-- permite que el usuario pueda utilizar el schema public
SELECT format(
    'GRANT USAGE ON SCHEMA public TO %I',
    :'app_user'
)
\gexec

-- permite realizar consultas, inserciones y actualizaciones sobre las tablas creadas 
SELECT format(
    'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO %I',
    :'app_user'
)
\gexec

-- permite utilizar las secuencias e ids autoincrement de las tablas creadas
SELECT format(
    'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I',
    :'app_user'
)
\gexec


EOSQL

echo "usuario creado correctamente."