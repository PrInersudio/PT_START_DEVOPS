echo "Starting 002-init.sh"

sed -i '$d' /var/lib/postgresql/data/pg_hba.conf
echo "host replication ${DB_REPL_USER} ${DB_REPL_HOST}/32 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
echo "host ${DB_DATABASE} ${DB_USER} ${BOT_HOST}/32 password" >> /var/lib/postgresql/data/pg_hba.conf

echo "pg_hba.conf is changed"

psql -U ${POSTGRES_USER} -d ${DB_DATABASE} \
-c "create user ${DB_REPL_USER} with replication encrypted password '${DB_REPL_PASSWORD}';" \
-c "create user ${DB_USER} with password '${DB_PASSWORD}';" \
-c "GRANT SELECT, INSERT ON TABLE emails TO ${DB_USER};" \
-c "GRANT SELECT, INSERT ON TABLE phone_numbers TO ${DB_USER};" \
-c "GRANT USAGE ON SEQUENCE emails_id_seq TO tg_bot;" \
-c "GRANT USAGE ON SEQUENCE phone_numbers_id_seq TO tg_bot;"


echo "Finished 002-init.sh sucessfully"
