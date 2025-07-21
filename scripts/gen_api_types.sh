#!/bin/sh

python -m src.tasks.gen_schema
npx json-schema-to-typescript api-schema.json -o api-types-generated.ts --unreachableDefinitions
