#!/usr/bin/env bash
# Creates labels, milestones, issues and sub-issue links for Tachocline Industries
# from issues.json. Idempotent: safe to re-run; only creates what is missing.
#
# SAFETY: writes ONLY to the hardcoded REPO below. Every gh call names the repo
# explicitly (never the current directory's git remote). Aborts if issues.json
# names a different repo.
#
# Usage:  cd gh-setup && ./setup_labels_milestones_issues.sh
# Needs:  gh (logged in as howardisaacson, scope: repo), python3
set -euo pipefail

readonly REPO="howardisaacson/tachocline-industries"
readonly OWNER="howardisaacson"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PLAN="$HERE/issues.json"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

command -v gh >/dev/null || die "gh not installed"
command -v python3 >/dev/null || die "python3 not found"
[[ -f "$PLAN" ]] || die "missing $PLAN"

# --- Guard rails ------------------------------------------------------------
plan_repo="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repo"])' "$PLAN")"
[[ "$plan_repo" == "$REPO" ]] || die "issues.json repo '$plan_repo' != hardcoded '$REPO'. Aborting."
login="$(gh api user --jq .login)"
[[ "$login" == "$OWNER" ]] || die "gh is logged in as '$login', expected '$OWNER'."
gh api "repos/$REPO" --jq .full_name >/dev/null || die "cannot access $REPO"
say "Target repo: $REPO (logged in as $login)"

# --- 1. Labels (gh label create --force updates colour/description if present)
say "Labels"
python3 - "$PLAN" > "$TMP/labels.tsv" <<'PY'
import json,sys
for l in json.load(open(sys.argv[1]))["labels"]:
    print(f'{l["name"]}\t{l["color"]}\t{l["description"]}')
PY
while IFS=$'\t' read -r name color desc; do
  gh label create "$name" --repo "$REPO" --color "$color" --description "$desc" --force >/dev/null
  echo "   label: $name"
done < "$TMP/labels.tsv"

# --- 2. Milestones (create only if the title is missing) --------------------
say "Milestones"
gh api --paginate "repos/$REPO/milestones?state=all&per_page=100" \
  --jq '.[] | [.title, (.number|tostring)] | @tsv' > "$TMP/ms_existing.tsv"
python3 - "$PLAN" > "$TMP/ms_plan.tsv" <<'PY'
import json,sys
for m in json.load(open(sys.argv[1]))["milestones"]:
    print(f'{m["title"]}\t{m["description"]}')
PY
while IFS=$'\t' read -r title desc; do
  if cut -f1 "$TMP/ms_existing.tsv" | grep -Fxq -- "$title"; then
    echo "   exists: $title"
  else
    num="$(gh api -X POST "repos/$REPO/milestones" -f title="$title" -f description="$desc" --jq .number)"
    printf '%s\t%s\n' "$title" "$num" >> "$TMP/ms_existing.tsv"
    echo "   created: $title (#$num)"
  fi
done < "$TMP/ms_plan.tsv"

# --- 3. Issues (create only if no open/closed issue has the same title) -----
say "Issues"
# Existing issues (excluding PRs): title, number, id
gh api --paginate "repos/$REPO/issues?state=all&per_page=100" \
  --jq '.[] | select(.pull_request == null) | [.title, (.number|tostring), (.id|tostring)] | @tsv' \
  > "$TMP/issues_existing.tsv"

# Write one JSON payload per planned issue + an index (key, title)
python3 - "$PLAN" "$TMP" <<'PY'
import json,sys,os
plan=json.load(open(sys.argv[1])); tmp=sys.argv[2]
ms={}
for line in open(os.path.join(tmp,"ms_existing.tsv")):
    t,n=line.rstrip("\n").split("\t"); ms[t]=int(n)
with open(os.path.join(tmp,"plan_index.tsv"),"w") as idx:
    for i in plan["issues"]:
        payload={"title":i["title"],"body":i["body"],"labels":i["labels"],"milestone":ms[i["milestone"]]}
        json.dump(payload,open(os.path.join(tmp,f'issue_{i["key"]}.json'),"w"))
        idx.write(f'{i["key"]}\t{i["title"]}\t{i.get("parent","")}\n')
PY

created=0; skipped=0
while IFS=$'\t' read -r key title _parent; do
  if cut -f1 "$TMP/issues_existing.tsv" | grep -Fxq -- "$title"; then
    skipped=$((skipped+1)); echo "   exists: $title"
  else
    line="$(gh api -X POST "repos/$REPO/issues" --input "$TMP/issue_${key}.json" \
            --jq '[.title, (.number|tostring), (.id|tostring)] | @tsv')"
    printf '%s\n' "$line" >> "$TMP/issues_existing.tsv"
    created=$((created+1)); echo "   created: #$(cut -f2 <<<"$line") $title"
    sleep 1   # be gentle: avoid secondary rate limits on content creation
  fi
done < "$TMP/plan_index.tsv"
say "Issues: $created created, $skipped already existed"

# --- 4. Sub-issues: POST /repos/{owner}/{repo}/issues/{parent_number}/sub_issues
#        with sub_issue_id = the child's numeric *id* (not its number).
say "Sub-issue links"
lookup() {  # $1=title -> "number<TAB>id"
  awk -F'\t' -v t="$1" '$1==t {print $2"\t"$3; exit}' "$TMP/issues_existing.tsv"
}
title_of() {  # $1=key -> title
  awk -F'\t' -v k="$1" '$1==k {print $2; exit}' "$TMP/plan_index.tsv"
}
while IFS=$'\t' read -r key title parent; do
  [[ -z "$parent" ]] && continue
  IFS=$'\t' read -r child_num child_id <<<"$(lookup "$title")"
  IFS=$'\t' read -r parent_num _ <<<"$(lookup "$(title_of "$parent")")"
  [[ -n "${child_id:-}" && -n "${parent_num:-}" ]] || { echo "   skip (not found): $title"; continue; }
  if gh api "repos/$REPO/issues/$parent_num/sub_issues?per_page=100" --paginate --jq '.[].id' \
       | grep -Fxq -- "$child_id"; then
    echo "   linked already: #$child_num -> #$parent_num"
  else
    gh api -X POST "repos/$REPO/issues/$parent_num/sub_issues" -F sub_issue_id="$child_id" >/dev/null \
      && echo "   linked: #$child_num -> parent #$parent_num" \
      || echo "   WARN: could not link #$child_num -> #$parent_num (already has another parent?)"
  fi
done < "$TMP/plan_index.tsv"

say "Done. Open: https://github.com/$REPO/issues  and  https://github.com/$REPO/milestones"
