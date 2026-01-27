#!/usr/bin/env bash

# Exit immediately if a command fails
set -e

echo "Initalizing database..."

# docker exec\
#  -e MYSQL_PWD="$DB_PASS"\
#  my-mysql mysql\
#  --user "$DB_USER"\
#  --port "$DB_PORT"\
#  --host "$DB_HOST"\
#  -e "SET FOREIGN_KEY_CHECKS=0; DROP DATABASE IF EXISTS ${DB_NAME}; SET FOREIGN_KEY_CHECKS=1;"

docker exec\
 -e MYSQL_PWD="$DB_PASS"\
 my-mysql mysql\
 --user "$DB_USER"\
 --port "$DB_PORT"\
 --host "$DB_HOST"\
 -e "SET GLOBAL sql_mode=(SELECT REPLACE(@@sql_mode,'ONLY_FULL_GROUP_BY',''));"

# docker exec\
#  -e MYSQL_PWD="$DB_PASS"\
#  my-mysql mysql\
#  --user "$DB_USER"\
#  --port "$DB_PORT"\
#  --host "$DB_HOST"\
#  -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME}"

# docker exec -i \
#  -e MYSQL_PWD="$DB_PASS"\
#  my-mysql mysql\
#  --user "$DB_USER"\
#  --port "$DB_PORT"\
#  --host "$DB_HOST"\
#  "$DB_NAME" < sql/schema.sql

echo "Done!"
