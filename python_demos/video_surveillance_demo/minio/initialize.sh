#!/bin/bash
echo "Starting MinIO..."
/usr/bin/docker-entrypoint.sh server /data --console-address ":9001" &
echo "Waiting for a few seconds..."
sleep 2
BUCKET_ALIAS=LOCALHOST_ALIAS/demo
mc ls $BUCKET_ALIAS >/dev/null 2>&1
bucket_not_exists=$?
if [ "$bucket_not_exists" != "0" ]; then
  echo "Bucket $BUCKET_ALIAS does not exist. Initializing..."
  # Create bucket
  mc mb $BUCKET_ALIAS
  # Lifecycle
  mc ilm add --tags expires_in=1d --expire-days 1 $BUCKET_ALIAS
  mc ilm add --tags expires_in=7d --expire-days 7 $BUCKET_ALIAS
  mc ilm add --tags expires_in=30d --expire-days 30 $BUCKET_ALIAS
  mc ilm add --tags expires_in=90d --expire-days 90 $BUCKET_ALIAS
  mc ilm add --tags expires_in=180d --expire-days 180 $BUCKET_ALIAS
  mc ilm add --tags expires_in=365d --expire-days 365 $BUCKET_ALIAS
  mc ilm rule ls $BUCKET_ALIAS
  echo "Bucket $BUCKET_ALIAS initialized."
else
  echo "Bucket $BUCKET_ALIAS already exists; no need to initialize."
fi
wait -n
exit $?