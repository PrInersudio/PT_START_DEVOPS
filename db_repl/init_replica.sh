
until pg_basebackup --pgdata=/var/lib/postgresql/data -R --slot=replication_slot --host=${DB_HOST} --port=${DB_PORT}
do
    echo 'Waiting for primary to connect...'
    sleep 1s
done
    echo 'Backup done, starting replica...'
    chown -R postgres:postgres /var/lib/postgresql/data
    chmod -R 0700 /var/lib/postgresql/data
    echo 'gosu postgres postgres' > init_replica.sh # нужно, чтобы скрипт бэкапа не выполнятся при перезагруке, а то postgres на это ругается
    exec gosu postgres postgres
fi