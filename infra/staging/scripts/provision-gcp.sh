#!/usr/bin/env bash
# Dung ha tang GCP cho staging (spec 014, T013; contract: specs/014-staging-deploy-monitoring/contracts/staging-cli.md).
# Chay o may DE (gcloud da login, project da gan billing). Chay lai an toan: tai nguyen da co thi in "exists" va bo qua.
#   infra/staging/scripts/provision-gcp.sh
# Bien (env hoac infra/staging/.staging.local, khong commit): GCP_PROJECT (mac dinh: project cua gcloud config),
# GCP_REGION, GCP_ZONE, VM_NAME, VM_MACHINE_TYPE, VM_DISK_GB.
# Thoat: 0 = xong, 1 = lenh gcloud loi, 2 = thieu cau hinh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_CONF="$SCRIPT_DIR/../.staging.local"
# shellcheck source=/dev/null
[[ -f "$LOCAL_CONF" ]] && source "$LOCAL_CONF"

GCP_PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
GCP_REGION="${GCP_REGION:-asia-southeast1}"
GCP_ZONE="${GCP_ZONE:-asia-southeast1-b}"
VM_NAME="${VM_NAME:-hireready-staging}"
VM_MACHINE_TYPE="${VM_MACHINE_TYPE:-e2-standard-2}"
VM_DISK_GB="${VM_DISK_GB:-50}"
NETWORK="default"
TAG="staging-web"
IP_NAME="$VM_NAME-ip"
SA_NAME="staging-vm"
SA_EMAIL="$SA_NAME@$GCP_PROJECT.iam.gserviceaccount.com"
BUCKET="gs://$GCP_PROJECT-staging-backup"
SNAPSHOT_POLICY="$VM_NAME-daily-snapshot"
IAP_RANGE="35.235.240.0/20" # dai IP cua IAP TCP forwarding (SSH khong mo ra Internet)

if [[ -z "$GCP_PROJECT" ]]; then
  echo "thieu GCP_PROJECT (gcloud config set project <id> hoac dat trong $LOCAL_CONF)" >&2
  exit 2
fi
GC=(gcloud --project "$GCP_PROJECT" --quiet)

step() { printf '\n== %s\n' "$*"; }
exists() { printf '   exists: %s\n' "$*"; }

step "bat API (compute, iap, logging, monitoring, storage)"
"${GC[@]}" services enable compute.googleapis.com iap.googleapis.com logging.googleapis.com \
  monitoring.googleapis.com storage.googleapis.com

step "IP tinh $IP_NAME ($GCP_REGION)"
if "${GC[@]}" compute addresses describe "$IP_NAME" --region "$GCP_REGION" >/dev/null 2>&1; then
  exists "$IP_NAME"
else
  "${GC[@]}" compute addresses create "$IP_NAME" --region "$GCP_REGION" --network-tier PREMIUM
fi
STATIC_IP="$("${GC[@]}" compute addresses describe "$IP_NAME" --region "$GCP_REGION" --format='value(address)')"

# Mang default co san default-allow-ssh / default-allow-rdp mo 0.0.0.0/0. Khong xoa (khong pha project khac): chan bang
# rule deny uu tien cao hon (900), roi mo lai 22 chi tu IAP o 800 (so nho hon = uu tien hon). Chi ap cho VM co tag.
create_rule() { # ten, roi cac tham so firewall-rules create
  local name="$1"; shift
  if "${GC[@]}" compute firewall-rules describe "$name" >/dev/null 2>&1; then
    exists "$name"
  else
    "${GC[@]}" compute firewall-rules create "$name" --network "$NETWORK" --target-tags "$TAG" "$@"
  fi
}
step "firewall: 80/443 tu Internet, 22 chi tu IAP, chan 22/3389 con lai"
create_rule staging-allow-web --direction INGRESS --action ALLOW --rules tcp:80,tcp:443 \
  --source-ranges 0.0.0.0/0 --priority 1000
create_rule staging-allow-iap-ssh --direction INGRESS --action ALLOW --rules tcp:22 \
  --source-ranges "$IAP_RANGE" --priority 800
create_rule staging-deny-admin --direction INGRESS --action DENY --rules tcp:22,tcp:3389 \
  --source-ranges 0.0.0.0/0 --priority 900

step "service account $SA_EMAIL (ghi log, metric, sao luu)"
if "${GC[@]}" iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  exists "$SA_EMAIL"
else
  "${GC[@]}" iam service-accounts create "$SA_NAME" --display-name "staging VM"
fi
for role in roles/logging.logWriter roles/monitoring.metricWriter; do
  "${GC[@]}" projects add-iam-policy-binding "$GCP_PROJECT" --member "serviceAccount:$SA_EMAIL" \
    --role "$role" --condition None >/dev/null
done

step "bucket sao luu $BUCKET (xoa ban > 7 ngay)"
if "${GC[@]}" storage buckets describe "$BUCKET" >/dev/null 2>&1; then
  exists "$BUCKET"
else
  "${GC[@]}" storage buckets create "$BUCKET" --location "$GCP_REGION" --uniform-bucket-level-access \
    --public-access-prevention
fi
LIFECYCLE="$(mktemp)"
trap 'rm -f "$LIFECYCLE"' EXIT
echo '{"rule":[{"action":{"type":"Delete"},"condition":{"age":7}}]}' >"$LIFECYCLE"
"${GC[@]}" storage buckets update "$BUCKET" --lifecycle-file "$LIFECYCLE" >/dev/null
"${GC[@]}" storage buckets add-iam-policy-binding "$BUCKET" --member "serviceAccount:$SA_EMAIL" \
  --role roles/storage.objectAdmin >/dev/null

step "lich snapshot o dia hang ngay, giu 7 ban ($SNAPSHOT_POLICY)"
if "${GC[@]}" compute resource-policies describe "$SNAPSHOT_POLICY" --region "$GCP_REGION" >/dev/null 2>&1; then
  exists "$SNAPSHOT_POLICY"
else
  "${GC[@]}" compute resource-policies create snapshot-schedule "$SNAPSHOT_POLICY" --region "$GCP_REGION" \
    --daily-schedule --start-time 19:00 --max-retention-days 7 --on-source-disk-delete keep-auto-snapshots
fi

step "VM $VM_NAME ($VM_MACHINE_TYPE, Ubuntu 24.04, ${VM_DISK_GB} GB, $GCP_ZONE)"
if "${GC[@]}" compute instances describe "$VM_NAME" --zone "$GCP_ZONE" >/dev/null 2>&1; then
  exists "$VM_NAME"
else
  "${GC[@]}" compute instances create "$VM_NAME" --zone "$GCP_ZONE" --machine-type "$VM_MACHINE_TYPE" \
    --image-family ubuntu-2404-lts-amd64 --image-project ubuntu-os-cloud \
    --boot-disk-size "${VM_DISK_GB}GB" --boot-disk-type pd-balanced \
    --address "$STATIC_IP" --network "$NETWORK" --tags "$TAG" \
    --service-account "$SA_EMAIL" --scopes cloud-platform \
    --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring \
    --metadata enable-oslogin=TRUE
fi

# lich snapshot gan vao O DIA (VM chi nhan policy bao tri / dat lich chay); o boot trung ten voi VM
step "gan lich snapshot vao o boot $VM_NAME"
if "${GC[@]}" compute disks describe "$VM_NAME" --zone "$GCP_ZONE" --format='value(resourcePolicies)' \
  | grep -q "/$SNAPSHOT_POLICY"; then
  exists "$SNAPSHOT_POLICY tren o $VM_NAME"
else
  "${GC[@]}" compute disks add-resource-policies "$VM_NAME" --zone "$GCP_ZONE" --resource-policies "$SNAPSHOT_POLICY"
fi

step "xong"
cat <<EOF
   IP tinh: $STATIC_IP
   DNS (name.com, domain tuannm.app): ban ghi A, host *.hireready, gia tri $STATIC_IP, TTL 300
   Buoc tiep (T014):
     gcloud compute scp --tunnel-through-iap --zone $GCP_ZONE infra/staging/scripts/bootstrap-vm.sh $VM_NAME:/tmp/
     gcloud compute ssh --tunnel-through-iap --zone $GCP_ZONE $VM_NAME --command 'sudo bash /tmp/bootstrap-vm.sh'
EOF
