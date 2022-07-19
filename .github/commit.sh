#!/usr/bin/bash

prepare_commit() {
  git config --global user.name "open-eol"
  git config --global user.email 'open-eol@users.noreply.github.com'
  git add coverage-badge.svg
  git commit -m "Update coverage badge" 2> /dev/null
  if [ $? -eq 0 ]; then
    git push https://open-eol:$1@github.com/open-uchile/eol_vimeo.git HEAD:master;
  else
    echo "Skipped";
  fi
  # Force 0 as output
  echo "Completed"
}

prepare_commit $1
