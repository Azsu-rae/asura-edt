#!/usr/bin/env bash

# Exit immediately if a command fails
set -e

echo "Initalizing database..."
# echo MYSQL_PWD=$MYSQL_PWD mariadb --host "$DB_HOST" --port "$DB_PORT" --user "$DB_USER" -e "DROP DATABASE IF EXISTS ${DB_NAME}"

export MYSQL_PWD="$DB_PASS"
mysql --host "$DB_HOST" --port "$DB_PORT" --user "$DB_USER" -e "SET FOREIGN_KEY_CHECKS=0; DROP DATABASE IF EXISTS ${DB_NAME}; SET FOREIGN_KEY_CHECKS=1;"
mysql --host "$DB_HOST" --port "$DB_PORT" --user "$DB_USER" -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME}"

mysql --host "$DB_HOST" --port "$DB_PORT" --user "$DB_USER" "$DB_NAME" < sql/schema.sql

echo "Done!"
