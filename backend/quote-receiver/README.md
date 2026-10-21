# PartRevive quote receiver

Cloud Run service `partrevive-quote` in Google Cloud project `monterey-bay-lab` (us-central1).
The static site's quote form posts here. The service validates the fields, stores each lead
(JSON + photo) in the private bucket `gs://partrevive-leads-mbl/leads/<lead_id>/`, and writes
one structured log line `event="partrevive_lead"`. A Cloud Monitoring log-based alert policy
("PartRevive: new quote request") emails that line's fields to Jon.

Deploy (from the repo root):

    gcloud run deploy partrevive-quote --source backend/quote-receiver --region us-central1 \
      --project monterey-bay-lab --allow-unauthenticated \
      --service-account partrevive-quote@monterey-bay-lab.iam.gserviceaccount.com \
      --set-env-vars LEADS_BUCKET=partrevive-leads-mbl,SITE_ORIGIN=https://jdinneen.github.io,SITE_BASE=https://jdinneen.github.io/partrevive \
      --memory 256Mi --cpu 1 --concurrency 20 --max-instances 3 --timeout 60

Runtime service account has only `storage.objectCreator` on the bucket and `logging.logWriter`.
No secrets are stored anywhere. Cost at launch volumes: effectively zero (Cloud Run free tier).
