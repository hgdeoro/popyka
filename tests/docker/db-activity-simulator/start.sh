#!/bin/bash

set -eu

echo "DSN=${DSN}"
echo "DSN_CREATE_DB=${DSN_CREATE_DB}"

psql ${DSN} -c "select 1" || \
    psql ${DSN_CREATE_DB} -c "create database sample_1"

psql ${DSN} -c "create table if not exists sample_table_activity (id serial primary key, name varchar)"

while /bin/true ; do
    psql ${DSN} -c "insert into sample_table_activity (name) values (gen_random_uuid())"
    psql ${DSN} -c "delete from sample_table_activity where id in (select id from sample_table_activity order by id desc offset 5)"
    psql ${DSN} -c "update sample_table_activity set name = 'updated ' || gen_random_uuid() where id = (select min(id) from sample_table_activity);"
    sleep 1
done
