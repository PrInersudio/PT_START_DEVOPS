FROM postgres:16.3
WORKDIR /db
VOLUME ./db_logs

ENV POSTGRES_USER admin
ENV POSTGRES_PASSWORD Qq123456
ENV POSTGRES_DB emails_and_phone_numbers

COPY 001-init.sql /docker-entrypoint-initdb.d/
COPY 002-init.sh /docker-entrypoint-initdb.d/
RUN mkdir db_logs && chown postgres:postgres db_logs
CMD ["postgres", "-c", "max_wal_senders=10", "-c", "wal_level=replica", "-c", "wal_log_hints=on", "-c", "hot_standby=on", "-c", "max_replication_slots=10", "-c", "hot_standby_feedback=on", "-c", "log_replication_commands=on", "-c", "logging_collector=on", "-c", "log_directory=/db/db_logs"]