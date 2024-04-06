#!/bin/bash

export PGPASSWORD=pass
export PGPORT=5434

psql -h localhost -U postgres -c "select 1" sample_1 || \
    psql -h localhost -U postgres -c "create database sample_1"

psql -h localhost -U postgres -c "create table if not exists sample_table_activity (id serial primary key, name varchar)" sample_1

while /bin/true ; do
    psql -h localhost -U postgres -c "insert into sample_table_activity (name) values (gen_random_uuid())" sample_1
    psql -h localhost -U postgres -c "delete from sample_table_activity where id in (select id from sample_table_activity order by id desc offset 5)" sample_1
    psql -h localhost -U postgres -c "update sample_table_activity set name = 'updated ' || gen_random_uuid() where id = (select min(id) from sample_table_activity);" sample_1
    sleep 1
done
