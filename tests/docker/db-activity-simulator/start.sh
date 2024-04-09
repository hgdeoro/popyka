#!/bin/bash

set -eu

echo "DSN_CHECK_DB=${DSN_CHECK_DB}"
echo "DSN_ACTIVITY_SIMULATOR=${DSN_ACTIVITY_SIMULATOR}"

psql ${DSN_CHECK_DB} -c "select 1" || \
    psql ${DSN_CHECK_DB} -c "create database sample_1"

psql ${DSN_ACTIVITY_SIMULATOR} -c "create table if not exists sample_table_activity (id serial primary key, name varchar)"

while /bin/true ; do
    psql ${DSN_ACTIVITY_SIMULATOR} -c "insert into sample_table_activity (name) values (md5(random()::text))"
    psql ${DSN_ACTIVITY_SIMULATOR} -c "delete from sample_table_activity where id in (select id from sample_table_activity order by id desc offset 5)"
    psql ${DSN_ACTIVITY_SIMULATOR} -c "update sample_table_activity set name = 'updated ' || md5(random()::text) where id = (select min(id) from sample_table_activity);"
    sleep 1
done
