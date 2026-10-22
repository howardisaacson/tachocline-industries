#!/usr/bin/env bash
# Creates (or reuses) the user-level Project "Tachocline Industries Roadmap",
# links it ONLY to the hardcoded REPO, adds custom fields, adds every repo issue,
# sets Phase from each issue's milestone, and tries to create Board/Table/Roadmap views.
#
# SAFETY: writes only to REPO's issues (read) and this one Project owned by OWNER.
# Never uses the current directory's git remote.
#
# Requires the 'project' scope:  gh auth refresh -s project
# Run AFTER setup_labels_milestones_issues.sh.
set -euo pipefail

readonly REPO="howardisaacson/tachocline-industries"
readonly OWNER="howardisaacson"
readonly TITLE="Tachocline Industries Roadmap"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

command -v gh >/dev/null || die "gh not installed"
command -v python3 >/dev/null || die "python3 not found"

# --- Guard rails --------------------------------------------------------------
status="$(gh auth status 2>&1 || true)"
if ! grep -Eq "Token scopes:.*'project'" <<<"$status"; then
  die "Your gh token lacks the 'project' scope. Run:  gh auth refresh -s project   then re-run this script."
fi
login="$(gh api user --jq .login)"
[[ "$login" == "$OWNER" ]] || die "gh is logged in as '$login', expected '$OWNER'."
[[ "$REPO" == "$OWNER/tachocline-industries" ]] || die "REPO mismatch; aborting."
gh api "repos/$REPO" --jq .full_name >/dev/null || die "cannot access $REPO"

# --- 1. Find or create the project (by exact title) ----------------------------
say "Project"
num="$(gh project list --owner "$OWNER" --closed --limit 100 --format json \
       | python3 -c 'import json,sys; t=sys.argv[1]; print(next((str(p["number"]) for p in json.load(sys.stdin)["projects"] if p["title"]==t),""))' "$TITLE")"
if [[ -z "$num" ]]; then
  num="$(gh project create --owner "$OWNER" --title "$TITLE" --format json --jq .number)"
  echo "   created project #$num"
else
  echo "   found project #$num"
fi
proj_id="$(gh project view "$num" --owner "$OWNER" --format json --jq .id)"

# --- 2. Link to the repo (shows under the repo's Projects tab) -----------------
gh project link "$num" --owner "$OWNER" --repo "$REPO" >/dev/null 2>&1 \
  && echo "   linked to $REPO" || echo "   link: already linked (or not permitted); check the repo's Projects tab"

# --- 3. Custom fields (create only if missing) ---------------------------------
say "Fields"
phases="$(gh api "repos/$REPO/milestones?state=all&per_page=100" --jq '[.[].title] | sort | join(",")')"
[[ -n "$phases" ]] || die "No milestones found; run setup_labels_milestones_issues.sh first."
existing_fields="$(gh project field-list "$num" --owner "$OWNER" --limit 100 --format json --jq '.fields[].name')"
mkfield() {  # name options
  if grep -Fxq -- "$1" <<<"$existing_fields"; then echo "   exists: $1"
  else gh project field-create "$num" --owner "$OWNER" --name "$1" --data-type SINGLE_SELECT \
         --single-select-options "$2" >/dev/null && echo "   created: $1 ($2)"; fi
}
mkfield "Phase" "$phases"
mkfield "Priority" "P0,P1,P2"
mkfield "Size" "XS,S,M,L"
# Note: if you add a milestone later, add the matching Phase option in the web UI
# (or delete the Phase field and re-run).

gh project field-list "$num" --owner "$OWNER" --limit 100 --format json > "$TMP/fields.json"
phase_field_id="$(python3 -c 'import json,sys; print(next(f["id"] for f in json.load(open(sys.argv[1]))["fields"] if f["name"]=="Phase"))' "$TMP/fields.json")"

# --- 4. Add every issue in REPO and set Phase = milestone ----------------------
say "Items"
gh api --paginate "repos/$REPO/issues?state=all&per_page=100" \
  --jq '.[] | select(.pull_request == null) | [.html_url, (.milestone.title // "")] | @tsv' > "$TMP/issues.tsv"
n=0
while IFS=$'\t' read -r url ms; do
  # item-add is idempotent: adding an issue already in the project returns the existing item
  item_id="$(gh project item-add "$num" --owner "$OWNER" --url "$url" --format json --jq .id)"
  if [[ -n "$ms" ]]; then
    opt_id="$(python3 -c 'import json,sys; f=next(f for f in json.load(open(sys.argv[1]))["fields"] if f["name"]=="Phase"); print(next((o["id"] for o in f.get("options",[]) if o["name"]==sys.argv[2]),""))' "$TMP/fields.json" "$ms")"
    if [[ -n "$opt_id" ]]; then
      gh project item-edit --id "$item_id" --project-id "$proj_id" --field-id "$phase_field_id" \
        --single-select-option-id "$opt_id" >/dev/null
    fi
  fi
  n=$((n+1)); echo "   $url  [${ms:-no milestone}]"
done < "$TMP/issues.tsv"
say "$n issues in project"

# --- 5. Views (best effort) ----------------------------------------------------
# GitHub added the GraphQL mutation createProjectV2View in July 2026 (layouts TABLE/BOARD/ROADMAP).
# It creates the view, but grouping, sorting and roadmap date fields still need the web UI.
say "Views (best effort)"
# shellcheck disable=SC2016  # GraphQL $variables are intentionally literal
existing_views="$(gh api graphql -f query='query($login:String!,$n:Int!){user(login:$login){projectV2(number:$n){views(first:50){nodes{name}}}}}' \
  -f login="$OWNER" -F n="$num" --jq '.data.user.projectV2.views.nodes[].name' 2>/dev/null || true)"
mkview() {  # name layout
  if grep -Fxq -- "$1" <<<"$existing_views"; then echo "   exists: $1"; return; fi
  # shellcheck disable=SC2016
  if gh api graphql -f query='mutation($p:ID!,$name:String!,$layout:ProjectV2ViewLayout!){createProjectV2View(input:{projectId:$p,name:$name,layout:$layout}){projectV2View{id}}}' \
       -f p="$proj_id" -f name="$1" -f layout="$2" >/dev/null 2>&1; then
    echo "   created: $1"
  else
    echo "   could not create '$1' via API; create it in the web UI (see checklist)"
  fi
}
mkview "Board" BOARD_LAYOUT
mkview "Table" TABLE_LAYOUT
mkview "Roadmap" ROADMAP_LAYOUT

say "Done: https://github.com/users/$OWNER/projects/$num"
cat <<'TXT'

Finish in the web UI (Project → … menu / view settings):
 [ ] Board view: Group by Status (Todo / In Progress / Done); column limit optional
 [ ] Table view: show Title, Status, Phase, Priority, Size, Labels, Milestone, Linked PRs; group by Phase
 [ ] Roadmap view: set date fields (add Start/Target date fields or use Milestone), zoom = Quarter
 [ ] Workflows → enable "Item added to project" defaults Status = Todo
 [ ] Workflows → "Item closed" → Done, and "Pull request merged" → Done (usually on by default; verify)
 [ ] Workflows → "Auto-add to project": filter  repo:howardisaacson/tachocline-industries is:issue,pr
 [ ] Workflows → "Auto-archive items" (optional): closed for 2+ weeks
 [ ] Set Priority and Size on Phase 0/1 issues (that triage is the learning exercise)
 [ ] Optional: delete the default "View 1" if it duplicates Table
TXT
