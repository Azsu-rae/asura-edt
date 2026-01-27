#!/usr/bin/env bash

set -a
source .env
set +a

source sql/setup_db.sh

# python -m scripts.populate_db
# python -m scripts.optimize
